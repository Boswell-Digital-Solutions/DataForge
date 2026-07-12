"""Forge Memory spine (FMEM-02) — authenticated, scoped, bitemporal endpoints.

The durable ``MemoryStore`` for the forge-memory engine. Every write is
authenticated (JWT) and carries a tenant scope; reads filter by scope before
returning; facts are bitemporal (current vs as-of); deletion is real and yields
a non-sensitive receipt.

Closes the FMEM-00 gaps in the legacy agent-memory surface: unauthenticated
writes, no scope isolation, no temporal model, no deletion path.

Contract note: the forge-memory engine already validates artifacts at its
boundary against the vendored schemas. This service re-validates the envelope
structurally (Pydantic, unknown-fields-fail-closed) and enforces the secret
fail-closed rule; deep family-schema validation via forge_contract_core can be
layered once the Memory* families land on its published branch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.models.memory_models import (
    MemoryClaim,
    MemoryDeletion,
    MemoryEpisode,
    MemoryFact,
    MemoryReceipt,
)
from app.models.memory_schemas import (
    ArtifactIn,
    DeletionReceiptOut,
    SupersedeRequest,
    WriteResponse,
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/api/v1/memory", tags=["Memory"])

_FORBIDDEN_SENSITIVITY = "secret_or_credential"
_DELETABLE = {
    "episodes": (MemoryEpisode, "memory_episode"),
    "claims": (MemoryClaim, "memory_claim"),
    "facts": (MemoryFact, "memory_fact"),
}


def _parse_dt(value: str) -> datetime:
    """Parse RFC 3339 to a naive-UTC datetime. Naive-UTC keeps comparisons
    consistent across SQLite (which strips tzinfo) and Postgres timestamptz."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid RFC 3339 timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _scope(payload: dict[str, Any]) -> dict[str, str | None]:
    scope = payload.get("scope") or {}
    tenant = scope.get("tenant_id")
    if not tenant:
        raise HTTPException(status_code=422, detail="payload.scope.tenant_id is required")
    return {
        "tenant_id": tenant,
        "user_id": scope.get("user_id"),
        "project_id": scope.get("project_id"),
        "repo_id": scope.get("repo_id"),
    }


def _require_family(art: ArtifactIn, expected: str) -> None:
    if art.artifact_family != expected:
        raise HTTPException(
            status_code=422,
            detail=f"expected artifact_family={expected!r}, got {art.artifact_family!r}",
        )


def _reject_secret(payload: dict[str, Any]) -> None:
    if payload.get("sensitivity_class") == _FORBIDDEN_SENSITIVITY:
        raise HTTPException(
            status_code=422,
            detail="sensitivity_class=secret_or_credential is rejected; secrets are never stored",
        )


# ── Episodes ──────────────────────────────────────────────────────────────────


@router.post("/episodes", status_code=201, response_model=WriteResponse)
def write_episode(
    art: ArtifactIn,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(art, "memory_episode")
    p = art.payload
    _reject_secret(p)
    scope = _scope(p)
    existed = db.get(MemoryEpisode, art.artifact_id) is not None
    row = MemoryEpisode(
        artifact_id=art.artifact_id,
        episode_id=p.get("episode_id", art.artifact_id),
        run_id=(p.get("run_ref") or {}).get("run_id"),
        agent_id=(p.get("run_ref") or {}).get("agent_id"),
        episode_type=p["episode_type"],
        origin_class=p["origin_class"],
        occurred_at=_parse_dt(p["occurred_at"]),
        recorded_at=_parse_dt(p["recorded_at"]),
        residency=p["residency"],
        sensitivity_class=p["sensitivity_class"],
        instruction_capability=p["instruction_capability"],
        quarantined=bool(p.get("quarantined", False)),
        payload=art.model_dump(),
        **scope,
    )
    db.merge(row)
    db.commit()
    return WriteResponse(artifact_id=art.artifact_id, family="memory_episode", status="refreshed" if existed else "stored")


# ── Claims ────────────────────────────────────────────────────────────────────


@router.post("/claims", status_code=201, response_model=WriteResponse)
def write_claim(
    art: ArtifactIn,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(art, "memory_claim")
    p = art.payload
    scope = _scope(p)
    existed = db.get(MemoryClaim, art.artifact_id) is not None
    row = MemoryClaim(
        artifact_id=art.artifact_id,
        claim_id=p.get("claim_id", art.artifact_id),
        subject_entity_id=p["subject_entity_id"],
        predicate=p["predicate"],
        object=str(p["object"]),
        authority_class=p["authority_class"],
        trust_state=p["trust_state"],
        verification_state=p["verification_state"],
        confidence=float(p["confidence"]),
        payload=art.model_dump(),
        **scope,
    )
    db.merge(row)
    db.commit()
    return WriteResponse(artifact_id=art.artifact_id, family="memory_claim", status="refreshed" if existed else "stored")


# ── Facts (bitemporal + supersession) ─────────────────────────────────────────


def _fact_row(art: ArtifactIn) -> MemoryFact:
    p = art.payload
    _reject_secret(p)
    scope = _scope(p)
    return MemoryFact(
        artifact_id=art.artifact_id,
        memory_id=p.get("memory_id", art.artifact_id),
        subject_entity_id=p["subject_entity_id"],
        predicate=p["predicate"],
        object=str(p["object"]),
        authority_class=p["authority_class"],
        trust_state=p["trust_state"],
        verification_state=p["verification_state"],
        status=p["status"],
        valid_from=_parse_dt(p["valid_from"]),
        valid_to=_parse_dt(p["valid_to"]) if p.get("valid_to") else None,
        observed_at=_parse_dt(p["observed_at"]),
        recorded_at=_parse_dt(p["recorded_at"]),
        supersedes_memory_id=p.get("supersedes_memory_id"),
        payload=art.model_dump(),
        **scope,
    )


@router.post("/facts", status_code=201, response_model=WriteResponse)
def write_fact(
    art: ArtifactIn,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(art, "memory_fact")
    existed = db.get(MemoryFact, art.artifact_id) is not None
    db.merge(_fact_row(art))
    db.commit()
    return WriteResponse(artifact_id=art.artifact_id, family="memory_fact", status="refreshed" if existed else "stored")


@router.post("/facts/{memory_id}/supersede", response_model=WriteResponse)
def supersede_fact(
    memory_id: str,
    body: SupersedeRequest,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(body.new_fact, "memory_fact")
    tenant = _scope(body.new_fact.payload)["tenant_id"]
    prev = db.get(MemoryFact, memory_id)
    if prev is None or prev.tenant_id != tenant:
        raise HTTPException(status_code=404, detail=f"fact {memory_id} not found in tenant scope")

    at = _parse_dt(body.effective_at)
    prev.status = "superseded"
    prev.valid_to = at
    prev_payload = dict(prev.payload or {})
    prev_inner = dict(prev_payload.get("payload") or {})
    prev_inner["status"] = "superseded"
    prev_inner["valid_to"] = body.effective_at
    prev_payload["payload"] = prev_inner
    prev.payload = prev_payload

    db.merge(_fact_row(body.new_fact))
    db.add(prev)
    db.commit()
    return WriteResponse(
        artifact_id=body.new_fact.artifact_id, family="memory_fact", status="stored"
    )


@router.get("/facts")
def retrieve_facts(
    tenant_id: str = Query(..., min_length=1),
    subject_entity_id: str = Query(..., min_length=1),
    predicate: str = Query(..., min_length=1),
    as_of: str | None = Query(None, description="RFC 3339; omit for current truth"),
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Deterministic temporal retrieval. Scope is enforced before results are
    returned. ``as_of`` omitted → current; provided → historically-valid facts."""
    q = db.query(MemoryFact).filter(
        MemoryFact.tenant_id == tenant_id,
        MemoryFact.subject_entity_id == subject_entity_id,
        MemoryFact.predicate == predicate,
    )
    if as_of is None:
        q = q.filter(MemoryFact.status == "active", MemoryFact.valid_to.is_(None))
        temporal = "current"
    else:
        at = _parse_dt(as_of)
        q = q.filter(
            MemoryFact.valid_from <= at,
            (MemoryFact.valid_to.is_(None)) | (MemoryFact.valid_to > at),
        )
        temporal = as_of
    rows = q.order_by(MemoryFact.valid_from.desc()).all()
    return {
        "temporal": temporal,
        "count": len(rows),
        "facts": [r.payload for r in rows],
    }


# ── Receipts ──────────────────────────────────────────────────────────────────


def _write_receipt(art: ArtifactIn, kind: str, db: Session) -> WriteResponse:
    scope = _scope(art.payload)
    row = MemoryReceipt(
        artifact_id=art.artifact_id,
        receipt_kind=kind,
        payload=art.model_dump(),
        **scope,
    )
    db.merge(row)
    db.commit()
    return WriteResponse(artifact_id=art.artifact_id, family=art.artifact_family, status="stored")


@router.post("/retrieval-receipts", status_code=201, response_model=WriteResponse)
def write_retrieval_receipt(
    art: ArtifactIn,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(art, "memory_retrieval_receipt")
    return _write_receipt(art, "retrieval", db)


@router.post("/use-receipts", status_code=201, response_model=WriteResponse)
def write_use_receipt(
    art: ArtifactIn,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> WriteResponse:
    _require_family(art, "memory_use_receipt")
    return _write_receipt(art, "use", db)


# ── Deletion (real, with receipt) ─────────────────────────────────────────────


@router.delete("/{family}/{artifact_id}", response_model=DeletionReceiptOut)
def delete_memory(
    family: str,
    artifact_id: str,
    tenant_id: str = Query(..., min_length=1),
    reason: str | None = Query(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> DeletionReceiptOut:
    if family not in _DELETABLE:
        raise HTTPException(status_code=404, detail=f"unknown memory family {family!r}")
    model, family_name = _DELETABLE[family]
    row = db.get(model, artifact_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"{family_name} {artifact_id} not found in tenant scope")

    db.delete(row)
    receipt = MemoryDeletion(
        target_family=family_name,
        target_id=artifact_id,
        tenant_id=tenant_id,
        reason=reason,
        requested_by=getattr(user, "username", "unknown"),
    )
    db.add(receipt)
    db.commit()
    return DeletionReceiptOut(
        receipt_id=receipt.id,
        target_family=family_name,
        target_id=artifact_id,
        deleted=True,
        deleted_at=receipt.deleted_at.isoformat() if receipt.deleted_at else None,
    )

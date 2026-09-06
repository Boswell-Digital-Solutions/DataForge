"""RateCardSnapshot.v1 durable store (Cost Provenance Tranche 3, RFC-CP-03).

DataForge is the durable owner of promoted rate-card snapshots. NeuroForge's
``promote_rate_card_candidate.py`` CLI is the sole writer; every consumer
(NeuroForge, Forge-Agents, Forge_Command) reads through this contract —
directly, or via DataForge_Local's read-through mirror of the same paths.

* POST /api/v1/rate-cards         — store a promoted snapshot (service-authenticated)
* GET  /api/v1/rate-cards         — list snapshots (filters: provider, model, status)
* GET  /api/v1/rate-cards/active  — the current ACTIVE snapshot for a (provider, model[, model_version])

Timestamp fields are handled as plain strings all the way through validation
and digest computation, matching the contract's own JSON-schema type (a
``Z``-suffixed string, not a native datetime) — they are parsed to/from
``datetime`` only at the DB column boundary, via ``_parse_ts``/``_iso_z``
below. This deliberately avoids routing timestamps through Pydantic's
``datetime`` type on this path: a value round-tripped through the ORM (read
back as a raw ``datetime`` from the DB) does not always re-serialize
identically to how it went in — SQLite in particular does not preserve
timezone-awareness the way Postgres does — and both the digest check and
``rate_card_overlap_errors`` compare these fields as exact strings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.database import get_db
from app.models.rate_card_models import RateCardSnapshot
from forge_contract_core.validators.cost import (
    compute_rate_card_digest,
    rate_card_overlap_errors,
)
from forge_contract_core.validators.families import (
    FamilyValidationError,
    validate_family_payload,
)

router = APIRouter(prefix="/api/v1/rate-cards", tags=["Rate Cards"])


def _parse_ts(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class RateCardSnapshotIn(BaseModel):
    schema_version: str
    id: UUID
    provider: str
    model: str
    model_version: str | None = None
    currency: str
    uncached_input_rate_micros_per_million_tokens: int | None = None
    cached_input_rate_micros_per_million_tokens: int | None = None
    cache_write_rate_micros_per_million_tokens: int | None = None
    reasoning_rate_micros_per_million_tokens: int | None = None
    output_rate_micros_per_million_tokens: int | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    status: str
    source_url: str | None = None
    retrieved_at: str
    approved_by: str | None = None
    approved_at: str | None = None
    revoked_reason: str | None = None
    superseded_by: UUID | None = None
    rounding_rule: str
    digest: str


class RateCardSnapshotOut(BaseModel):
    schema_version: str = "RateCardSnapshot.v1"
    id: UUID
    provider: str
    model: str
    model_version: str | None
    currency: str
    uncached_input_rate_micros_per_million_tokens: int | None
    cached_input_rate_micros_per_million_tokens: int | None
    cache_write_rate_micros_per_million_tokens: int | None
    reasoning_rate_micros_per_million_tokens: int | None
    output_rate_micros_per_million_tokens: int | None
    effective_from: str | None
    effective_to: str | None
    status: str
    source_url: str | None
    retrieved_at: str
    approved_by: str | None
    approved_at: str | None
    revoked_reason: str | None
    superseded_by: UUID | None
    rounding_rule: str
    digest: str


class RateCardSnapshotListResponse(BaseModel):
    items: list[RateCardSnapshotOut]
    total: int


class PublicRateCardSnapshotOut(BaseModel):
    """Deliberately reduced public projection for BDS Website pricing displays."""

    schema_version: str = "RateCardSnapshot.v1"
    provider: str
    model: str
    model_version: str | None
    currency: str
    uncached_input_rate_micros_per_million_tokens: int | None
    cached_input_rate_micros_per_million_tokens: int | None
    cache_write_rate_micros_per_million_tokens: int | None
    reasoning_rate_micros_per_million_tokens: int | None
    output_rate_micros_per_million_tokens: int | None
    effective_from: str | None
    effective_to: str | None
    rounding_rule: str


def _to_payload_dict(body: RateCardSnapshotIn) -> dict[str, Any]:
    """Serialize the incoming body to the exact JSON shape the contract validates."""
    return body.model_dump(mode="json")


def _row_to_out(row: RateCardSnapshot) -> RateCardSnapshotOut:
    return RateCardSnapshotOut(
        id=row.id,
        provider=row.provider,
        model=row.model,
        model_version=row.model_version,
        currency=row.currency,
        uncached_input_rate_micros_per_million_tokens=row.uncached_input_rate_micros_per_million_tokens,
        cached_input_rate_micros_per_million_tokens=row.cached_input_rate_micros_per_million_tokens,
        cache_write_rate_micros_per_million_tokens=row.cache_write_rate_micros_per_million_tokens,
        reasoning_rate_micros_per_million_tokens=row.reasoning_rate_micros_per_million_tokens,
        output_rate_micros_per_million_tokens=row.output_rate_micros_per_million_tokens,
        effective_from=_iso_z(row.effective_from),
        effective_to=_iso_z(row.effective_to),
        status=row.status,
        source_url=row.source_url,
        retrieved_at=_iso_z(row.retrieved_at),
        approved_by=row.approved_by,
        approved_at=_iso_z(row.approved_at),
        revoked_reason=row.revoked_reason,
        superseded_by=row.superseded_by,
        rounding_rule=row.rounding_rule,
        digest=row.digest,
    )


def _row_to_public_out(row: RateCardSnapshot) -> PublicRateCardSnapshotOut:
    return PublicRateCardSnapshotOut(
        provider=row.provider,
        model=row.model,
        model_version=row.model_version,
        currency=row.currency,
        uncached_input_rate_micros_per_million_tokens=row.uncached_input_rate_micros_per_million_tokens,
        cached_input_rate_micros_per_million_tokens=row.cached_input_rate_micros_per_million_tokens,
        cache_write_rate_micros_per_million_tokens=row.cache_write_rate_micros_per_million_tokens,
        reasoning_rate_micros_per_million_tokens=row.reasoning_rate_micros_per_million_tokens,
        output_rate_micros_per_million_tokens=row.output_rate_micros_per_million_tokens,
        effective_from=_iso_z(row.effective_from),
        effective_to=_iso_z(row.effective_to),
        rounding_rule=row.rounding_rule,
    )


@router.post("", status_code=201, response_model=RateCardSnapshotOut)
def store_rate_card(
    body: RateCardSnapshotIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),
) -> RateCardSnapshotOut:
    """Store a promoted RateCardSnapshot.v1. Upsert by id; rate-content is immutable."""
    payload = _to_payload_dict(body)

    try:
        validate_family_payload("rate_card_snapshot", 1, payload)
    except FamilyValidationError as exc:
        raise HTTPException(
            status_code=422, detail=f"rate_card_snapshot failed canonical validation: {exc.errors}"
        ) from exc

    recomputed_digest = compute_rate_card_digest(payload)
    if recomputed_digest != body.digest:
        raise HTTPException(
            status_code=422,
            detail=f"digest mismatch: declared {body.digest!r}, recomputed {recomputed_digest!r}",
        )

    existing = db.get(RateCardSnapshot, body.id)
    if existing is not None and existing.digest != body.digest:
        # The digest is computed over exactly the rate-content fields, so
        # comparing it directly is both simpler and safer than re-comparing
        # every field after a round trip through the DB.
        raise HTTPException(
            status_code=409,
            detail=f"rate-content is immutable for existing id {body.id}",
        )

    if body.status == "ACTIVE":
        sibling_query = (
            db.query(RateCardSnapshot)
            .filter(RateCardSnapshot.provider == body.provider)
            .filter(RateCardSnapshot.model == body.model)
            .filter(RateCardSnapshot.status == "ACTIVE")
        )
        if body.model_version is None:
            sibling_query = sibling_query.filter(RateCardSnapshot.model_version.is_(None))
        else:
            sibling_query = sibling_query.filter(RateCardSnapshot.model_version == body.model_version)
        siblings = [
            _row_to_out(row).model_dump(mode="json")
            for row in sibling_query.all()
            if row.id != body.id
        ]
        overlap_errors = rate_card_overlap_errors([*siblings, payload])
        if overlap_errors:
            raise HTTPException(status_code=409, detail=overlap_errors)

    if existing is not None:
        existing.status = body.status
        existing.effective_from = _parse_ts(body.effective_from)
        existing.effective_to = _parse_ts(body.effective_to)
        existing.approved_by = body.approved_by
        existing.approved_at = _parse_ts(body.approved_at)
        existing.revoked_reason = body.revoked_reason
        existing.superseded_by = body.superseded_by
        db.commit()
        return _row_to_out(existing)

    row = RateCardSnapshot(
        id=body.id,
        provider=body.provider,
        model=body.model,
        model_version=body.model_version,
        currency=body.currency,
        uncached_input_rate_micros_per_million_tokens=body.uncached_input_rate_micros_per_million_tokens,
        cached_input_rate_micros_per_million_tokens=body.cached_input_rate_micros_per_million_tokens,
        cache_write_rate_micros_per_million_tokens=body.cache_write_rate_micros_per_million_tokens,
        reasoning_rate_micros_per_million_tokens=body.reasoning_rate_micros_per_million_tokens,
        output_rate_micros_per_million_tokens=body.output_rate_micros_per_million_tokens,
        effective_from=_parse_ts(body.effective_from),
        effective_to=_parse_ts(body.effective_to),
        status=body.status,
        source_url=body.source_url,
        retrieved_at=_parse_ts(body.retrieved_at),
        approved_by=body.approved_by,
        approved_at=_parse_ts(body.approved_at),
        revoked_reason=body.revoked_reason,
        superseded_by=body.superseded_by,
        rounding_rule=body.rounding_rule,
        digest=body.digest,
    )
    db.add(row)
    db.commit()
    return _row_to_out(row)


@router.get("", response_model=RateCardSnapshotListResponse)
def list_rate_cards(
    provider: str | None = Query(None),
    model: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),
) -> RateCardSnapshotListResponse:
    q = db.query(RateCardSnapshot)
    if provider:
        q = q.filter(RateCardSnapshot.provider == provider)
    if model:
        q = q.filter(RateCardSnapshot.model == model)
    if status:
        q = q.filter(RateCardSnapshot.status == status)
    total = q.count()
    rows = (
        q.order_by(RateCardSnapshot.provider.asc(), RateCardSnapshot.model.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return RateCardSnapshotListResponse(items=[_row_to_out(r) for r in rows], total=total)


@router.get("/active", response_model=RateCardSnapshotOut)
def get_active_rate_card(
    provider: str = Query(...),
    model: str = Query(...),
    model_version: str | None = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),
) -> RateCardSnapshotOut:
    q = (
        db.query(RateCardSnapshot)
        .filter(RateCardSnapshot.provider == provider)
        .filter(RateCardSnapshot.model == model)
        .filter(RateCardSnapshot.status == "ACTIVE")
    )
    q = (
        q.filter(RateCardSnapshot.model_version.is_(None))
        if model_version is None
        else q.filter(RateCardSnapshot.model_version == model_version)
    )
    row = q.order_by(RateCardSnapshot.effective_from.desc()).first()
    if row is None:
        raise HTTPException(status_code=404, detail="no ACTIVE rate card for this provider/model")
    return _row_to_out(row)


@router.get("/public/active", response_model=PublicRateCardSnapshotOut)
def get_public_active_rate_card(
    provider: str = Query(...),
    model: str = Query(...),
    model_version: str | None = Query(None),
    db: Session = Depends(get_db),
) -> PublicRateCardSnapshotOut:
    """Public BDS Website projection; raw provenance/governance fields stay private."""
    q = (
        db.query(RateCardSnapshot)
        .filter(RateCardSnapshot.provider == provider)
        .filter(RateCardSnapshot.model == model)
        .filter(RateCardSnapshot.status == "ACTIVE")
    )
    q = (
        q.filter(RateCardSnapshot.model_version.is_(None))
        if model_version is None
        else q.filter(RateCardSnapshot.model_version == model_version)
    )
    row = q.order_by(RateCardSnapshot.effective_from.desc()).first()
    if row is None:
        raise HTTPException(status_code=404, detail="no ACTIVE rate card for this provider/model")
    return _row_to_public_out(row)

"""Model-outcome receipt store (DataForge owns durable learning state).

Append-only ground-truth code-fix outcomes. NeuroForge's Category Champion Matrix
is a replayable projection: it POSTs each outcome here (durable) and rebuilds from
GET on startup, so shadow learning survives restarts/deploys.

* POST /api/v1/model-outcomes        — store a receipt (idempotent per bundle+model+stage)
* GET  /api/v1/model-outcomes        — list receipts (replay; filter by cell/model)
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.database import get_db
from app.models.model_outcome_models import ModelOutcome

router = APIRouter(prefix="/api/v1/model-outcomes", tags=["Model Outcomes"])


class ModelOutcomeIn(BaseModel):
    context_bundle_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    routing_cell: str = Field(..., min_length=1)
    reward: float = Field(..., ge=0.0, le=1.0)
    stage: str = Field(..., min_length=1)
    tier: str | None = None
    task_intent_id: str | None = None
    family: str | None = None
    kind: str | None = None
    language: str | None = None
    complexity: str | None = None
    risk: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    source_system: str = "forgehq"
    outcome_id: str | None = None


class ModelOutcomeStored(BaseModel):
    outcome_id: str
    status: str


def _outcome_id(body: ModelOutcomeIn) -> str:
    if body.outcome_id:
        return body.outcome_id[:128]
    seed = f"{body.context_bundle_id}|{body.model_id}|{body.stage}"
    return "mo_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


@router.post("", status_code=201, response_model=ModelOutcomeStored)
def store_outcome(
    body: ModelOutcomeIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),  # P0-5: service-authenticated ingest
) -> ModelOutcomeStored:
    """Append a learning receipt. Idempotent per (bundle, model, stage) — first write wins."""
    oid = _outcome_id(body)
    if db.get(ModelOutcome, oid) is not None:
        return ModelOutcomeStored(outcome_id=oid, status="exists")
    db.add(
        ModelOutcome(
            outcome_id=oid,
            context_bundle_id=body.context_bundle_id,
            task_intent_id=body.task_intent_id,
            model_id=body.model_id,
            tier=body.tier,
            routing_cell=body.routing_cell,
            family=body.family,
            kind=body.kind,
            language=body.language,
            complexity=body.complexity,
            risk=body.risk,
            stage=body.stage,
            reward=body.reward,
            evidence_json=list(body.evidence),
            source_system=body.source_system,
        )
    )
    db.commit()
    return ModelOutcomeStored(outcome_id=oid, status="stored")


def _row(o: ModelOutcome) -> dict[str, Any]:
    created = o.created_at
    return {
        "outcome_id": o.outcome_id,
        "context_bundle_id": o.context_bundle_id,
        "task_intent_id": o.task_intent_id,
        "model_id": o.model_id,
        "tier": o.tier,
        "routing_cell": o.routing_cell,
        "family": o.family,
        "kind": o.kind,
        "language": o.language,
        "complexity": o.complexity,
        "risk": o.risk,
        "stage": o.stage,
        "reward": o.reward,
        "evidence": o.evidence_json or [],
        "source_system": o.source_system,
        "created_at": created.isoformat() if isinstance(created, datetime) else created,
    }


def _make_cursor(row: ModelOutcome) -> str:
    created = row.created_at
    created_iso = created.isoformat() if isinstance(created, datetime) else str(created)
    return f"{created_iso}|{row.outcome_id}"


def _parse_cursor(cursor: str) -> tuple[datetime, str]:
    created_iso, _, outcome_id = cursor.partition("|")
    return datetime.fromisoformat(created_iso), outcome_id


@router.get("")
def list_outcomes(
    cursor: str | None = Query(None, description="Opaque keyset cursor from a prior page's next_cursor"),
    routing_cell: str | None = Query(None),
    model_id: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),  # P0-5: authenticated replay reads
) -> dict[str, Any]:
    """List receipts for NeuroForge matrix replay — keyset-paginated (P0-8/P0-7).

    Ordered by (created_at, outcome_id) for a deterministic, monotonic projection
    cursor. ``next_cursor`` is non-null when more rows may exist; the caller pages
    until it is null. This is the append-only log NeuroForge's projector replays so
    multiple workers converge.
    """
    from sqlalchemy import and_, or_

    q = db.query(ModelOutcome)
    if routing_cell:
        q = q.filter(ModelOutcome.routing_cell == routing_cell)
    if model_id:
        q = q.filter(ModelOutcome.model_id == model_id)
    if cursor:
        after_created, after_oid = _parse_cursor(cursor)
        q = q.filter(
            or_(
                ModelOutcome.created_at > after_created,
                and_(ModelOutcome.created_at == after_created, ModelOutcome.outcome_id > after_oid),
            )
        )
    rows = (
        q.order_by(ModelOutcome.created_at.asc(), ModelOutcome.outcome_id.asc())
        .limit(limit)
        .all()
    )
    next_cursor = _make_cursor(rows[-1]) if len(rows) == limit else None
    return {"items": [_row(r) for r in rows], "count": len(rows), "next_cursor": next_cursor}

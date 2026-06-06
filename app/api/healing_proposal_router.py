"""Healing Proposal Store API.

Pending self-healing code-fix proposals (Forge_Command inbox ``LocalEventEnvelope``
bodies, ``event_class=proposal``) awaiting operator accept/reject in Forge_Command.

Flow:
* ForgeAgents/Sentinel POSTs a proposal envelope here (``status=pending``).
* The local Forge_Command bridge GETs ``status=pending`` to ingest into its inbox.
* The operator's Accept/Reject in FC PATCHes ``status`` + records a ``decision``
  receipt (the learning signal — see receipts-as-learning).

Endpoints:
* POST  /api/v1/healing-proposals          — store a proposal envelope
* GET   /api/v1/healing-proposals          — list (filter by status/repo)
* GET   /api/v1/healing-proposals/{id}     — fetch one
* PATCH /api/v1/healing-proposals/{id}     — advance status + decision receipt

Auth is optional (trusted fleet callers), mirroring the agent-memory store.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.healing_proposal_models import HealingProposalRecord

router = APIRouter(prefix="/api/v1/healing-proposals", tags=["Healing Proposals"])

_VALID_STATUS = {"pending", "ingested", "accepted", "rejected", "applied", "failed"}


class ProposalStoreResponse(BaseModel):
    proposal_id: str
    status: str
    stored_at: datetime


class ProposalSummary(BaseModel):
    proposal_id: str
    source_system: str
    repo_id: Optional[str]
    commit_sha: Optional[str]
    severity: str
    status: str
    schema_version: str
    envelope: dict[str, Any]
    decision: Optional[dict[str, Any]]
    created_at: datetime


class ProposalListResponse(BaseModel):
    items: list[ProposalSummary]
    count: int


class ProposalUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1)
    decision: Optional[dict[str, Any]] = None


def _to_summary(row: HealingProposalRecord) -> ProposalSummary:
    return ProposalSummary(
        proposal_id=row.proposal_id,
        source_system=row.source_system,
        repo_id=row.repo_id,
        commit_sha=row.commit_sha,
        severity=row.severity,
        status=row.status,
        schema_version=row.schema_version,
        envelope=row.envelope,
        decision=row.decision,
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ProposalStoreResponse)
def store_proposal(
    envelope: dict[str, Any],
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ProposalStoreResponse:
    proposal_id = envelope.get("event_id")
    if not proposal_id:
        raise HTTPException(status_code=422, detail="envelope missing required field: event_id")
    proposal_id = str(proposal_id)[:64]

    existing = (
        db.query(HealingProposalRecord)
        .filter(HealingProposalRecord.proposal_id == proposal_id)
        .first()
    )
    if existing is not None:  # idempotent ingest
        return ProposalStoreResponse(
            proposal_id=existing.proposal_id,
            status=existing.status,
            stored_at=existing.created_at,
        )

    row = HealingProposalRecord(
        proposal_id=proposal_id,
        source_system=str(envelope.get("source_system") or "unknown")[:64],
        repo_id=(str(envelope["repo_id"])[:128] if envelope.get("repo_id") else None),
        commit_sha=(str(envelope["commit_sha"])[:64] if envelope.get("commit_sha") else None),
        severity=str(envelope.get("severity") or "info")[:16],
        schema_version=str(envelope.get("schema_version") or "")[:64],
        status="pending",
        envelope=envelope,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProposalStoreResponse(
        proposal_id=row.proposal_id, status=row.status, stored_at=row.created_at
    )


@router.get("", response_model=ProposalListResponse)
def list_proposals(
    status: Optional[str] = Query(None),
    repo_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ProposalListResponse:
    q = db.query(HealingProposalRecord)
    if status:
        q = q.filter(HealingProposalRecord.status == status)
    if repo_id:
        q = q.filter(HealingProposalRecord.repo_id == repo_id)
    rows = q.order_by(HealingProposalRecord.created_at.desc()).limit(limit).all()
    items = [_to_summary(r) for r in rows]
    return ProposalListResponse(items=items, count=len(items))


@router.get("/{proposal_id}", response_model=ProposalSummary)
def get_proposal(proposal_id: str, db: Session = Depends(get_db)) -> ProposalSummary:
    row = (
        db.query(HealingProposalRecord)
        .filter(HealingProposalRecord.proposal_id == proposal_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    return _to_summary(row)


@router.patch("/{proposal_id}", response_model=ProposalSummary)
def update_proposal(
    proposal_id: str,
    body: ProposalUpdateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ProposalSummary:
    if body.status not in _VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"invalid status: {body.status}")
    row = (
        db.query(HealingProposalRecord)
        .filter(HealingProposalRecord.proposal_id == proposal_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    row.status = body.status
    if body.decision is not None:
        row.decision = body.decision
    db.commit()
    db.refresh(row)
    return _to_summary(row)

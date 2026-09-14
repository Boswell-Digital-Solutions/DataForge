"""BDS-DF-RF-001 Receipt-to-Finding Knowledge Spine -- storage surface.

Producer: Forge_Command (repo_role_matrix.json). Consumer: DataForge (storage)
and Forge_Command (review feed) -- see RFC-DF-RF-01 in forge_contract_core.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.df_rf_schemas import (
    DfRfCandidateReviewFeed,
    DfRfIngestRequest,
    DfRfIngestResponse,
)
from app.services.df_rf_ingest import (
    DfRfConflictError,
    DfRfValidationError,
    list_candidate_review_feed,
    store_df_rf_record,
)

router = APIRouter(
    prefix="/api/v1/df-rf",
    tags=["Receipt-to-Finding Knowledge Spine"],
)


@router.post(
    "",
    response_model=DfRfIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_df_rf_record(
    request: DfRfIngestRequest,
    db: Session = Depends(get_db),
) -> DfRfIngestResponse:
    """Store one df_rf_evidence_link, df_rf_finding_candidate, or df_rf_disposition
    record. Terminal candidates only (OD-02) -- there is no promotion endpoint."""
    try:
        return store_df_rf_record(db, request)
    except DfRfConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DfRfValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/review-feed", response_model=DfRfCandidateReviewFeed)
def candidate_review_feed(
    run_id: str | None = Query(default=None),
    record_family: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> DfRfCandidateReviewFeed:
    """Open finding candidates (candidate_detected/under_review) with their
    evidence links' verification status, for the Forge_Command operator review
    surface. Read-only -- disposition is applied separately."""
    items = list_candidate_review_feed(db, run_id=run_id, record_family=record_family, limit=limit)
    return DfRfCandidateReviewFeed(items=items, count=len(items))

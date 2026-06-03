"""Pending DataForge storage surface for LLM provider intelligence records."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_intel_pending_records_schemas import (
    LLMIntelCandidateReviewFeed,
    LLMIntelPendingRecordIngestRequest,
    LLMIntelPendingRecordIngestResponse,
    LLMIntelRunPendingRecordSummary,
)
from app.services.llm_intel_pending_records import (
    PendingRecordConflictError,
    PendingRecordValidationError,
    build_run_summary,
    list_candidate_review_feed,
    store_pending_record,
)

router = APIRouter(
    prefix="/api/v1/llm-intel/pending-records",
    tags=["LLM Intel Pending Records"],
)


@router.post(
    "",
    response_model=LLMIntelPendingRecordIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_pending_record(
    request: LLMIntelPendingRecordIngestRequest,
    db: Session = Depends(get_db),
) -> LLMIntelPendingRecordIngestResponse:
    """Store one pending LLM-intel record without applying promotion."""
    try:
        return store_pending_record(db, request)
    except PendingRecordConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PendingRecordValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/runs/{run_id}/summary", response_model=LLMIntelRunPendingRecordSummary)
def pending_run_summary(
    run_id: str,
    db: Session = Depends(get_db),
) -> LLMIntelRunPendingRecordSummary:
    """Return pending record ids stored for one LLM-intel weekly run."""
    return build_run_summary(db, run_id)


@router.get("/review-feed", response_model=LLMIntelCandidateReviewFeed)
def candidate_review_feed(
    run_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> LLMIntelCandidateReviewFeed:
    """Reviewable pending candidates with their drift diff and source trust, for the
    Forge_Command operator review surface. Read-only — promotion is applied separately."""
    items = list_candidate_review_feed(
        db, run_id=run_id, provider_id=provider_id, limit=limit
    )
    return LLMIntelCandidateReviewFeed(items=items, count=len(items))

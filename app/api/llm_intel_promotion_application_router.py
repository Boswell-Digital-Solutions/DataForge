"""DataForge promotion application surface for LLM provider intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_intel_pending_records_schemas import (
    LLMIntelPromotedRecordRead,
    LLMIntelPromotionApplicationResponse,
    LLMIntelPromotionDecisionApplyRequest,
)
from app.services.llm_intel_promotion_application import (
    PromotionApplicationConflictError,
    PromotionApplicationValidationError,
    apply_promotion_decision,
    get_promoted_record,
    list_promoted_records,
)


router = APIRouter(
    prefix="/api/v1/llm-intel/promotion-application",
    tags=["LLM Intel Promotion Application"],
)


@router.post(
    "/decisions/apply",
    response_model=LLMIntelPromotionApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_decision(
    request: LLMIntelPromotionDecisionApplyRequest,
    db: Session = Depends(get_db),
) -> LLMIntelPromotionApplicationResponse:
    """Validate a ForgeCommand decision receipt and apply it when approved."""
    try:
        return apply_promotion_decision(db, request)
    except PromotionApplicationConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PromotionApplicationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/promoted-records", response_model=list[LLMIntelPromotedRecordRead])
def promoted_records(
    provider_id: str | None = Query(default=None),
    record_type: str | None = Query(default=None),
    current_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[LLMIntelPromotedRecordRead]:
    """Return DataForge-promoted canonical records for read-only consumers."""
    return list_promoted_records(
        db,
        provider_id=provider_id,
        record_type=record_type,
        current_only=current_only,
    )


@router.get(
    "/promoted-records/{promoted_record_id}",
    response_model=LLMIntelPromotedRecordRead,
)
def promoted_record(
    promoted_record_id: str,
    db: Session = Depends(get_db),
) -> LLMIntelPromotedRecordRead:
    """Return one DataForge-promoted canonical record."""
    row = get_promoted_record(db, promoted_record_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promoted record not found")
    return row

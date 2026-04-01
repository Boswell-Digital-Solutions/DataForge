from __future__ import annotations

from app.models.runtime_promotion_candidate_models import RuntimePromotionCandidate
from app.services.runtime_promotion_candidate_builder import build_candidate_from_receipt
from datetime import UTC, datetime
from hashlib import sha256
import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.runtime_promotion_models import RuntimePromotionReceipt
from app.models.runtime_promotion_schemas import (
    LocalFailurePatternIngestRequest,
    RuntimePromotionIngestAck,
)

router = APIRouter(
    prefix="/api/v1/runtime-promotion",
    tags=["runtime-promotion"],
)


def _build_receipt_id(request: LocalFailurePatternIngestRequest) -> str:
    canonical_payload = {
        "envelope_type": request.envelope_type,
        "envelope_version": request.envelope_version,
        "fleet_member_id": request.fleet_member_id,
        "runtime_bundle_id": request.runtime_bundle_id,
        "runtime_bundle_version": request.runtime_bundle_version,
        "service": request.service,
        "dedupe_key": request.dedupe_key,
        "observed_at": request.observed_at.isoformat(),
        "payload": request.payload.model_dump(mode="json"),
    }
    digest = sha256(
        json.dumps(
            canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"rpr_{digest[:24]}"


def _build_ack(
    *,
    receipt_id: str,
    received_at: datetime,
) -> RuntimePromotionIngestAck:
    return RuntimePromotionIngestAck(
        receipt_id=receipt_id,
        envelope_type="local_failure_pattern",
        envelope_version="v1",
        status="accepted",
        received_at=received_at,
    )


@router.post(
    "/receipts/local-failure-pattern",
    response_model=RuntimePromotionIngestAck,
    status_code=status.HTTP_201_CREATED,
)
def ingest_local_failure_pattern(
    request: LocalFailurePatternIngestRequest,
    db: Session = Depends(get_db),
) -> RuntimePromotionIngestAck:
    received_at = datetime.now(UTC)
    receipt_id = _build_receipt_id(request)

    existing = (
        db.query(RuntimePromotionReceipt)
        .filter(RuntimePromotionReceipt.receipt_id == receipt_id)
        .first()
    )
    if existing is not None:
        existing_received_at = existing.created_at or received_at
        return _build_ack(
            receipt_id=receipt_id,
            received_at=existing_received_at,
        )

    row = RuntimePromotionReceipt(
        receipt_id=receipt_id,
        envelope_type=request.envelope_type,
        envelope_version=request.envelope_version,
        fleet_member_id=request.fleet_member_id,
        runtime_bundle_id=request.runtime_bundle_id,
        runtime_bundle_version=request.runtime_bundle_version,
        service=request.service,
        dedupe_key=request.dedupe_key,
        observed_at=request.observed_at,
        payload=request.payload.model_dump(mode="json"),
        raw_envelope=request.model_dump(mode="json"),
        ingest_status="accepted",
        source="forge_local_runtime",
        notes=None,
    )

    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_after_conflict = (
            db.query(RuntimePromotionReceipt)
            .filter(RuntimePromotionReceipt.receipt_id == receipt_id)
            .first()
        )
        if existing_after_conflict is not None:
            existing_received_at = existing_after_conflict.created_at or received_at
            return _build_ack(
                receipt_id=receipt_id,
                received_at=existing_received_at,
            )
        raise

    db.refresh(row)

    existing_candidate = (
        db.query(RuntimePromotionCandidate)
        .filter(RuntimePromotionCandidate.receipt_id == row.receipt_id)
        .first()
    )
    if existing_candidate is None:
        candidate = build_candidate_from_receipt(row)
        db.add(candidate)
        db.commit()

    row_received_at = row.created_at or received_at
    return _build_ack(
        receipt_id=receipt_id,
        received_at=row_received_at,
    )
    if existing_candidate is None:
        candidate = build_candidate_from_receipt(row)
        db.add(candidate)
        db.commit()

    row_received_at = row.created_at or received_at
    return _build_ack(
        receipt_id=receipt_id,
        received_at=row_received_at,
    )
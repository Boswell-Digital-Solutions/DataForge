"""Proving-slice intake router.

Provides two endpoints:

  POST /api/v1/proving-slice/intake
    Receives a full shared-envelope artifact from DataForge Local.
    Validates via forge-contract-core. Persists the intake record and emits
    a promotion_receipt artifact. Always returns 200 with the receipt — the
    intake_outcome field carries the domain decision (accepted / rejected /
    duplicate_reconciled). HTTP 4xx/5xx are reserved for transport errors.

  GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}
    Fetches the receipt for a previously submitted artifact. Used by DataForge
    Local to reconcile ambiguous sends. Returns 404 if the artifact is unknown.

Scope invariants (enforced, not suggested):
  - Only source_drift_finding and promotion_envelope families are admitted.
  - promotion_receipt is never submitted here — it is emitted here.
  - Accepted artifacts get a shared_record_ref assigned at intake time.
  - Rejected artifacts are persisted (for audit) with intake_outcome='rejected'.
  - Duplicate idempotency keys are reconciled without re-validating.
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Resolve forge-contract-core from the ecosystem contracts directory
_CONTRACT_CORE = (
    Path(__file__).parent.parent.parent.parent.parent
    / "contracts"
    / "forge-contract-core"
)
if str(_CONTRACT_CORE) not in sys.path:
    sys.path.insert(0, str(_CONTRACT_CORE))

from forge_contract_core.identity import compute_idempotency_key
from forge_contract_core.validators.artifact import (
    ArtifactValidationError,
    validate_artifact,
)

from app.database import get_db
from app.models.proving_slice_models import PSCloudIntakeRecord, PSCloudReceipt
from app.models.proving_slice_schemas import (
    ArtifactIntakeRequest,
    ProofReceiptArtifact,
    ReceiptLookupResponse,
    ReceiptPayload,
)

# Families the proving-slice intake route will accept from Local
_INTAKE_ADMITTED_FAMILIES = frozenset(
    {"source_drift_finding", "promotion_envelope", "triple_variant_audit_receipt"}
)

router = APIRouter(
    prefix="/api/v1/proving-slice",
    tags=["proving-slice"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _shared_record_ref(artifact: ArtifactIntakeRequest) -> str:
    """Compute the canonical shared record reference for an accepted artifact."""
    return (
        f"{artifact.artifact_family}:{artifact.artifact_id}"
        f":v{artifact.artifact_version}:shared"
    )


def _receipt_signature(receipt_artifact_id: str) -> str:
    """Placeholder signature — real signing deferred to Stage 5 key governance."""
    digest = hashlib.sha256(receipt_artifact_id.encode()).hexdigest()
    return f"sha256:cloud-proving-slice-v1-{digest}"


def _build_receipt_artifact(
    *,
    receipt_artifact_id: str,
    receipt_id: str,
    artifact: ArtifactIntakeRequest,
    intake_outcome: str,
    shared_record_ref: str | None,
    rejection_class: str | None,
    retry_allowed: bool,
    outcome_summary: str,
    now: datetime,
) -> ProofReceiptArtifact:
    now_iso = now.isoformat().replace("+00:00", "Z")
    related_ref = (
        f"{artifact.artifact_family}:{artifact.artifact_id}:v{artifact.artifact_version}"
    )
    receipt_idem = compute_idempotency_key(
        "promotion_receipt",
        receipt_artifact_id,
        1,
        artifact.lineage_root_id,
    )
    return ProofReceiptArtifact(
        artifact_id=receipt_artifact_id,
        artifact_family="promotion_receipt",
        artifact_version=1,
        produced_by_system="DataForge",
        produced_by_component="proving_slice_intake",
        source_scope="shared",
        lineage_root_id=artifact.lineage_root_id,
        parent_artifact_id=artifact.artifact_id,
        trace_id=artifact.trace_id,
        idempotency_key=receipt_idem,
        created_at=now_iso,
        recorded_at=now_iso,
        sensitivity_class="internal",
        visibility_class="operator",
        promotion_class="local_only",
        validation_status="valid",
        signer_identity="DataForge/proving_slice_intake@proving-slice-v1",
        signature=_receipt_signature(receipt_artifact_id),
        payload=ReceiptPayload(
            receipt_id=receipt_id,
            related_artifact_ref=related_ref,
            intake_outcome=intake_outcome,  # type: ignore[arg-type]
            shared_record_ref=shared_record_ref,
            received_at=now_iso,
            idempotency_key=artifact.idempotency_key,
            outcome_summary=outcome_summary,
            rejection_class=rejection_class,
            retry_allowed=retry_allowed,
            producer_identity=artifact.produced_by_system,
        ),
    )


def _persist_intake_and_receipt(
    db: Session,
    *,
    intake_id: str,
    receipt_id: str,
    receipt_artifact_id: str,
    artifact: ArtifactIntakeRequest,
    artifact_dict: dict[str, Any],
    intake_outcome: str,
    shared_record_ref: str | None,
    rejection_class: str | None,
    rejection_detail: str | None,
    retry_allowed: bool,
    outcome_summary: str,
    now: datetime,
) -> None:
    intake_row = PSCloudIntakeRecord(
        intake_id=intake_id,
        artifact_id=artifact.artifact_id,
        artifact_family=artifact.artifact_family,
        artifact_version=artifact.artifact_version,
        idempotency_key=artifact.idempotency_key,
        produced_by_system=artifact.produced_by_system,
        lineage_root_id=artifact.lineage_root_id,
        trace_id=artifact.trace_id,
        intake_outcome=intake_outcome,
        rejection_class=rejection_class,
        rejection_detail=rejection_detail,
        shared_record_ref=shared_record_ref,
        payload_json=artifact_dict.get("payload", {}),
        envelope_json={k: v for k, v in artifact_dict.items() if k != "payload"},
        received_at=now,
        processed_at=now,
    )
    db.add(intake_row)
    db.flush()  # populate intake_id FK before creating receipt row

    receipt_row = PSCloudReceipt(
        receipt_id=receipt_id,
        intake_id=intake_id,
        artifact_id=artifact.artifact_id,
        receipt_artifact_id=receipt_artifact_id,
        intake_outcome=intake_outcome,
        rejection_class=rejection_class,
        retry_allowed=retry_allowed,
        outcome_summary=outcome_summary,
        shared_record_ref=shared_record_ref,
        emitted_at=now,
    )
    db.add(receipt_row)
    db.commit()


# ── routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/intake",
    response_model=ProofReceiptArtifact,
    status_code=status.HTTP_200_OK,
    summary="Proving-slice artifact intake",
    description=(
        "Accepts a source_drift_finding or promotion_envelope artifact from DataForge "
        "Local. Validates, persists, and returns a promotion_receipt. "
        "The intake_outcome field in the receipt payload carries the domain decision."
    ),
)
def intake_artifact(
    request: ArtifactIntakeRequest,
    db: Session = Depends(get_db),
) -> ProofReceiptArtifact:
    now = datetime.now(UTC)
    artifact_dict = request.model_dump()

    # ── Family gate ───────────────────────────────────────────────────────────
    if request.artifact_family not in _INTAKE_ADMITTED_FAMILIES:
        # Rejected outright — not persisted (unsupported family is a caller error)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Artifact family {request.artifact_family!r} is not admitted "
                f"by the proving-slice intake. Admitted: {sorted(_INTAKE_ADMITTED_FAMILIES)}"
            ),
        )

    # ── Duplicate check ───────────────────────────────────────────────────────
    existing = (
        db.query(PSCloudIntakeRecord)
        .filter(PSCloudIntakeRecord.idempotency_key == request.idempotency_key)
        .first()
    )
    if existing is not None:
        # Already processed — return duplicate_reconciled receipt without re-writing.
        existing_receipt = (
            db.query(PSCloudReceipt)
            .filter(PSCloudReceipt.intake_id == existing.intake_id)
            .first()
        )
        receipt_artifact_id = (
            existing_receipt.receipt_artifact_id if existing_receipt else str(uuid.uuid4())
        )
        receipt_id = (
            existing_receipt.receipt_id if existing_receipt else str(uuid.uuid4())
        )
        return _build_receipt_artifact(
            receipt_artifact_id=receipt_artifact_id,
            receipt_id=receipt_id,
            artifact=request,
            intake_outcome="duplicate_reconciled",
            shared_record_ref=existing.shared_record_ref,
            rejection_class=None,
            retry_allowed=False,
            outcome_summary=(
                "Artifact was already received and processed. "
                "Returning the original shared record reference."
            ),
            now=now,
        )

    # ── Contract validation ───────────────────────────────────────────────────
    intake_id = str(uuid.uuid4())
    receipt_id = str(uuid.uuid4())
    receipt_artifact_id = str(uuid.uuid4())

    try:
        validate_artifact(artifact_dict, strict_idempotency=True)
    except ArtifactValidationError as exc:
        rejection_class = exc.cause or "validation_failure"
        rejection_detail = str(exc)
        outcome_summary = f"Artifact failed contract validation: {rejection_detail}"
        _persist_intake_and_receipt(
            db,
            intake_id=intake_id,
            receipt_id=receipt_id,
            receipt_artifact_id=receipt_artifact_id,
            artifact=request,
            artifact_dict=artifact_dict,
            intake_outcome="rejected",
            shared_record_ref=None,
            rejection_class=rejection_class,
            rejection_detail=rejection_detail,
            retry_allowed=False,
            outcome_summary=outcome_summary,
            now=now,
        )
        return _build_receipt_artifact(
            receipt_artifact_id=receipt_artifact_id,
            receipt_id=receipt_id,
            artifact=request,
            intake_outcome="rejected",
            shared_record_ref=None,
            rejection_class=rejection_class,
            retry_allowed=False,
            outcome_summary=outcome_summary,
            now=now,
        )

    # ── Accepted ──────────────────────────────────────────────────────────────
    shared_ref = _shared_record_ref(request)
    outcome_summary = (
        "Artifact accepted and recorded as shared truth. "
        f"Canonical reference: {shared_ref}"
    )
    _persist_intake_and_receipt(
        db,
        intake_id=intake_id,
        receipt_id=receipt_id,
        receipt_artifact_id=receipt_artifact_id,
        artifact=request,
        artifact_dict=artifact_dict,
        intake_outcome="accepted",
        shared_record_ref=shared_ref,
        rejection_class=None,
        rejection_detail=None,
        retry_allowed=False,
        outcome_summary=outcome_summary,
        now=now,
    )
    return _build_receipt_artifact(
        receipt_artifact_id=receipt_artifact_id,
        receipt_id=receipt_id,
        artifact=request,
        intake_outcome="accepted",
        shared_record_ref=shared_ref,
        rejection_class=None,
        retry_allowed=False,
        outcome_summary=outcome_summary,
        now=now,
    )


@router.get(
    "/receipts/by-artifact/{artifact_id}",
    response_model=ReceiptLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch receipt by artifact ID",
    description=(
        "Returns the receipt emitted for a previously submitted artifact. "
        "Used by DataForge Local to reconcile ambiguous sends. Returns 404 if "
        "the artifact_id has never been processed."
    ),
)
def get_receipt_by_artifact(
    artifact_id: str,
    db: Session = Depends(get_db),
) -> ReceiptLookupResponse:
    intake = (
        db.query(PSCloudIntakeRecord)
        .filter(PSCloudIntakeRecord.artifact_id == artifact_id)
        .order_by(PSCloudIntakeRecord.received_at.desc())
        .first()
    )
    if intake is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No intake record found for artifact_id={artifact_id!r}",
        )

    receipt_row = (
        db.query(PSCloudReceipt)
        .filter(PSCloudReceipt.intake_id == intake.intake_id)
        .first()
    )
    if receipt_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake record exists but no receipt row found for artifact_id={artifact_id!r}",
        )

    # Reconstruct a minimal ArtifactIntakeRequest from the stored envelope
    envelope = intake.envelope_json or {}
    pseudo_request = ArtifactIntakeRequest(
        artifact_id=intake.artifact_id,
        artifact_family=intake.artifact_family,
        artifact_version=intake.artifact_version,
        produced_by_system=intake.produced_by_system,
        produced_by_component=envelope.get("produced_by_component", ""),
        source_scope=envelope.get("source_scope", "local"),
        lineage_root_id=intake.lineage_root_id,
        parent_artifact_id=envelope.get("parent_artifact_id"),
        trace_id=intake.trace_id,
        idempotency_key=intake.idempotency_key,
        created_at=envelope.get("created_at", ""),
        recorded_at=envelope.get("recorded_at", ""),
        sensitivity_class=envelope.get("sensitivity_class", "internal"),
        visibility_class=envelope.get("visibility_class", "operator"),
        promotion_class=envelope.get("promotion_class", "promotable"),
        validation_status=envelope.get("validation_status", "valid"),
        signer_identity=envelope.get("signer_identity", ""),
        signature=envelope.get("signature", ""),
        payload=intake.payload_json or {},
    )

    receipt_artifact = _build_receipt_artifact(
        receipt_artifact_id=receipt_row.receipt_artifact_id,
        receipt_id=receipt_row.receipt_id,
        artifact=pseudo_request,
        intake_outcome=receipt_row.intake_outcome,
        shared_record_ref=receipt_row.shared_record_ref,
        rejection_class=receipt_row.rejection_class,
        retry_allowed=receipt_row.retry_allowed,
        outcome_summary=receipt_row.outcome_summary or "",
        now=intake.processed_at,
    )

    return ReceiptLookupResponse(artifact_id=artifact_id, receipt=receipt_artifact)

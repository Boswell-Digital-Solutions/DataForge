"""Pending LLM intelligence evidence storage.

DataForge owns durable pending evidence for the weekly LLM-intel workflow. This
module stores immutable receipts, source fingerprints, extracted claims, drift
reports, replay manifests, and mutable pending candidates. It does not apply
promotion decisions or mutate promoted provider registry truth.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.llm_intel_pending_records_models import (
    LLMIntelDriftReportRecord,
    LLMIntelExtractedClaimRecord,
    LLMIntelPendingCandidateRecord,
    LLMIntelReceiptRecord,
    LLMIntelReplayManifestRecord,
    LLMIntelSourceFingerprintRecord,
)
from app.models.llm_intel_pending_records_schemas import (
    LLMIntelCandidateReviewItem,
    LLMIntelPendingRecordIngestRequest,
    LLMIntelPendingRecordIngestResponse,
    LLMIntelRunPendingRecordSummary,
)
from app.services.llm_intel_source_trust import (
    LLM_PROVIDER_IDS,
    OFFICIAL_REQUIRED_CLAIM_TYPES,
)
from forge_contract_core.validators.families import (
    FamilyValidationError,
    validate_family_payload,
)


CONTRACT_RECORD_FAMILIES = {
    "llm_intel_fetch_receipts": ("llm_intel_fetch_receipt", "fetch_receipt_id"),
    "llm_intel_provider_adapter_receipts": ("provider_adapter_receipt", "receipt_id"),
    "llm_intel_source_fingerprints": ("llm_intel_source_fingerprint", "fingerprint_id"),
    "llm_intel_extracted_claims": ("llm_intel_extracted_claim", "claim_id"),
    "llm_intel_drift_reports": ("llm_intel_drift_report", "drift_report_id"),
}

CANDIDATE_RECORD_FAMILIES = {
    "llm_intel_model_candidates": "model",
    "llm_intel_pricing_candidates": "pricing",
    "llm_intel_capability_candidates": "capability",
}

BLOCKED_PENDING_PROMOTION_STATES = frozenset(
    {
        "approved_for_promotion",
        "promoted",
        "superseded",
        "rollback_requested",
        "rollback_completed",
        "archived",
    }
)

# Candidate promotion states still open for operator review in Forge_Command.
REVIEWABLE_CANDIDATE_STATES = frozenset(
    {
        "candidate_detected",
        "evidence_collected",
        "drift_classified",
        "more_evidence_required",
        "deferred",
    }
)


class PendingRecordValidationError(ValueError):
    """Raised when a pending LLM-intel record cannot be stored."""


class PendingRecordConflictError(ValueError):
    """Raised when a record id would overwrite a different payload."""


def store_pending_record(
    db: Session,
    request: LLMIntelPendingRecordIngestRequest,
) -> LLMIntelPendingRecordIngestResponse:
    record_family = request.record_family
    payload = request.payload
    payload_hash = stable_hash(payload)

    if record_family == "llm_intel_fetch_receipts":
        return _store_fetch_receipt(db, record_family, payload, payload_hash)
    if record_family == "llm_intel_provider_adapter_receipts":
        return _store_provider_adapter_receipt(db, record_family, payload, payload_hash)
    if record_family == "llm_intel_source_fingerprints":
        return _store_source_fingerprint(db, record_family, payload, payload_hash, request.run_id)
    if record_family == "llm_intel_extracted_claims":
        return _store_extracted_claim(db, record_family, payload, payload_hash)
    if record_family in CANDIDATE_RECORD_FAMILIES:
        return _store_candidate(db, record_family, payload, payload_hash)
    if record_family == "llm_intel_drift_reports":
        return _store_drift_report(db, record_family, payload, payload_hash)
    if record_family == "llm_intel_replay_manifests":
        return _store_replay_manifest(db, record_family, payload, payload_hash)

    raise PendingRecordValidationError(f"unsupported record_family {record_family!r}")


def build_run_summary(db: Session, run_id: str) -> LLMIntelRunPendingRecordSummary:
    receipts = (
        db.query(LLMIntelReceiptRecord)
        .filter(LLMIntelReceiptRecord.run_id == run_id)
        .order_by(LLMIntelReceiptRecord.receipt_id.asc())
        .all()
    )
    fingerprints = (
        db.query(LLMIntelSourceFingerprintRecord)
        .filter(LLMIntelSourceFingerprintRecord.run_id == run_id)
        .order_by(LLMIntelSourceFingerprintRecord.fingerprint_id.asc())
        .all()
    )
    claims = (
        db.query(LLMIntelExtractedClaimRecord)
        .filter(LLMIntelExtractedClaimRecord.run_id == run_id)
        .order_by(LLMIntelExtractedClaimRecord.claim_id.asc())
        .all()
    )
    candidates = (
        db.query(LLMIntelPendingCandidateRecord)
        .filter(LLMIntelPendingCandidateRecord.run_id == run_id)
        .order_by(LLMIntelPendingCandidateRecord.candidate_id.asc())
        .all()
    )
    drift_reports = (
        db.query(LLMIntelDriftReportRecord)
        .filter(LLMIntelDriftReportRecord.run_id == run_id)
        .order_by(LLMIntelDriftReportRecord.drift_report_id.asc())
        .all()
    )
    replay_manifests = (
        db.query(LLMIntelReplayManifestRecord)
        .filter(LLMIntelReplayManifestRecord.run_id == run_id)
        .order_by(LLMIntelReplayManifestRecord.replay_manifest_id.asc())
        .all()
    )

    return LLMIntelRunPendingRecordSummary(
        run_id=run_id,
        record_counts={
            "llm_intel_receipts": len(receipts),
            "llm_intel_source_fingerprints": len(fingerprints),
            "llm_intel_extracted_claims": len(claims),
            "llm_intel_pending_candidates": len(candidates),
            "llm_intel_drift_reports": len(drift_reports),
            "llm_intel_replay_manifests": len(replay_manifests),
        },
        receipt_ids=[row.receipt_id for row in receipts],
        source_fingerprint_ids=[row.fingerprint_id for row in fingerprints],
        claim_ids=[row.claim_id for row in claims],
        candidate_ids=[row.candidate_id for row in candidates],
        drift_report_ids=[row.drift_report_id for row in drift_reports],
        replay_manifest_ids=[row.replay_manifest_id for row in replay_manifests],
    )


def list_candidate_review_feed(
    db: Session,
    *,
    run_id: str | None = None,
    provider_id: str | None = None,
    states: set[str] | None = None,
    limit: int = 200,
) -> list[LLMIntelCandidateReviewItem]:
    """Return reviewable pending candidates enriched with their drift diff (old/new),
    impact class, and source trust — the read model for the Forge_Command operator
    review surface. Read-only: this never changes promotion state."""
    review_states = set(states) if states else set(REVIEWABLE_CANDIDATE_STATES)
    query = db.query(LLMIntelPendingCandidateRecord).filter(
        LLMIntelPendingCandidateRecord.promotion_state.in_(review_states)
    )
    if run_id:
        query = query.filter(LLMIntelPendingCandidateRecord.run_id == run_id)
    if provider_id:
        query = query.filter(LLMIntelPendingCandidateRecord.provider_id == provider_id)
    candidates = (
        query.order_by(
            LLMIntelPendingCandidateRecord.created_at.desc(),
            LLMIntelPendingCandidateRecord.candidate_id.asc(),
        )
        .limit(limit)
        .all()
    )
    if not candidates:
        return []

    candidate_ids = [row.candidate_id for row in candidates]
    drift_by_candidate: dict[str, LLMIntelDriftReportRecord] = {}
    for drift in (
        db.query(LLMIntelDriftReportRecord)
        .filter(LLMIntelDriftReportRecord.candidate_id.in_(candidate_ids))
        .all()
    ):
        # One drift report per candidate in the weekly flow; keep the first seen.
        drift_by_candidate.setdefault(drift.candidate_id, drift)

    fingerprint_ids: set[str] = set()
    for row in candidates:
        fingerprint_ids.update(row.source_fingerprint_ids or [])
    fingerprint_by_id: dict[str, LLMIntelSourceFingerprintRecord] = {}
    if fingerprint_ids:
        for fingerprint in (
            db.query(LLMIntelSourceFingerprintRecord)
            .filter(LLMIntelSourceFingerprintRecord.fingerprint_id.in_(fingerprint_ids))
            .all()
        ):
            fingerprint_by_id[fingerprint.fingerprint_id] = fingerprint

    items: list[LLMIntelCandidateReviewItem] = []
    for row in candidates:
        drift = drift_by_candidate.get(row.candidate_id)
        fingerprints = [
            fingerprint_by_id[fid]
            for fid in (row.source_fingerprint_ids or [])
            if fid in fingerprint_by_id
        ]
        trust_classes = sorted({fp.trust_class for fp in fingerprints})
        source_urls = sorted(
            {
                url
                for fp in fingerprints
                if isinstance((url := (fp.payload or {}).get("source_url")), str) and url
            }
        )
        items.append(
            LLMIntelCandidateReviewItem(
                candidate_id=row.candidate_id,
                run_id=row.run_id,
                provider_id=row.provider_id,
                candidate_type=row.candidate_type,
                claim_type=row.claim_type,
                claim_path=row.claim_path,
                promotion_state=row.promotion_state,
                candidate_value=(row.payload or {}).get("candidate_value", {}),
                old_value=(drift.payload or {}).get("old_value") if drift else None,
                impact_class=drift.impact_class if drift else None,
                drift_report_id=drift.drift_report_id if drift else None,
                review_packet_id=f"review-{row.candidate_id}",
                source_fingerprint_ids=list(row.source_fingerprint_ids or []),
                trust_classes=trust_classes,
                source_urls=source_urls,
                has_official_source=any(tc == "OFFICIAL" for tc in trust_classes),
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        )
    return items


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _store_fetch_receipt(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    _validate_contract_payload(record_family, payload)
    receipt_id = _require_string(payload, "fetch_receipt_id")
    existing = _existing_receipt(db, receipt_id)
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=receipt_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelReceiptRecord(
        receipt_id=receipt_id,
        record_family=record_family,
        run_id=_require_string(payload, "run_id"),
        provider_id=_require_provider_id(payload),
        source_id=_optional_string(payload, "source_id"),
        adapter_id=None,
        receipt_status=_require_string(payload, "fetch_status"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, receipt_id, row.run_id, row.provider_id, payload_hash)


def _store_provider_adapter_receipt(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    _validate_contract_payload(record_family, payload)
    receipt_id = _require_string(payload, "receipt_id")
    _require_source_fingerprints(db, [_require_string(payload, "source_fingerprint_id")])
    existing = _existing_receipt(db, receipt_id)
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=receipt_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelReceiptRecord(
        receipt_id=receipt_id,
        record_family=record_family,
        run_id=_require_string(payload, "run_id"),
        provider_id=_require_provider_id(payload),
        source_id=None,
        adapter_id=_require_string(payload, "adapter_id"),
        receipt_status=_require_string(payload, "status"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, receipt_id, row.run_id, row.provider_id, payload_hash)


def _store_source_fingerprint(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
    run_id: str | None,
) -> LLMIntelPendingRecordIngestResponse:
    _validate_contract_payload(record_family, payload)
    fingerprint_id = _require_string(payload, "fingerprint_id")
    existing = (
        db.query(LLMIntelSourceFingerprintRecord)
        .filter(LLMIntelSourceFingerprintRecord.fingerprint_id == fingerprint_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=fingerprint_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelSourceFingerprintRecord(
        fingerprint_id=fingerprint_id,
        run_id=run_id,
        source_id=_require_string(payload, "source_id"),
        provider_id=_require_provider_id(payload),
        trust_class=_require_string(payload, "trust_class"),
        content_hash=_require_string(payload, "content_hash"),
        adapter_id=_require_string(payload, "adapter_id"),
        adapter_version=_require_string(payload, "adapter_version"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, fingerprint_id, row.run_id, row.provider_id, payload_hash)


def _store_extracted_claim(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    _validate_contract_payload(record_family, payload)
    claim_id = _require_string(payload, "claim_id")
    existing = (
        db.query(LLMIntelExtractedClaimRecord)
        .filter(LLMIntelExtractedClaimRecord.claim_id == claim_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=claim_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelExtractedClaimRecord(
        claim_id=claim_id,
        run_id=_require_string(payload, "run_id"),
        provider_id=_require_provider_id(payload),
        claim_type=_require_string(payload, "claim_type"),
        claim_path=_require_string(payload, "claim_path"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, claim_id, row.run_id, row.provider_id, payload_hash)


def _store_candidate(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    candidate_id = _require_string(payload, "candidate_id")
    run_id = _require_string(payload, "run_id")
    provider_id = _require_provider_id(payload)
    claim_type = _require_string(payload, "claim_type")
    claim_path = _require_string(payload, "claim_path")
    promotion_state = _require_string(payload, "promotion_state")
    candidate_type = _require_string(payload, "candidate_type")

    expected_candidate_type = CANDIDATE_RECORD_FAMILIES[record_family]
    if candidate_type != expected_candidate_type:
        raise PendingRecordValidationError(
            f"{record_family} requires candidate_type {expected_candidate_type!r}"
        )
    if promotion_state in BLOCKED_PENDING_PROMOTION_STATES:
        raise PendingRecordValidationError(
            f"pending candidate cannot enter state {promotion_state!r}"
        )

    source_fingerprint_ids = _require_string_list(payload, "source_fingerprint_ids")
    receipt_ids = _require_string_list(payload, "receipt_ids")
    claim_ids = _optional_string_list(payload, "claim_ids")
    if not isinstance(payload.get("candidate_value"), dict):
        raise PendingRecordValidationError("candidate_value is required")

    fingerprint_rows = _require_source_fingerprints(db, source_fingerprint_ids)
    _require_receipts(db, receipt_ids)
    if claim_ids:
        _require_claims(db, claim_ids)
    if claim_type in OFFICIAL_REQUIRED_CLAIM_TYPES and not any(
        row.trust_class == "OFFICIAL" for row in fingerprint_rows
    ):
        raise PendingRecordValidationError(
            f"{claim_type} candidates require OFFICIAL source fingerprint evidence"
        )

    existing = (
        db.query(LLMIntelPendingCandidateRecord)
        .filter(LLMIntelPendingCandidateRecord.candidate_id == candidate_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=candidate_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelPendingCandidateRecord(
        candidate_id=candidate_id,
        record_family=record_family,
        run_id=run_id,
        provider_id=provider_id,
        candidate_type=candidate_type,
        claim_type=claim_type,
        claim_path=claim_path,
        promotion_state=promotion_state,
        source_fingerprint_ids=source_fingerprint_ids,
        receipt_ids=receipt_ids,
        claim_ids=claim_ids,
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, candidate_id, run_id, provider_id, payload_hash)


def _store_drift_report(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    _validate_contract_payload(record_family, payload)
    drift_report_id = _require_string(payload, "drift_report_id")
    candidate_id = _require_string(payload, "candidate_id")
    _require_candidates(db, [candidate_id])

    existing = (
        db.query(LLMIntelDriftReportRecord)
        .filter(LLMIntelDriftReportRecord.drift_report_id == drift_report_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=drift_report_id,
            run_id=existing.run_id,
            provider_id=existing.provider_id,
        )

    row = LLMIntelDriftReportRecord(
        drift_report_id=drift_report_id,
        run_id=_require_string(payload, "run_id"),
        provider_id=_require_provider_id(payload),
        candidate_id=candidate_id,
        drift_type=_require_string(payload, "drift_type"),
        impact_class=_require_string(payload, "impact_class"),
        requires_maid=bool(payload["requires_maid"]),
        conflict_status=_require_string(payload, "conflict_status"),
        promotion_state=_require_string(payload, "promotion_state"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, drift_report_id, row.run_id, row.provider_id, payload_hash)


def _store_replay_manifest(
    db: Session,
    record_family: str,
    payload: dict[str, Any],
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    _require_schema_version(payload, "llm_intel.replay_manifest.v1")
    replay_manifest_id = _require_string(payload, "replay_manifest_id")
    run_id = _require_string(payload, "run_id")
    _require_string(payload, "manifest_status")
    _require_hash(payload, "input_manifest_hash")
    _require_hash(payload, "replay_determinism_hash")
    output_manifest_hash = _optional_string(payload, "output_manifest_hash")
    if output_manifest_hash is not None:
        _require_hash(payload, "output_manifest_hash")

    source_fingerprint_ids = _require_string_list(payload, "source_fingerprint_ids")
    fetch_receipt_ids = _require_string_list(payload, "fetch_receipt_ids")
    adapter_receipt_ids = _require_string_list(payload, "adapter_receipt_ids")
    claim_ids = _require_string_list(payload, "claim_ids")
    candidate_ids = _require_string_list(payload, "candidate_ids")
    drift_report_ids = _require_string_list(payload, "drift_report_ids")

    _require_source_fingerprints(db, source_fingerprint_ids)
    _require_receipts(db, fetch_receipt_ids)
    _require_receipts(db, adapter_receipt_ids)
    _require_claims(db, claim_ids)
    _require_candidates(db, candidate_ids)
    _require_drift_reports(db, drift_report_ids)

    existing = (
        db.query(LLMIntelReplayManifestRecord)
        .filter(LLMIntelReplayManifestRecord.replay_manifest_id == replay_manifest_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing_hash=existing.payload_hash,
            payload_hash=payload_hash,
            record_family=record_family,
            record_id=replay_manifest_id,
            run_id=existing.run_id,
            provider_id=None,
        )

    row = LLMIntelReplayManifestRecord(
        replay_manifest_id=replay_manifest_id,
        run_id=run_id,
        manifest_status=_require_string(payload, "manifest_status"),
        input_manifest_hash=_require_string(payload, "input_manifest_hash"),
        output_manifest_hash=output_manifest_hash,
        replay_determinism_hash=_require_string(payload, "replay_determinism_hash"),
        source_fingerprint_ids=source_fingerprint_ids,
        fetch_receipt_ids=fetch_receipt_ids,
        adapter_receipt_ids=adapter_receipt_ids,
        claim_ids=claim_ids,
        candidate_ids=candidate_ids,
        drift_report_ids=drift_report_ids,
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return _stored(record_family, replay_manifest_id, run_id, None, payload_hash)


def _validate_contract_payload(record_family: str, payload: dict[str, Any]) -> None:
    family, _ = CONTRACT_RECORD_FAMILIES[record_family]
    try:
        validate_family_payload(family, 1, payload)
    except FamilyValidationError as exc:
        raise PendingRecordValidationError(
            f"{record_family} failed canonical validation: {exc.errors}"
        ) from exc


def _existing_receipt(db: Session, receipt_id: str) -> LLMIntelReceiptRecord | None:
    return (
        db.query(LLMIntelReceiptRecord)
        .filter(LLMIntelReceiptRecord.receipt_id == receipt_id)
        .first()
    )


def _require_source_fingerprints(
    db: Session,
    fingerprint_ids: list[str],
) -> list[LLMIntelSourceFingerprintRecord]:
    rows = (
        db.query(LLMIntelSourceFingerprintRecord)
        .filter(LLMIntelSourceFingerprintRecord.fingerprint_id.in_(fingerprint_ids))
        .all()
    )
    found = {row.fingerprint_id for row in rows}
    missing = sorted(set(fingerprint_ids) - found)
    if missing:
        raise PendingRecordValidationError(f"missing source fingerprint(s): {missing}")
    return rows


def _require_receipts(db: Session, receipt_ids: list[str]) -> None:
    rows = (
        db.query(LLMIntelReceiptRecord)
        .filter(LLMIntelReceiptRecord.receipt_id.in_(receipt_ids))
        .all()
    )
    found = {row.receipt_id for row in rows}
    missing = sorted(set(receipt_ids) - found)
    if missing:
        raise PendingRecordValidationError(f"missing receipt(s): {missing}")


def _require_claims(db: Session, claim_ids: list[str]) -> None:
    rows = (
        db.query(LLMIntelExtractedClaimRecord)
        .filter(LLMIntelExtractedClaimRecord.claim_id.in_(claim_ids))
        .all()
    )
    found = {row.claim_id for row in rows}
    missing = sorted(set(claim_ids) - found)
    if missing:
        raise PendingRecordValidationError(f"missing extracted claim(s): {missing}")


def _require_candidates(db: Session, candidate_ids: list[str]) -> None:
    rows = (
        db.query(LLMIntelPendingCandidateRecord)
        .filter(LLMIntelPendingCandidateRecord.candidate_id.in_(candidate_ids))
        .all()
    )
    found = {row.candidate_id for row in rows}
    missing = sorted(set(candidate_ids) - found)
    if missing:
        raise PendingRecordValidationError(f"missing candidate(s): {missing}")


def _require_drift_reports(db: Session, drift_report_ids: list[str]) -> None:
    rows = (
        db.query(LLMIntelDriftReportRecord)
        .filter(LLMIntelDriftReportRecord.drift_report_id.in_(drift_report_ids))
        .all()
    )
    found = {row.drift_report_id for row in rows}
    missing = sorted(set(drift_report_ids) - found)
    if missing:
        raise PendingRecordValidationError(f"missing drift report(s): {missing}")


def _duplicate_or_conflict(
    *,
    existing_hash: str,
    payload_hash: str,
    record_family: str,
    record_id: str,
    run_id: str | None,
    provider_id: str | None,
) -> LLMIntelPendingRecordIngestResponse:
    if existing_hash != payload_hash:
        raise PendingRecordConflictError(
            f"{record_family} record {record_id!r} already exists with different payload"
        )
    return LLMIntelPendingRecordIngestResponse(
        record_family=record_family,
        record_id=record_id,
        run_id=run_id,
        provider_id=provider_id,
        payload_hash=payload_hash,
        storage_status="duplicate",
    )


def _stored(
    record_family: str,
    record_id: str,
    run_id: str | None,
    provider_id: str | None,
    payload_hash: str,
) -> LLMIntelPendingRecordIngestResponse:
    return LLMIntelPendingRecordIngestResponse(
        record_family=record_family,
        record_id=record_id,
        run_id=run_id,
        provider_id=provider_id,
        payload_hash=payload_hash,
        storage_status="stored",
    )


def _require_schema_version(payload: dict[str, Any], expected: str) -> None:
    if payload.get("schema_version") != expected:
        raise PendingRecordValidationError(f"schema_version must be {expected!r}")


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PendingRecordValidationError(f"{field} is required")
    return value.strip()


def _optional_string(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise PendingRecordValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _require_string_list(payload: dict[str, Any], field: str) -> list[str]:
    values = _optional_string_list(payload, field)
    if not values:
        raise PendingRecordValidationError(f"{field} is required")
    return values


def _optional_string_list(payload: dict[str, Any], field: str) -> list[str]:
    values = payload.get(field, [])
    if not isinstance(values, list):
        raise PendingRecordValidationError(f"{field} must be a list")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise PendingRecordValidationError(f"{field} must contain non-empty strings")
        normalized.append(value.strip())
    return normalized


def _require_provider_id(payload: dict[str, Any]) -> str:
    provider_id = _require_string(payload, "provider_id")
    if provider_id not in LLM_PROVIDER_IDS:
        raise PendingRecordValidationError(f"unknown provider_id {provider_id!r}")
    return provider_id


def _require_hash(payload: dict[str, Any], field: str) -> str:
    value = _require_string(payload, field)
    if not _is_sha256(value):
        raise PendingRecordValidationError(f"{field} must be a sha256 hash")
    return value


def _is_sha256(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    return all(char in "0123456789abcdef" for char in value.removeprefix("sha256:"))

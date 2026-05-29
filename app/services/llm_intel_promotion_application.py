"""DataForge promotion application for LLM provider intelligence.

ForgeCommand can approve a candidate for promotion, but only DataForge mutates
canonical promoted truth. This module validates ForgeCommand decision receipts,
records them durably, and applies approved decisions into promoted records with
supersession lineage.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.llm_intel_pending_records_models import (
    LLMIntelDriftReportRecord,
    LLMIntelPendingCandidateRecord,
    LLMIntelPromotedRecord,
    LLMIntelPromotionDecisionRecord,
    LLMIntelSourceFingerprintRecord,
    LLMIntelSupersessionChainRecord,
)
from app.models.llm_intel_pending_records_schemas import (
    LLMIntelPromotionApplicationResponse,
    LLMIntelPromotionDecisionApplyRequest,
)
from app.services.llm_intel_pending_records import stable_hash
from app.services.llm_intel_source_trust import OFFICIAL_REQUIRED_CLAIM_TYPES
from forge_contract_core.validators.families import (
    FamilyValidationError,
    validate_family_payload,
)


CANDIDATE_RECORD_TYPES = {
    "model": "model_registry",
    "pricing": "pricing",
    "capability": "capability",
}

NON_PROMOTION_STATES_BY_DECISION = {
    "reject": "rejected",
    "defer": "deferred",
    "request_more_evidence": "more_evidence_required",
    "rollback_request": "rollback_requested",
}

TERMINAL_CANDIDATE_STATES = frozenset(
    {
        "promoted",
        "superseded",
        "rollback_completed",
        "archived",
    }
)


class PromotionApplicationValidationError(ValueError):
    """Raised when a decision receipt cannot be applied by DataForge."""


class PromotionApplicationConflictError(ValueError):
    """Raised when promotion application would silently overwrite truth."""


def apply_promotion_decision(
    db: Session,
    request: LLMIntelPromotionDecisionApplyRequest,
) -> LLMIntelPromotionApplicationResponse:
    try:
        return _apply_promotion_decision(db, request)
    except Exception:
        db.rollback()
        raise


def list_promoted_records(
    db: Session,
    *,
    provider_id: str | None = None,
    record_type: str | None = None,
    current_only: bool = True,
) -> list[LLMIntelPromotedRecord]:
    query = db.query(LLMIntelPromotedRecord)
    if provider_id is not None:
        query = query.filter(LLMIntelPromotedRecord.provider_id == provider_id)
    if record_type is not None:
        query = query.filter(LLMIntelPromotedRecord.record_type == record_type)
    if current_only:
        query = query.filter(LLMIntelPromotedRecord.is_current.is_(True))
    return (
        query.order_by(
            LLMIntelPromotedRecord.provider_id.asc(),
            LLMIntelPromotedRecord.record_type.asc(),
            LLMIntelPromotedRecord.claim_path.asc(),
            LLMIntelPromotedRecord.promoted_at.desc(),
        )
        .all()
    )


def get_promoted_record(
    db: Session,
    promoted_record_id: str,
) -> LLMIntelPromotedRecord | None:
    return (
        db.query(LLMIntelPromotedRecord)
        .filter(LLMIntelPromotedRecord.promoted_record_id == promoted_record_id)
        .first()
    )


def _apply_promotion_decision(
    db: Session,
    request: LLMIntelPromotionDecisionApplyRequest,
) -> LLMIntelPromotionApplicationResponse:
    payload = request.payload
    _validate_contract_payload("llm_intel_promotion_decision", payload)
    payload_hash = stable_hash(payload)
    decision_row, decision_status = _record_decision(db, payload, payload_hash)

    existing_promoted = _promoted_for_decision(db, decision_row.decision_id)
    if existing_promoted is not None:
        chain_event = _chain_event_for_promoted_record(db, existing_promoted.promoted_record_id)
        db.commit()
        return _promotion_response(
            decision_row=decision_row,
            application_status="duplicate",
            promotion_state="promoted",
            promoted_row=existing_promoted,
            chain_event=chain_event,
        )

    candidate = _require_candidate(db, decision_row.candidate_id)

    if decision_row.decision != "approve":
        expected_state = NON_PROMOTION_STATES_BY_DECISION.get(decision_row.decision)
        if decision_row.resulting_state != expected_state:
            raise PromotionApplicationValidationError(
                f"{decision_row.decision!r} decisions must result in {expected_state!r}"
            )
        _mark_candidate_and_drift_reports(db, candidate, decision_row.resulting_state)
        decision_row.applied_at = _utc_now()
        db.commit()
        return _promotion_response(
            decision_row=decision_row,
            application_status=(
                "duplicate" if decision_status == "duplicate" else "recorded_no_promotion"
            ),
            promotion_state=decision_row.resulting_state,
            promoted_row=None,
            chain_event=None,
        )

    if candidate.promotion_state in TERMINAL_CANDIDATE_STATES:
        raise PromotionApplicationConflictError(
            f"candidate {candidate.candidate_id!r} is already in terminal state "
            f"{candidate.promotion_state!r}"
        )

    promoted_row, chain_event = _promote_candidate(db, decision_row, candidate)
    decision_row.promoted_record_id = promoted_row.promoted_record_id
    decision_row.applied_at = promoted_row.promoted_at
    _mark_candidate_and_drift_reports(db, candidate, "promoted")
    db.commit()

    return _promotion_response(
        decision_row=decision_row,
        application_status=decision_status,
        promotion_state="promoted",
        promoted_row=promoted_row,
        chain_event=chain_event,
    )


def _record_decision(
    db: Session,
    payload: dict[str, Any],
    payload_hash: str,
) -> tuple[LLMIntelPromotionDecisionRecord, str]:
    decision_id = _require_string(payload, "decision_id")
    existing = (
        db.query(LLMIntelPromotionDecisionRecord)
        .filter(LLMIntelPromotionDecisionRecord.decision_id == decision_id)
        .first()
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise PromotionApplicationConflictError(
                f"promotion decision {decision_id!r} already exists with different payload"
            )
        return existing, "duplicate"

    row = LLMIntelPromotionDecisionRecord(
        decision_id=decision_id,
        review_packet_id=_require_string(payload, "review_packet_id"),
        candidate_id=_require_string(payload, "candidate_id"),
        operator_id=_require_string(payload, "operator_id"),
        authority_ring=_require_string(payload, "authority_ring"),
        decision=_require_string(payload, "decision"),
        resulting_state=_require_string(payload, "resulting_state"),
        evidence_bundle_hash=_require_string(payload, "evidence_bundle_hash"),
        affected_record_refs=_string_list(payload.get("affected_record_refs", [])),
        constraints=_string_list(payload.get("constraints", [])),
        payload_hash=payload_hash,
        payload=payload,
        decided_at=_require_string(payload, "decided_at"),
    )
    db.add(row)
    db.flush()
    return row, "stored"


def _promote_candidate(
    db: Session,
    decision_row: LLMIntelPromotionDecisionRecord,
    candidate: LLMIntelPendingCandidateRecord,
) -> tuple[LLMIntelPromotedRecord, LLMIntelSupersessionChainRecord]:
    record_type = CANDIDATE_RECORD_TYPES.get(candidate.candidate_type)
    if record_type is None:
        raise PromotionApplicationValidationError(
            f"unsupported candidate_type {candidate.candidate_type!r}"
        )

    candidate_value = candidate.payload.get("candidate_value")
    if not isinstance(candidate_value, dict):
        raise PromotionApplicationValidationError("candidate_value is required for promotion")

    fingerprint_rows = _require_source_fingerprints(db, candidate.source_fingerprint_ids)
    if candidate.claim_type in OFFICIAL_REQUIRED_CLAIM_TYPES and not any(
        row.trust_class == "OFFICIAL" for row in fingerprint_rows
    ):
        raise PromotionApplicationValidationError(
            f"{candidate.claim_type} promotions require OFFICIAL source evidence"
        )
    if any(row.trust_class == "BLOCKED" for row in fingerprint_rows):
        raise PromotionApplicationValidationError(
            "BLOCKED source evidence cannot support promotion"
        )

    now = _utc_now()
    promoted_record_id = _digest_id("promoted", decision_row.decision_id)
    current_row = _current_promoted_record(db, candidate.provider_id, record_type, candidate.claim_path)
    promotion_action = "supersede" if current_row is not None else "promote"
    supersedes_record_id = current_row.promoted_record_id if current_row is not None else None
    lineage_root_id = (
        current_row.lineage_root_id
        if current_row is not None
        else _digest_id("lineage", candidate.provider_id, record_type, candidate.claim_path)
    )

    metadata = {
        "promoted_by_system": "DataForge",
        "promotion_action": promotion_action,
        "promoted_at": _iso_z(now),
        "promotion_receipt_id": _digest_id("promotion-receipt", decision_row.decision_id),
        "lineage_root_id": lineage_root_id,
        "supersedes_record_id": supersedes_record_id,
    }
    promoted_payload = {
        "schema_version": "llm_intel.promoted_record.v1",
        "promoted_record_id": promoted_record_id,
        "provider_id": candidate.provider_id,
        "record_type": record_type,
        "promoted_value": candidate_value,
        "source_decision_ref": (
            f"llm_intel_promotion_decision:{decision_row.decision_id}:v1"
        ),
        "candidate_id": candidate.candidate_id,
        "evidence_bundle_hash": decision_row.evidence_bundle_hash,
        "source_evidence": _source_evidence(fingerprint_rows),
        "dataforge_promotion_metadata": metadata,
    }
    _validate_contract_payload("llm_intel_promoted_record", promoted_payload)
    promoted_payload_hash = stable_hash(promoted_payload)

    existing = get_promoted_record(db, promoted_record_id)
    if existing is not None:
        if existing.payload_hash != promoted_payload_hash:
            raise PromotionApplicationConflictError(
                f"promoted record {promoted_record_id!r} already exists with different payload"
            )
        chain_event = _chain_event_for_promoted_record(db, promoted_record_id)
        if chain_event is None:
            raise PromotionApplicationConflictError(
                f"promoted record {promoted_record_id!r} is missing supersession chain event"
            )
        return existing, chain_event

    if current_row is not None:
        current_row.is_current = False
        current_row.superseded_by_record_id = promoted_record_id
        current_row.superseded_at = now

    promoted_row = LLMIntelPromotedRecord(
        promoted_record_id=promoted_record_id,
        provider_id=candidate.provider_id,
        record_type=record_type,
        candidate_id=candidate.candidate_id,
        decision_id=decision_row.decision_id,
        source_decision_ref=promoted_payload["source_decision_ref"],
        evidence_bundle_hash=decision_row.evidence_bundle_hash,
        claim_path=candidate.claim_path,
        promotion_action=promotion_action,
        lineage_root_id=lineage_root_id,
        supersedes_record_id=supersedes_record_id,
        is_current=True,
        source_fingerprint_ids=list(candidate.source_fingerprint_ids),
        receipt_ids=list(candidate.receipt_ids),
        claim_ids=list(candidate.claim_ids),
        payload_hash=promoted_payload_hash,
        payload=promoted_payload,
        promoted_at=now,
    )
    db.add(promoted_row)

    chain_payload = {
        "schema_version": "llm_intel.supersession_chain.v1",
        "lineage_root_id": lineage_root_id,
        "provider_id": candidate.provider_id,
        "record_type": record_type,
        "claim_path": candidate.claim_path,
        "from_record_id": supersedes_record_id,
        "to_record_id": promoted_record_id,
        "decision_id": decision_row.decision_id,
        "action": promotion_action,
        "created_at": _iso_z(now),
    }
    chain_event = LLMIntelSupersessionChainRecord(
        chain_event_id=_digest_id("chain-event", promoted_record_id),
        provider_id=candidate.provider_id,
        record_type=record_type,
        claim_path=candidate.claim_path,
        lineage_root_id=lineage_root_id,
        from_record_id=supersedes_record_id,
        to_record_id=promoted_record_id,
        decision_id=decision_row.decision_id,
        action=promotion_action,
        payload_hash=stable_hash(chain_payload),
        payload=chain_payload,
    )
    db.add(chain_event)
    db.flush()
    return promoted_row, chain_event


def _current_promoted_record(
    db: Session,
    provider_id: str,
    record_type: str,
    claim_path: str,
) -> LLMIntelPromotedRecord | None:
    return (
        db.query(LLMIntelPromotedRecord)
        .filter(LLMIntelPromotedRecord.provider_id == provider_id)
        .filter(LLMIntelPromotedRecord.record_type == record_type)
        .filter(LLMIntelPromotedRecord.claim_path == claim_path)
        .filter(LLMIntelPromotedRecord.is_current.is_(True))
        .order_by(LLMIntelPromotedRecord.promoted_at.desc())
        .first()
    )


def _promoted_for_decision(
    db: Session,
    decision_id: str,
) -> LLMIntelPromotedRecord | None:
    return (
        db.query(LLMIntelPromotedRecord)
        .filter(LLMIntelPromotedRecord.decision_id == decision_id)
        .first()
    )


def _chain_event_for_promoted_record(
    db: Session,
    promoted_record_id: str,
) -> LLMIntelSupersessionChainRecord | None:
    return (
        db.query(LLMIntelSupersessionChainRecord)
        .filter(LLMIntelSupersessionChainRecord.to_record_id == promoted_record_id)
        .first()
    )


def _mark_candidate_and_drift_reports(
    db: Session,
    candidate: LLMIntelPendingCandidateRecord,
    promotion_state: str,
) -> None:
    candidate.promotion_state = promotion_state
    candidate_payload = dict(candidate.payload)
    candidate_payload["promotion_state"] = promotion_state
    candidate.payload = candidate_payload

    drift_reports = (
        db.query(LLMIntelDriftReportRecord)
        .filter(LLMIntelDriftReportRecord.candidate_id == candidate.candidate_id)
        .all()
    )
    for drift_report in drift_reports:
        drift_report.promotion_state = promotion_state
        drift_payload = dict(drift_report.payload)
        drift_payload["promotion_state"] = promotion_state
        drift_report.payload = drift_payload


def _require_candidate(db: Session, candidate_id: str) -> LLMIntelPendingCandidateRecord:
    row = (
        db.query(LLMIntelPendingCandidateRecord)
        .filter(LLMIntelPendingCandidateRecord.candidate_id == candidate_id)
        .first()
    )
    if row is None:
        raise PromotionApplicationValidationError(
            f"missing pending candidate {candidate_id!r}"
        )
    return row


def _require_source_fingerprints(
    db: Session,
    fingerprint_ids: list[str],
) -> list[LLMIntelSourceFingerprintRecord]:
    if not fingerprint_ids:
        raise PromotionApplicationValidationError("promotion requires source fingerprints")
    rows = (
        db.query(LLMIntelSourceFingerprintRecord)
        .filter(LLMIntelSourceFingerprintRecord.fingerprint_id.in_(fingerprint_ids))
        .all()
    )
    found = {row.fingerprint_id for row in rows}
    missing = sorted(set(fingerprint_ids) - found)
    if missing:
        raise PromotionApplicationValidationError(
            f"missing source fingerprint(s): {missing}"
        )
    return sorted(rows, key=lambda row: row.fingerprint_id)


def _source_evidence(rows: list[LLMIntelSourceFingerprintRecord]) -> list[dict[str, str]]:
    return [
        {
            "source_id": row.source_id,
            "trust_class": row.trust_class,
            "content_hash": row.content_hash,
        }
        for row in rows
    ]


def _promotion_response(
    *,
    decision_row: LLMIntelPromotionDecisionRecord,
    application_status: str,
    promotion_state: str,
    promoted_row: LLMIntelPromotedRecord | None,
    chain_event: LLMIntelSupersessionChainRecord | None,
) -> LLMIntelPromotionApplicationResponse:
    return LLMIntelPromotionApplicationResponse(
        decision_id=decision_row.decision_id,
        candidate_id=decision_row.candidate_id,
        decision=decision_row.decision,
        decision_resulting_state=decision_row.resulting_state,
        promotion_state=promotion_state,
        promotion_applied=promoted_row is not None,
        application_status=application_status,
        payload_hash=decision_row.payload_hash,
        promoted_record_id=promoted_row.promoted_record_id if promoted_row else None,
        promotion_action=promoted_row.promotion_action if promoted_row else None,
        supersedes_record_id=promoted_row.supersedes_record_id if promoted_row else None,
        lineage_root_id=promoted_row.lineage_root_id if promoted_row else None,
        supersession_chain_event_id=chain_event.chain_event_id if chain_event else None,
        promoted_payload=promoted_row.payload if promoted_row else None,
    )


def _validate_contract_payload(family: str, payload: dict[str, Any]) -> None:
    try:
        validate_family_payload(family, 1, payload)
    except FamilyValidationError as exc:
        raise PromotionApplicationValidationError(
            f"{family} failed canonical validation: {exc.errors}"
        ) from exc


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PromotionApplicationValidationError(f"{field} is required")
    return value.strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise PromotionApplicationValidationError("expected a list of strings")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PromotionApplicationValidationError("expected a list of non-empty strings")
        normalized.append(item.strip())
    return normalized


def _digest_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"{prefix}-{digest}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso_z(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")

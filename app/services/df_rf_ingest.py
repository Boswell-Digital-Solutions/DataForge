"""BDS-DF-RF-001 Receipt-to-Finding Knowledge Spine -- ingest service.

Generalizes the reusable mechanisms of app/services/llm_intel_pending_records.py
per OD-03 ("generalize, don't duplicate"): stable_hash() is imported verbatim
(no LLM-intel-specific logic in it at all); the idempotent duplicate-vs-conflict
shape and referential-integrity-lookup pattern are re-implemented here against
the new df_rf_* tables, not the llm_intel_* ones. The promotion/registry-
projection logic in llm_intel_promotion_application.py does NOT generalize --
OD-02 makes df_rf_finding_candidate terminal, with df_rf_disposition.v1 as its
only lifecycle exit and no promoted-record materialization at all.

candidate_id and disposition_id/evidence_link_id identity: candidate_id is a
deterministic uuid5(DF_RF_NAMESPACE, record_family + "|" + natural_key) per the
WP-01 Board Review's Finding 1 correction (RFC-DF-RF-01) -- computed here, by
DataForge, not trusted from the caller, so a caller cannot forge dedup identity.
evidence_link_id and disposition_id are still externally supplied (mirroring
llm-intel's receipt_id/candidate_id pattern) since neither has an equivalent
redelivery-dedup requirement stated in the RFC.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.df_rf_models import (
    DfRfDispositionRecord,
    DfRfEvidenceLinkRecord,
    DfRfFindingCandidateRecord,
)
from app.models.df_rf_schemas import (
    DfRfCandidateReviewItem,
    DfRfDispositionRead,
    DfRfIngestRequest,
    DfRfIngestResponse,
)
from app.models.memory_models import MemoryConflict
from app.models.telemetry_models import ForgeCheckRunReceiptV1Record
from app.services.llm_intel_pending_records import stable_hash
from forge_contract_core.validators.families import (
    FamilyValidationError,
    validate_family_payload,
)


# RFC-DF-RF-01: DF_RF_NAMESPACE is minted once, here, at implementation time
# (the RFC deliberately left this to implementation, not schema-drafting).
DF_RF_NAMESPACE = uuid.UUID("6f2d7e3a-df01-4a1c-9c3e-df01df01df01")

# Implementation-time survey (RFC-DF-RF-01 Sequencing / BDS-FMEM-OPCOURT-001
# WP-01 §2): which upstream_family values DataForge can actually verify
# against its own storage, and which column identifies a record within it.
# ForgeCheckRunReceipt.v1 (forge_check_run_receipts_v1.receipt_id, a Postgres
# UUID column) and MemoryConflict.v1 (memory_conflicts.conflict_id, a plain
# String(64) column -- see _compute_verification_status's string-comparison
# note below) are both DataForge-owned, queryable storage today.
# TelemetryEmitReceipt.v1 has no durable DataForge-side table (WP-00 Sec 2.4 --
# the production write path isn't confirmed live end-to-end), and
# ServiceHealthEnvelope.v1 is polled live, never persisted historically.
# Extending this map to more families is additive, non-RFC implementation work.
_VERIFIABLE_UPSTREAM_FAMILIES: dict[str, tuple[type, str]] = {
    "ForgeCheckRunReceipt.v1": (ForgeCheckRunReceiptV1Record, "receipt_id"),
    "MemoryConflict.v1": (MemoryConflict, "conflict_id"),
}


class DfRfValidationError(ValueError):
    """Raised when a df_rf record cannot be stored."""


class DfRfConflictError(ValueError):
    """Raised when a record id would overwrite a different payload."""


def store_df_rf_record(db: Session, request: DfRfIngestRequest) -> DfRfIngestResponse:
    payload = dict(request.payload)
    if request.family == "df_rf_evidence_link":
        return _store_evidence_link(db, payload)
    if request.family == "df_rf_finding_candidate":
        return _store_finding_candidate(db, payload)
    if request.family == "df_rf_disposition":
        return _store_disposition(db, payload)
    raise DfRfValidationError(f"unsupported family {request.family!r}")


def _validate_payload(family: str, payload: dict[str, Any]) -> None:
    try:
        validate_family_payload(family, 1, payload)
    except FamilyValidationError as exc:
        raise DfRfValidationError(f"{family} failed canonical validation: {exc.errors}") from exc


def _compute_verification_status(
    db: Session, upstream_family: str, upstream_record_id: str
) -> str:
    lookup = _VERIFIABLE_UPSTREAM_FAMILIES.get(upstream_family)
    if lookup is None:
        return "verification_unavailable"
    model, id_column = lookup
    try:
        parsed = uuid.UUID(upstream_record_id)
    except ValueError:
        return "unverified"
    # The bound value's Python type must match what the column's own type
    # expects, not the other way around: ForgeCheckRunReceipt.v1.receipt_id is
    # a Postgres UUID(as_uuid=True) column, whose bind processor calls
    # `.hex` on the value and raises AttributeError if given a plain string
    # (confirmed by a real test failure during this work, not assumed);
    # MemoryConflict.v1.conflict_id is a plain String(64) column, which
    # rejects a uuid.UUID object the same way in reverse under SQLite (the
    # test backend). Inspect the column's own type and bind the form it
    # actually expects, rather than picking one form for every family.
    column = getattr(model, id_column)
    query_value: uuid.UUID | str = (
        upstream_record_id if isinstance(column.type, sa.String) else parsed
    )
    exists = (
        db.query(model).filter(column == query_value).first()
        is not None
    )
    return "verified" if exists else "unverified"


def _store_evidence_link(db: Session, payload: dict[str, Any]) -> DfRfIngestResponse:
    # verification_status is computed by DataForge, never trusted from the
    # caller (RFC-DF-RF-01 Finding 2) -- overwrite whatever the caller sent,
    # then re-validate so a caller cannot claim "verified" for a family/id
    # this instance cannot actually check.
    upstream_family = payload.get("upstream_family")
    upstream_record_id = payload.get("upstream_record_id")
    if not isinstance(upstream_family, str) or not isinstance(upstream_record_id, str):
        raise DfRfValidationError("upstream_family and upstream_record_id are required")
    payload["verification_status"] = _compute_verification_status(
        db, upstream_family, upstream_record_id
    )

    _validate_payload("df_rf_evidence_link", payload)
    evidence_link_id = _require_string(payload, "evidence_link_id")
    payload_hash = stable_hash(payload)

    existing = (
        db.query(DfRfEvidenceLinkRecord)
        .filter(DfRfEvidenceLinkRecord.evidence_link_id == evidence_link_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing.payload_hash, payload_hash, "df_rf_evidence_link", evidence_link_id
        )

    row = DfRfEvidenceLinkRecord(
        evidence_link_id=evidence_link_id,
        source_plan_id=_require_string(payload, "source_plan_id"),
        upstream_family=upstream_family,
        upstream_record_id=upstream_record_id,
        observed_at=_require_datetime(payload, "observed_at"),
        collected_by=_require_string(payload, "collected_by"),
        verification_status=payload["verification_status"],
        privacy_class=_require_string(payload, "privacy_class"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return DfRfIngestResponse(
        family="df_rf_evidence_link",
        record_id=evidence_link_id,
        payload_hash=payload_hash,
        storage_status="stored",
    )


def _store_finding_candidate(db: Session, payload: dict[str, Any]) -> DfRfIngestResponse:
    record_family = _require_string(payload, "record_family")
    natural_key = _require_string(payload, "natural_key")
    # candidate_id is deterministic (RFC-DF-RF-01 Finding 1) -- computed here,
    # overwriting whatever the caller sent, so redelivering the same finding
    # always resolves to the same row regardless of what the caller passed.
    candidate_id = str(uuid.uuid5(DF_RF_NAMESPACE, f"{record_family}|{natural_key}"))
    payload["candidate_id"] = candidate_id

    evidence_link_ids = payload.get("evidence_link_ids")
    if not isinstance(evidence_link_ids, list) or not evidence_link_ids:
        raise DfRfValidationError("evidence_link_ids is required and must be non-empty")
    _require_evidence_links(db, evidence_link_ids)

    _validate_payload("df_rf_finding_candidate", payload)
    payload_hash = stable_hash(payload)

    existing = (
        db.query(DfRfFindingCandidateRecord)
        .filter(DfRfFindingCandidateRecord.candidate_id == candidate_id)
        .first()
    )
    if existing is not None:
        if existing.payload_hash == payload_hash:
            return DfRfIngestResponse(
                family="df_rf_finding_candidate",
                record_id=candidate_id,
                payload_hash=payload_hash,
                storage_status="duplicate",
            )
        # Same conceptual finding (same natural_key), updated content -- an
        # open candidate (candidate_detected/under_review) is expected to
        # accrue more evidence over its lifecycle (WP-01 Corrective Addendum),
        # so this is an update, not a conflict, unlike evidence_link/
        # disposition which are immutable once stored.
        existing.category = _require_string(payload, "category")
        existing.evidence_link_ids = evidence_link_ids
        existing.disposition_state = _require_string(payload, "disposition_state")
        existing.summary = _require_string(payload, "summary")
        existing.classification = _require_string(payload, "classification")
        existing.payload_hash = payload_hash
        existing.payload = payload
        db.commit()
        return DfRfIngestResponse(
            family="df_rf_finding_candidate",
            record_id=candidate_id,
            payload_hash=payload_hash,
            storage_status="stored",
        )

    row = DfRfFindingCandidateRecord(
        candidate_id=candidate_id,
        record_family=record_family,
        natural_key=natural_key,
        run_id=_require_string(payload, "run_id"),
        category=_require_string(payload, "category"),
        evidence_link_ids=evidence_link_ids,
        disposition_state=_require_string(payload, "disposition_state"),
        summary=_require_string(payload, "summary"),
        classification=_require_string(payload, "classification"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)
    db.commit()
    return DfRfIngestResponse(
        family="df_rf_finding_candidate",
        record_id=candidate_id,
        payload_hash=payload_hash,
        storage_status="stored",
    )


def _store_disposition(db: Session, payload: dict[str, Any]) -> DfRfIngestResponse:
    candidate_id = _require_string(payload, "candidate_id")
    _require_candidate(db, candidate_id)

    _validate_payload("df_rf_disposition", payload)
    disposition_id = _require_string(payload, "disposition_id")
    payload_hash = stable_hash(payload)

    existing = (
        db.query(DfRfDispositionRecord)
        .filter(DfRfDispositionRecord.disposition_id == disposition_id)
        .first()
    )
    if existing is not None:
        return _duplicate_or_conflict(
            existing.payload_hash, payload_hash, "df_rf_disposition", disposition_id
        )

    row = DfRfDispositionRecord(
        disposition_id=disposition_id,
        candidate_id=candidate_id,
        operator_id=_require_string(payload, "operator_id"),
        decision=_require_string(payload, "decision"),
        rationale=_require_string(payload, "rationale"),
        evidence_bundle_hash=_require_string(payload, "evidence_bundle_hash"),
        decided_at=_require_datetime(payload, "decided_at"),
        payload_hash=payload_hash,
        payload=payload,
    )
    db.add(row)

    candidate = (
        db.query(DfRfFindingCandidateRecord)
        .filter(DfRfFindingCandidateRecord.candidate_id == candidate_id)
        .first()
    )
    candidate.disposition_state = row.decision
    db.commit()
    return DfRfIngestResponse(
        family="df_rf_disposition",
        record_id=disposition_id,
        payload_hash=payload_hash,
        storage_status="stored",
    )


def list_candidate_review_feed(
    db: Session,
    *,
    run_id: str | None = None,
    record_family: str | None = None,
    states: set[str] | None = None,
    limit: int = 200,
) -> list[DfRfCandidateReviewItem]:
    """Read-only Forge_Command operator review feed: candidates enriched with
    their evidence links' verification status and (if closed) disposition."""
    open_states = states or {"candidate_detected", "under_review"}
    query = db.query(DfRfFindingCandidateRecord).filter(
        DfRfFindingCandidateRecord.disposition_state.in_(open_states)
    )
    if run_id:
        query = query.filter(DfRfFindingCandidateRecord.run_id == run_id)
    if record_family:
        query = query.filter(DfRfFindingCandidateRecord.record_family == record_family)
    candidates = (
        query.order_by(
            DfRfFindingCandidateRecord.created_at.desc(),
            DfRfFindingCandidateRecord.candidate_id.asc(),
        )
        .limit(limit)
        .all()
    )
    if not candidates:
        return []

    evidence_link_ids: set[str] = set()
    for row in candidates:
        evidence_link_ids.update(row.evidence_link_ids or [])
    status_by_id: dict[str, str] = {}
    if evidence_link_ids:
        for link in (
            db.query(DfRfEvidenceLinkRecord)
            .filter(DfRfEvidenceLinkRecord.evidence_link_id.in_(evidence_link_ids))
            .all()
        ):
            status_by_id[link.evidence_link_id] = link.verification_status

    candidate_ids = [row.candidate_id for row in candidates]
    disposition_by_candidate: dict[str, DfRfDispositionRecord] = {}
    for disp in (
        db.query(DfRfDispositionRecord)
        .filter(DfRfDispositionRecord.candidate_id.in_(candidate_ids))
        .all()
    ):
        disposition_by_candidate.setdefault(disp.candidate_id, disp)

    items: list[DfRfCandidateReviewItem] = []
    for row in candidates:
        disp = disposition_by_candidate.get(row.candidate_id)
        items.append(
            DfRfCandidateReviewItem(
                candidate_id=row.candidate_id,
                record_family=row.record_family,
                run_id=row.run_id,
                category=row.category,
                disposition_state=row.disposition_state,
                summary=row.summary,
                evidence_link_ids=list(row.evidence_link_ids or []),
                evidence_verification_statuses={
                    eid: status_by_id[eid]
                    for eid in (row.evidence_link_ids or [])
                    if eid in status_by_id
                },
                disposition=(
                    DfRfDispositionRead(
                        disposition_id=disp.disposition_id,
                        candidate_id=disp.candidate_id,
                        operator_id=disp.operator_id,
                        decision=disp.decision,
                        rationale=disp.rationale,
                        decided_at=disp.decided_at.isoformat() if disp.decided_at else None,
                    )
                    if disp
                    else None
                ),
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        )
    return items


def _require_evidence_links(db: Session, evidence_link_ids: list[str]) -> None:
    rows = (
        db.query(DfRfEvidenceLinkRecord)
        .filter(DfRfEvidenceLinkRecord.evidence_link_id.in_(evidence_link_ids))
        .all()
    )
    found = {row.evidence_link_id for row in rows}
    missing = sorted(set(evidence_link_ids) - found)
    if missing:
        raise DfRfValidationError(f"missing evidence link(s): {missing}")


def _require_candidate(db: Session, candidate_id: str) -> None:
    exists = (
        db.query(DfRfFindingCandidateRecord)
        .filter(DfRfFindingCandidateRecord.candidate_id == candidate_id)
        .first()
        is not None
    )
    if not exists:
        raise DfRfValidationError(f"missing finding candidate: {candidate_id!r}")


def _duplicate_or_conflict(
    existing_hash: str, payload_hash: str, family: str, record_id: str
) -> DfRfIngestResponse:
    if existing_hash != payload_hash:
        raise DfRfConflictError(
            f"{family} record {record_id!r} already exists with a different payload"
        )
    return DfRfIngestResponse(
        family=family,
        record_id=record_id,
        payload_hash=payload_hash,
        storage_status="duplicate",
    )


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DfRfValidationError(f"{field} is required")
    return value.strip()


def _require_datetime(payload: dict[str, Any], field: str) -> datetime:
    value = _require_string(payload, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DfRfValidationError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

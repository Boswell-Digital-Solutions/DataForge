"""CP5 shadow-only adaptive telemetry retention and derivation receipts.

This module writes only derived CP5 records. It never deletes, updates, or
rewrites ForgeEvent.v1 or ForgeCheck evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import rfc8785
from forge_telemetry import (
    TelemetryDerivationReceiptV1,
    derivation_receipt_digest,
    validate_telemetry_derivation_receipt_v1,
)
from sqlalchemy.orm import Session

from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeCheckRunReceiptV1Record,
    ForgeEventV1Record,
    TelemetryDerivationReceiptV1Record,
    TelemetryRetentionDecisionV1Record,
    TelemetryRoutineAggregateV1Record,
)
from app.models.telemetry_schemas import TelemetryRoutineAggregatePayloadV1

RETENTION_POLICY_PATH = (
    Path(__file__).parent
    / "models"
    / "contracts"
    / "telemetry_retention_policy.v1.json"
)
RETENTION_POLICY_SHA256 = (
    "45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52"
)
RETENTION_POLICY_ID = "bds.telemetry.retention"
RETENTION_POLICY_VERSION = "1.0.0-shadow"
RETENTION_POLICY_MODE = "shadow"
RETENTION_CLOCK_BASIS = "received_at"
MAX_SHADOW_SOURCE_ITEMS = 500


def _load_policy() -> dict[str, Any]:
    raw = RETENTION_POLICY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RETENTION_POLICY_SHA256:
        raise RuntimeError("telemetry retention policy digest mismatch")
    policy = json.loads(raw)
    required = {
        "schema_version": "forge.dataforge.telemetry-retention-policy.v1",
        "policy_id": RETENTION_POLICY_ID,
        "version": RETENTION_POLICY_VERSION,
        "mode": RETENTION_POLICY_MODE,
        "clock_basis": RETENTION_CLOCK_BASIS,
        "deletion_enabled": False,
        "source_overwrite_enabled": False,
    }
    if any(policy.get(key) != value for key, value in required.items()):
        raise RuntimeError("telemetry retention policy boundary mismatch")
    if policy.get("source_limit") != MAX_SHADOW_SOURCE_ITEMS:
        raise RuntimeError("telemetry retention policy source limit mismatch")
    return policy


RETENTION_POLICY = _load_policy()


@dataclass(frozen=True)
class ShadowSource:
    evidence_kind: str
    evidence_ref: str
    sha256: str
    received_at: datetime
    service_or_check: str
    environment: str
    tenant_ref: str | None
    privacy_class: str
    retention_class: str
    legal_class: str
    routine_success: bool
    sampled_normal_trace: bool
    slow: bool
    governed: bool


@dataclass(frozen=True)
class ShadowDecision:
    source: ShadowSource
    action: str
    reason_code: str
    projected_delete_at: datetime | None


@dataclass(frozen=True)
class ShadowRetentionRunResult:
    source_count: int
    decision_count: int
    aggregate_count: int
    partial: bool
    policy_sha256: str = RETENTION_POLICY_SHA256
    policy_mode: str = RETENTION_POLICY_MODE
    clock_basis: str = RETENTION_CLOCK_BASIS
    deletion_count: int = 0
    source_update_count: int = 0


def run_shadow_retention(
    db: Session,
    *,
    window_start_at: datetime,
    window_end_at: datetime,
    environment: str,
    tenant_ref: str | None,
    source_limit: int = MAX_SHADOW_SOURCE_ITEMS,
) -> ShadowRetentionRunResult:
    """Persist inert decisions and aggregates for one received-at window."""

    start = _utc(window_start_at)
    end = _utc(window_end_at)
    if start > end:
        raise ValueError("retention window start exceeds end")
    if not 1 <= source_limit <= MAX_SHADOW_SOURCE_ITEMS:
        raise ValueError("retention source limit is outside bounds")

    sources = _load_sources(
        db,
        start=start,
        end=end,
        environment=environment,
        tenant_ref=tenant_ref,
        source_limit=source_limit,
    )
    if len(sources) > source_limit:
        raise ValueError("retention_window_source_limit_exceeded")
    selected = sources
    decisions = [_classify(source) for source in selected]

    try:
        for decision in decisions:
            _persist_decision(
                db,
                decision=decision,
                window_start_at=start,
                window_end_at=end,
            )
        aggregate_count = _persist_routine_aggregates(
            db,
            decisions=decisions,
            window_start_at=start,
            window_end_at=end,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ShadowRetentionRunResult(
        source_count=len(selected),
        decision_count=len(decisions),
        aggregate_count=aggregate_count,
        partial=False,
    )


def _load_sources(
    db: Session,
    *,
    start: datetime,
    end: datetime,
    environment: str,
    tenant_ref: str | None,
    source_limit: int,
) -> list[ShadowSource]:
    # Bound every source-family query before materialization. The combined
    # source count is checked below and fails closed before any derived write.
    family_limit = source_limit + 1
    event_query = db.query(ForgeEventV1Record).filter(
        ForgeEventV1Record.received_at >= start,
        ForgeEventV1Record.received_at <= end,
        ForgeEventV1Record.environment == environment,
    )
    result_query = db.query(ForgeCheckResultV1Record).filter(
        ForgeCheckResultV1Record.received_at >= start,
        ForgeCheckResultV1Record.received_at <= end,
        ForgeCheckResultV1Record.environment == environment,
    )
    receipt_query = (
        db.query(ForgeCheckRunReceiptV1Record, ForgeCheckResultV1Record)
        .join(
            ForgeCheckResultV1Record,
            ForgeCheckRunReceiptV1Record.result_id
            == ForgeCheckResultV1Record.result_id,
        )
        .filter(
            ForgeCheckRunReceiptV1Record.received_at >= start,
            ForgeCheckRunReceiptV1Record.received_at <= end,
            ForgeCheckRunReceiptV1Record.environment == environment,
        )
    )
    if tenant_ref is None:
        event_query = event_query.filter(ForgeEventV1Record.tenant_ref.is_(None))
        result_query = result_query.filter(
            ForgeCheckResultV1Record.tenant_ref.is_(None)
        )
        receipt_query = receipt_query.filter(
            ForgeCheckRunReceiptV1Record.tenant_ref.is_(None)
        )
    else:
        event_query = event_query.filter(ForgeEventV1Record.tenant_ref == tenant_ref)
        result_query = result_query.filter(
            ForgeCheckResultV1Record.tenant_ref == tenant_ref
        )
        receipt_query = receipt_query.filter(
            ForgeCheckRunReceiptV1Record.tenant_ref == tenant_ref
        )

    event_query = event_query.order_by(
        ForgeEventV1Record.received_at,
        ForgeEventV1Record.event_id,
    ).limit(family_limit)
    result_query = result_query.order_by(
        ForgeCheckResultV1Record.received_at,
        ForgeCheckResultV1Record.result_id,
    ).limit(family_limit)
    receipt_query = receipt_query.order_by(
        ForgeCheckRunReceiptV1Record.received_at,
        ForgeCheckRunReceiptV1Record.receipt_id,
    ).limit(family_limit)

    sources: list[ShadowSource] = []
    for event in event_query.all():
        retention_class = event.retention_class
        sources.append(
            ShadowSource(
                evidence_kind="forge_event",
                evidence_ref=str(event.event_id),
                sha256=event.event_digest,
                received_at=_utc(event.received_at),
                service_or_check=event.service_name,
                environment=event.environment,
                tenant_ref=event.tenant_ref,
                privacy_class=event.privacy_class,
                retention_class=retention_class,
                legal_class=(
                    "legal_hold" if retention_class == "legal_hold" else "standard"
                ),
                routine_success=(
                    event.outcome == "ok"
                    and event.severity == "info"
                    and event.evidence_class in {"diagnostic", "operational"}
                ),
                sampled_normal_trace=event.sampled and event.trace_id is not None,
                slow=False,
                governed=(
                    event.evidence_class in {"audit", "security"}
                    or event.privacy_class in {"restricted", "confidential"}
                ),
            )
        )

    check_retention = RETENTION_POLICY["check_evidence_default_retention_class"]
    check_legal = RETENTION_POLICY["check_evidence_default_legal_class"]
    slow_threshold = RETENTION_POLICY["slow_check_threshold_ms"]
    for result in result_query.all():
        sources.append(
            ShadowSource(
                evidence_kind="forge_check_result",
                evidence_ref=str(result.result_id),
                sha256=result.payload_digest,
                received_at=_utc(result.received_at),
                service_or_check=result.check_id,
                environment=result.environment,
                tenant_ref=result.tenant_ref,
                privacy_class=result.privacy_class,
                retention_class=check_retention,
                legal_class=check_legal,
                routine_success=result.status == "passed",
                sampled_normal_trace=False,
                slow=result.duration_ms >= slow_threshold,
                governed=result.privacy_class in {"restricted", "confidential"},
            )
        )
    for receipt, result in receipt_query.all():
        sources.append(
            ShadowSource(
                evidence_kind="forge_check_run_receipt",
                evidence_ref=str(receipt.receipt_id),
                sha256=receipt.payload_digest,
                received_at=_utc(receipt.received_at),
                service_or_check=receipt.check_id,
                environment=receipt.environment,
                tenant_ref=receipt.tenant_ref,
                privacy_class=result.privacy_class,
                retention_class=check_retention,
                legal_class=check_legal,
                routine_success=receipt.status == "passed",
                sampled_normal_trace=False,
                slow=result.duration_ms >= slow_threshold,
                governed=result.privacy_class in {"restricted", "confidential"},
            )
        )

    return sorted(
        sources,
        key=lambda item: (
            item.received_at,
            item.evidence_kind,
            item.evidence_ref,
        ),
    )


def _classify(source: ShadowSource) -> ShadowDecision:
    if source.retention_class == "legal_hold" or source.legal_class == "legal_hold":
        return ShadowDecision(source, "legal_hold", "legal_hold", None)
    if source.governed:
        return ShadowDecision(
            source,
            RETENTION_POLICY["governed_action"],
            "governed_evidence_long",
            source.received_at
            + timedelta(days=RETENTION_POLICY["governed_retention_days"]),
        )
    if not source.routine_success:
        return ShadowDecision(
            source,
            RETENTION_POLICY["failure_action"],
            "failure_long",
            source.received_at
            + timedelta(days=RETENTION_POLICY["failure_retention_days"]),
        )
    if source.slow:
        return ShadowDecision(
            source,
            RETENTION_POLICY["failure_action"],
            "slow_check_long",
            source.received_at
            + timedelta(days=RETENTION_POLICY["failure_retention_days"]),
        )
    if source.sampled_normal_trace:
        return ShadowDecision(
            source,
            RETENTION_POLICY["sampled_normal_trace_action"],
            "sampled_normal_trace_short",
            source.received_at
            + timedelta(days=RETENTION_POLICY["sampled_normal_trace_retention_days"]),
        )
    days = RETENTION_POLICY["retention_days"][source.retention_class]
    return ShadowDecision(
        source,
        RETENTION_POLICY["routine_success_action"],
        f"routine_success_{source.retention_class}",
        source.received_at + timedelta(days=days),
    )


def _persist_decision(
    db: Session,
    *,
    decision: ShadowDecision,
    window_start_at: datetime,
    window_end_at: datetime,
) -> None:
    source = decision.source
    stable = (
        f"{source.evidence_kind}:{source.evidence_ref}:"
        f"{RETENTION_POLICY_SHA256}:{_wire_time(window_end_at)}"
    )
    decision_id = uuid5(NAMESPACE_URL, f"cp5-retention-decision:{stable}")
    derivation_id = uuid5(NAMESPACE_URL, f"cp5-retention-derivation:{stable}")
    receipt_id = uuid5(NAMESPACE_URL, f"cp5-retention-receipt:{stable}")
    output_payload = {
        "schema_version": "forge.dataforge.telemetry-retention-decision.v1",
        "decision_id": str(decision_id),
        "source_kind": source.evidence_kind,
        "source_ref": source.evidence_ref,
        "source_sha256": source.sha256,
        "source_received_at": _wire_time(source.received_at),
        "privacy_class": source.privacy_class,
        "retention_class": source.retention_class,
        "legal_class": source.legal_class,
        "action": decision.action,
        "reason_code": decision.reason_code,
        "projected_delete_at": (
            _wire_time(decision.projected_delete_at)
            if decision.projected_delete_at is not None
            else None
        ),
        "applied": False,
        "source_overwritten": False,
        "policy_sha256": RETENTION_POLICY_SHA256,
    }
    output_sha256 = hashlib.sha256(rfc8785.dumps(output_payload)).hexdigest()
    receipt = _receipt(
        receipt_id=receipt_id,
        derivation_id=derivation_id,
        derivation_type="retention_decision",
        sources=[source],
        window_start_at=window_start_at,
        window_end_at=window_end_at,
        output_ref=decision_id,
        output_sha256=output_sha256,
        action=decision.action,
        reason_code=decision.reason_code,
        projected_delete_at=decision.projected_delete_at,
    )
    _persist_receipt(db, receipt)

    existing = db.get(TelemetryRetentionDecisionV1Record, decision_id)
    if existing is not None:
        if (
            existing.receipt_id != receipt_id
            or existing.source_sha256 != source.sha256
            or existing.action != decision.action
            or existing.reason_code != decision.reason_code
        ):
            raise RuntimeError("retention_decision_identity_conflict")
        return
    db.add(
        TelemetryRetentionDecisionV1Record(
            decision_id=decision_id,
            receipt_id=receipt_id,
            source_kind=source.evidence_kind,
            source_ref=source.evidence_ref,
            source_sha256=source.sha256,
            source_received_at=source.received_at,
            service_or_check=source.service_or_check,
            environment=source.environment,
            tenant_ref=source.tenant_ref,
            privacy_class=source.privacy_class,
            retention_class=source.retention_class,
            legal_class=source.legal_class,
            policy_id=RETENTION_POLICY_ID,
            policy_version=RETENTION_POLICY_VERSION,
            policy_sha256=RETENTION_POLICY_SHA256,
            policy_mode=RETENTION_POLICY_MODE,
            clock_basis=RETENTION_CLOCK_BASIS,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            action=decision.action,
            reason_code=decision.reason_code,
            projected_delete_at=decision.projected_delete_at,
            applied=False,
            source_overwritten=False,
            created_at=window_end_at,
        )
    )


def _persist_routine_aggregates(
    db: Session,
    *,
    decisions: list[ShadowDecision],
    window_start_at: datetime,
    window_end_at: datetime,
) -> int:
    groups: dict[tuple[str, ...], list[ShadowDecision]] = defaultdict(list)
    for decision in decisions:
        if decision.action != "aggregate_then_delete":
            continue
        source = decision.source
        key = (
            source.evidence_kind,
            source.service_or_check,
            source.environment,
            source.tenant_ref or "",
            source.privacy_class,
            source.retention_class,
            decision.reason_code,
        )
        groups[key].append(decision)

    for key, group in sorted(groups.items()):
        key_payload = {
            "dimensions": list(key),
            "window_end_at": _wire_time(window_end_at),
            "policy_sha256": RETENTION_POLICY_SHA256,
        }
        group_key = hashlib.sha256(rfc8785.dumps(key_payload)).hexdigest()
        aggregate_id = uuid5(NAMESPACE_URL, f"cp5-routine-aggregate:{group_key}")
        derivation_id = uuid5(NAMESPACE_URL, f"cp5-aggregate-derivation:{group_key}")
        receipt_id = uuid5(NAMESPACE_URL, f"cp5-aggregate-receipt:{group_key}")
        source = group[0].source
        aggregate = TelemetryRoutineAggregatePayloadV1(
            schema_version="forge.dataforge.telemetry-routine-aggregate.v1",
            aggregate_id=aggregate_id,
            group_key=group_key,
            evidence_kind=source.evidence_kind,
            service_or_check=source.service_or_check,
            environment=source.environment,
            tenant_ref=source.tenant_ref,
            privacy_class=source.privacy_class,
            retention_class=source.retention_class,
            decision_reason_code=group[0].reason_code,
            source_count=len(group),
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            clock_basis="received_at",
            policy_id=RETENTION_POLICY_ID,
            policy_version=RETENTION_POLICY_VERSION,
            policy_sha256=RETENTION_POLICY_SHA256,
            policy_mode="shadow",
            source_overwritten=False,
        )
        aggregate_payload = aggregate.model_dump(mode="json")
        aggregate_digest = hashlib.sha256(rfc8785.dumps(aggregate_payload)).hexdigest()
        projected_delete_at = max(
            item.projected_delete_at
            for item in group
            if item.projected_delete_at is not None
        )
        receipt = _receipt(
            receipt_id=receipt_id,
            derivation_id=derivation_id,
            derivation_type="routine_success_aggregate",
            sources=[item.source for item in group],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            output_ref=aggregate_id,
            output_sha256=aggregate_digest,
            action="aggregate_then_delete",
            reason_code=group[0].reason_code,
            projected_delete_at=projected_delete_at,
        )
        _persist_receipt(db, receipt)
        existing = db.get(TelemetryRoutineAggregateV1Record, aggregate_id)
        if existing is not None:
            if (
                existing.receipt_id != receipt_id
                or existing.payload_digest != aggregate_digest
            ):
                raise RuntimeError("retention_aggregate_identity_conflict")
            continue
        db.add(
            TelemetryRoutineAggregateV1Record(
                aggregate_id=aggregate_id,
                receipt_id=receipt_id,
                payload_digest=aggregate_digest,
                payload=aggregate_payload,
                group_key=group_key,
                evidence_kind=source.evidence_kind,
                service_or_check=source.service_or_check,
                environment=source.environment,
                tenant_ref=source.tenant_ref,
                privacy_class=source.privacy_class,
                retention_class=source.retention_class,
                decision_reason_code=group[0].reason_code,
                source_count=len(group),
                window_start_at=window_start_at,
                window_end_at=window_end_at,
                policy_id=RETENTION_POLICY_ID,
                policy_version=RETENTION_POLICY_VERSION,
                policy_sha256=RETENTION_POLICY_SHA256,
                policy_mode=RETENTION_POLICY_MODE,
                created_at=window_end_at,
            )
        )
    return len(groups)


def _receipt(
    *,
    receipt_id: UUID,
    derivation_id: UUID,
    derivation_type: str,
    sources: list[ShadowSource],
    window_start_at: datetime,
    window_end_at: datetime,
    output_ref: UUID,
    output_sha256: str,
    action: str,
    reason_code: str,
    projected_delete_at: datetime | None,
) -> TelemetryDerivationReceiptV1:
    payload = {
        "schema_version": "TelemetryDerivationReceipt.v1",
        "receipt_id": str(receipt_id),
        "derivation_id": str(derivation_id),
        "derivation_type": derivation_type,
        "created_at": _wire_time(window_end_at),
        "producer": {
            "service_name": "dataforge",
            "version": RETENTION_POLICY["producer_version"],
        },
        "policy": {
            "policy_id": RETENTION_POLICY_ID,
            "version": RETENTION_POLICY_VERSION,
            "sha256": RETENTION_POLICY_SHA256,
            "mode": "shadow",
        },
        "window": {
            "clock_basis": "received_at",
            "start_at": _wire_time(window_start_at),
            "end_at": _wire_time(window_end_at),
        },
        "source_evidence": [
            {
                "evidence_kind": source.evidence_kind,
                "evidence_ref": source.evidence_ref,
                "sha256": source.sha256,
                "received_at": _wire_time(source.received_at),
                "privacy_class": source.privacy_class,
                "retention_class": source.retention_class,
                "legal_class": source.legal_class,
            }
            for source in sources
        ],
        "sampling": {
            "method": "all",
            "population_count": len(sources),
            "included_count": len(sources),
            "sample_rate": 1.0,
            "seed_sha256": None,
        },
        "exclusions": [],
        "output": {
            "output_kind": derivation_type,
            "output_ref": str(output_ref),
            "sha256": output_sha256,
        },
        "decision": {
            "action": action,
            "reason_code": reason_code,
            "applied": False,
            "projected_delete_at": (
                _wire_time(projected_delete_at)
                if projected_delete_at is not None
                else None
            ),
            "source_overwritten": False,
        },
        "uncertainty": {
            "state": "complete",
            "reason_codes": [],
        },
        "missing_evidence": [],
    }
    return validate_telemetry_derivation_receipt_v1(payload)


def _persist_receipt(
    db: Session,
    receipt: TelemetryDerivationReceiptV1,
) -> None:
    payload = receipt.model_dump(mode="json")
    digest = derivation_receipt_digest(receipt)
    existing = db.get(TelemetryDerivationReceiptV1Record, receipt.receipt_id)
    if existing is not None:
        if existing.payload_digest != digest:
            raise RuntimeError("derivation_receipt_identity_conflict")
        return
    db.add(
        TelemetryDerivationReceiptV1Record(
            receipt_id=receipt.receipt_id,
            derivation_id=receipt.derivation_id,
            payload_digest=digest,
            payload=payload,
            derivation_type=receipt.derivation_type,
            producer_service_name=receipt.producer.service_name,
            producer_version=receipt.producer.version,
            policy_id=receipt.policy.policy_id,
            policy_version=receipt.policy.version,
            policy_sha256=receipt.policy.sha256,
            policy_mode=receipt.policy.mode,
            clock_basis=receipt.window.clock_basis,
            window_start_at=receipt.window.start_at,
            window_end_at=receipt.window.end_at,
            output_kind=receipt.output.output_kind,
            output_ref=receipt.output.output_ref,
            output_sha256=receipt.output.sha256,
            decision_action=receipt.decision.action,
            decision_reason_code=receipt.decision.reason_code,
            decision_applied=receipt.decision.applied,
            source_overwritten=receipt.decision.source_overwritten,
            uncertainty_state=receipt.uncertainty.state,
            source_count=len(receipt.source_evidence),
            created_at=receipt.created_at,
        )
    )


def _wire_time(value: datetime) -> str:
    return _utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

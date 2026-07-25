"""CP6 evidence-grounded incident candidate derivation and source proof."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from forge_telemetry import (
    IncidentCandidateV1,
    incident_candidate_fingerprint,
    validate_incident_candidate_v1,
)
from sqlalchemy.orm import Session

from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeEventV1Record,
)

INCIDENT_FINGERPRINT_VERSION = "incident-candidate-fingerprint.v1"
INCIDENT_RULES_VERSION = "cp6.1"
INCIDENT_CALIBRATION_VERSION = "cp6.rules.v1"
_PRIVACY_RANK = {
    "public": 0,
    "internal": 1,
    "restricted": 2,
    "confidential": 3,
}


class IncidentCandidateSourceError(ValueError):
    """A candidate references source evidence DataForge cannot prove."""


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _legal_class(privacy_class: str, retention_class: str) -> str:
    if retention_class == "legal_hold":
        return "legal_hold"
    if privacy_class in {"restricted", "confidential"}:
        return "regulated"
    return "standard"


def _maximum_privacy(classes: list[str]) -> str:
    return max(classes, key=lambda value: _PRIVACY_RANK[value])


def build_deterministic_incident_candidate(
    check: ForgeCheckResultV1Record,
    correlated_events: list[ForgeEventV1Record],
    *,
    window_start_at: datetime,
    window_end_at: datetime,
    created_at: datetime,
) -> IncidentCandidateV1:
    """Build one non-authoritative candidate from exact durable source rows."""

    if check.status not in {"failed", "timed_out", "blocked", "indeterminate"}:
        raise ValueError("incident_candidate_requires_failed_check")
    window_start_at = _utc(window_start_at)
    window_end_at = _utc(window_end_at)
    created_at = _utc(created_at)
    if window_start_at > window_end_at or created_at < window_end_at:
        raise ValueError("incident_candidate_window_invalid")
    check_received_at = _utc(check.received_at)
    if not window_start_at <= check_received_at <= window_end_at:
        raise ValueError("incident_candidate_check_outside_window")

    for event in correlated_events:
        if (
            event.environment != check.environment
            or event.tenant_ref != check.tenant_ref
            or event.correlation_id != check.correlation_id
            or not window_start_at <= _utc(event.received_at) <= window_end_at
        ):
            raise ValueError("incident_candidate_event_scope_conflict")

    source_evidence: list[dict[str, object]] = [
        {
            "evidence_kind": "forge_check_result",
            "evidence_ref": str(check.result_id),
            "sha256": check.payload_digest,
            "observed_at": _utc_text(check_received_at),
            "clock_basis": "received_at",
            "privacy_class": check.privacy_class,
            "retention_class": "long",
            "legal_class": _legal_class(check.privacy_class, "long"),
        }
    ]
    ordered_events = sorted(
        correlated_events,
        key=lambda item: (_utc(item.received_at), str(item.event_id)),
    )
    for event in ordered_events:
        source_evidence.append(
            {
                "evidence_kind": "forge_event",
                "evidence_ref": str(event.event_id),
                "sha256": event.event_digest,
                "observed_at": _utc_text(event.received_at),
                "clock_basis": "received_at",
                "privacy_class": event.privacy_class,
                "retention_class": event.retention_class,
                "legal_class": _legal_class(
                    event.privacy_class,
                    event.retention_class,
                ),
            }
        )

    trace_ids = sorted(
        {
            value
            for value in (
                check.trace_id,
                *(event.trace_id for event in correlated_events),
            )
            if value is not None
        }
    )
    source_refs = [
        str(check.result_id),
        *[str(event.event_id) for event in ordered_events],
    ]
    has_correlated_error = any(
        event.severity in {"error", "critical"}
        or event.outcome in {"fail", "blocked", "indeterminate"}
        for event in correlated_events
    )
    if has_correlated_error:
        cause_code = "correlated_service_failure"
        cause_summary = (
            "Failed check and correlated error evidence occurred in the same window."
        )
        confidence = 7200
    else:
        cause_code = "check_failure_without_correlated_error"
        cause_summary = (
            "The check failed, but no correlated error event proves the cause."
        )
        confidence = 4500

    missing_evidence = [
        "baseline_deviation_evidence",
        "configuration_change_evidence",
        "deployment_change_evidence",
    ]
    uncertainty_reasons = [
        "baseline_evidence_missing",
        "change_evidence_missing",
    ]
    if not correlated_events:
        missing_evidence.append("correlated_event_evidence")
        uncertainty_reasons.append("correlated_event_missing")
    if not trace_ids:
        missing_evidence.append("trace_detail_evidence")
        uncertainty_reasons.append("trace_detail_missing")

    payload: dict[str, object] = {
        "schema_version": "IncidentCandidate.v1",
        "candidate_id": str(uuid4()),
        "created_at": _utc_text(created_at),
        "environment": check.environment,
        "tenant_ref": check.tenant_ref,
        "correlation_id": (
            str(check.correlation_id) if check.correlation_id is not None else None
        ),
        "trace_ids": trace_ids,
        "window": {
            "clock_basis": "evidence_observed_at",
            "start_at": _utc_text(window_start_at),
            "end_at": _utc_text(window_end_at),
        },
        "source_evidence": source_evidence,
        "suspected_cause": {
            "cause_code": cause_code,
            "summary": cause_summary,
            "evidence_refs": source_refs,
        },
        "alternatives": [
            {
                "cause_code": "dependency_failure",
                "summary": "A dependency failure may have produced the observations.",
                "evidence_refs": [str(event.event_id) for event in ordered_events],
            },
            {
                "cause_code": "recent_change",
                "summary": (
                    "A deployment or configuration change remains possible but unproven."
                ),
                "evidence_refs": [],
            },
        ],
        "confidence": {
            "score_basis_points": confidence,
            "method": "deterministic_rules",
            "calibration_version": INCIDENT_CALIBRATION_VERSION,
        },
        "uncertainty": {
            "state": "partial",
            "reason_codes": sorted(set(uncertainty_reasons)),
        },
        "missing_evidence": sorted(set(missing_evidence)),
        "deduplication": {
            "fingerprint_version": INCIDENT_FINGERPRINT_VERSION,
            "fingerprint_sha256": "0" * 64,
        },
        "analysis_provenance": {
            "analysis_kind": "deterministic_rules",
            "producer_service": "dataforge",
            "producer_version": INCIDENT_RULES_VERSION,
            "provider": None,
            "model": None,
            "prompt_sha256": None,
            "model_response_sha256": None,
            "run_receipt_ref": None,
        },
        "privacy_class": _maximum_privacy(
            [str(source["privacy_class"]) for source in source_evidence]
        ),
        "authority": {
            "classification": "derived_candidate",
            "candidate_only": True,
            "can_repair": False,
            "can_rollback": False,
            "can_notify": False,
            "can_promote": False,
            "requires_human_decision": True,
            "source_overwritten": False,
        },
    }
    payload["deduplication"]["fingerprint_sha256"] = (  # type: ignore[index]
        incident_candidate_fingerprint(payload)
    )
    return validate_incident_candidate_v1(payload)


def verify_incident_candidate_sources(
    db: Session,
    candidate: IncidentCandidateV1,
) -> None:
    """Prove every admitted source against an immutable DataForge row."""

    candidate_correlation = candidate.correlation_id
    candidate_traces = set(candidate.trace_ids)
    for source in candidate.source_evidence:
        try:
            source_id = UUID(source.evidence_ref)
        except ValueError as exc:
            raise IncidentCandidateSourceError(
                "incident_candidate_source_unverifiable"
            ) from exc

        if source.evidence_kind == "forge_event":
            event = db.get(ForgeEventV1Record, source_id)
            if event is None or any(
                (
                    event.event_digest != source.sha256,
                    _utc(event.received_at) != _utc(source.observed_at),
                    event.environment != candidate.environment,
                    event.tenant_ref != candidate.tenant_ref,
                    event.privacy_class != source.privacy_class,
                    event.retention_class != source.retention_class,
                    _legal_class(event.privacy_class, event.retention_class)
                    != source.legal_class,
                    candidate_correlation is not None
                    and event.correlation_id != candidate_correlation,
                    event.trace_id is not None
                    and event.trace_id not in candidate_traces,
                )
            ):
                raise IncidentCandidateSourceError(
                    "incident_candidate_source_mismatch"
                )
            continue

        if source.evidence_kind == "forge_check_result":
            check = db.get(ForgeCheckResultV1Record, source_id)
            if check is None or any(
                (
                    check.payload_digest != source.sha256,
                    _utc(check.received_at) != _utc(source.observed_at),
                    check.environment != candidate.environment,
                    check.tenant_ref != candidate.tenant_ref,
                    check.privacy_class != source.privacy_class,
                    source.retention_class != "long",
                    _legal_class(check.privacy_class, "long") != source.legal_class,
                    candidate_correlation is not None
                    and check.correlation_id != candidate_correlation,
                    check.trace_id is not None
                    and check.trace_id not in candidate_traces,
                )
            ):
                raise IncidentCandidateSourceError(
                    "incident_candidate_source_mismatch"
                )
            continue

        raise IncidentCandidateSourceError(
            "incident_candidate_source_unverifiable"
        )

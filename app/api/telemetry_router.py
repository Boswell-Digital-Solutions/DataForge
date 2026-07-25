"""Authenticated canonical ForgeEvent.v1 capability and ingest boundary."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from forge_telemetry import IncidentCandidateV1, TelemetryDerivationReceiptV1
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.logging_config import get_logger
from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeCheckRunReceiptV1Record,
    ForgeEventV1Record,
    IncidentCandidateV1Record,
    TelemetryDerivationReceiptV1Record,
    TelemetryRetentionDecisionV1Record,
    TelemetryRoutineAggregateV1Record,
)
from app.models.telemetry_schemas import (
    ForgeCheckEvidenceIngestResponseV1,
    ForgeCheckEvidenceReadItemV1,
    ForgeCheckEvidenceReadV1,
    ForgeCheckEvidenceSubmissionV1,
    ForgeEventCorrelationReadV1,
    ForgeEventCorrelationSummaryV1,
    ForgeEventV1IngestResponse,
    ForgeEventV1Submission,
    ForgeTelemetrySinkCapabilityV1,
    IncidentCandidateIngestResponseV1,
    IncidentCandidateReadItemV1,
    IncidentCandidateReadV1,
    IncidentCandidateSubmissionV1,
    TelemetryRetentionDecisionReadItemV1,
    TelemetryRetentionShadowReadV1,
    TelemetryRoutineAggregatePayloadV1,
    TelemetryRoutineAggregateReadItemV1,
    event_digest,
    forge_check_payload_digest,
    forge_event_v1_write_enabled,
    forge_telemetry_sink_capability,
    incident_candidate_payload_digest,
)
from app.telemetry_incidents import (
    IncidentCandidateSourceError,
    verify_incident_candidate_sources,
)
from app.telemetry_retention import (
    RETENTION_CLOCK_BASIS,
    RETENTION_POLICY_ID,
    RETENTION_POLICY_MODE,
    RETENTION_POLICY_SHA256,
    RETENTION_POLICY_VERSION,
)
from app.telemetry_database import (
    get_telemetry_db,
    require_telemetry_rate_budget,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])
MAX_CORRELATION_EVENTS = 200
MAX_CORRELATION_RESPONSE_BYTES = 256 * 1024
MAX_CHECK_EVIDENCE_ITEMS = 200
MAX_CHECK_EVIDENCE_RESPONSE_BYTES = 256 * 1024
MAX_RETENTION_SHADOW_ITEMS = 50
MAX_RETENTION_SHADOW_RESPONSE_BYTES = 512 * 1024
MAX_INCIDENT_CANDIDATE_ITEMS = 25
MAX_INCIDENT_CANDIDATE_RESPONSE_BYTES = 512 * 1024


class EventIdentityConflict(ValueError):
    """The event ID is already bound to different canonical content."""


class CheckEvidenceIdentityConflict(ValueError):
    """A result or receipt ID is already bound to different content."""


class IncidentCandidateIdentityConflict(ValueError):
    """A candidate ID is already bound to different canonical content."""


def forge_event_correlation_read_enabled() -> bool:
    """Require an explicit rollout switch for the CP3 read boundary."""

    return (
        os.getenv("DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED", "false")
        .strip()
        .lower()
        == "true"
    )


def forge_check_evidence_write_enabled() -> bool:
    """Fail closed unless the CP4 evidence writer is explicitly enabled."""

    return (
        os.getenv("DATAFORGE_FORGE_CHECK_EVIDENCE_WRITE_ENABLED", "false")
        .strip()
        .lower()
        == "true"
    )


def forge_check_evidence_read_enabled() -> bool:
    """Fail closed unless the CP4 evidence read projection is enabled."""

    return (
        os.getenv("DATAFORGE_FORGE_CHECK_EVIDENCE_READ_ENABLED", "false")
        .strip()
        .lower()
        == "true"
    )


def telemetry_retention_shadow_read_enabled() -> bool:
    """Fail closed unless the CP5 read-only shadow projection is enabled."""

    return (
        os.getenv(
            "DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED",
            "false",
        )
        .strip()
        .lower()
        == "true"
    )


def incident_candidate_write_enabled() -> bool:
    """Fail closed unless the CP6 candidate writer is explicitly enabled."""

    return (
        os.getenv(
            "DATAFORGE_INCIDENT_CANDIDATE_WRITE_ENABLED",
            "false",
        )
        .strip()
        .lower()
        == "true"
    )


def incident_candidate_read_enabled() -> bool:
    """Fail closed unless the CP6 candidate-only read is explicitly enabled."""

    return (
        os.getenv(
            "DATAFORGE_INCIDENT_CANDIDATE_READ_ENABLED",
            "false",
        )
        .strip()
        .lower()
        == "true"
    )


def _authorize_correlation_read(
    auth: AuthContext,
    *,
    environment: str,
    tenant_ref: str | None,
) -> set[str]:
    """Require Forge_Command's exact read identity and requested scope."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:read" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_read_scope_required"},
        )
    expected_binding = {
        "service_name": "forge_command",
        "environment": environment,
        "tenant_ref": tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )
    return {scope for scope in scopes if isinstance(scope, str)}


def _authorize_check_evidence_write(
    auth: AuthContext,
    evidence: ForgeCheckEvidenceSubmissionV1,
) -> None:
    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:write:checks" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forge_check_write_scope_required"},
        )
    expected_binding = {
        "service_name": "forgeagents",
        "environment": evidence.environment,
        "tenant_ref": evidence.tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )


def _authorize_check_evidence_read(
    auth: AuthContext,
    *,
    environment: str,
    tenant_ref: str | None,
) -> None:
    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:read:checks" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forge_check_read_scope_required"},
        )
    expected_binding = {
        "service_name": "forge_command",
        "environment": environment,
        "tenant_ref": tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )


def _authorize_retention_shadow_read(
    auth: AuthContext,
    *,
    environment: str,
    tenant_ref: str | None,
) -> set[str]:
    """Require Forge_Command's dedicated CP5 read identity and exact scope."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:read:retention" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_retention_read_scope_required"},
        )
    expected_binding = {
        "service_name": "forge_command",
        "environment": environment,
        "tenant_ref": tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )
    return {scope for scope in scopes if isinstance(scope, str)}


def _authorize_incident_candidate_write(
    auth: AuthContext,
    submission: IncidentCandidateSubmissionV1,
) -> None:
    """Require the exact analysis producer identity and CP6 write scope."""

    producer_service = submission.candidate.analysis_provenance.producer_service
    if producer_service not in {"dataforge", "neuroforge"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "incident_candidate_producer_forbidden"},
        )
    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if (
        not isinstance(scopes, list)
        or "telemetry:write:incident-candidates" not in scopes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "incident_candidate_write_scope_required"},
        )
    expected_binding = {
        "service_name": producer_service,
        "environment": submission.environment,
        "tenant_ref": submission.tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )


def _authorize_incident_candidate_read(
    auth: AuthContext,
    *,
    environment: str,
    tenant_ref: str | None,
) -> set[str]:
    """Require Forge_Command's dedicated CP6 read identity and exact scope."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if (
        not isinstance(scopes, list)
        or "telemetry:read:incident-candidates" not in scopes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "incident_candidate_read_scope_required"},
        )
    expected_binding = {
        "service_name": "forge_command",
        "environment": environment,
        "tenant_ref": tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )
    return {scope for scope in scopes if isinstance(scope, str)}


def _admit_telemetry_rate_budget(
    _auth: AuthContext = Depends(require_api_key),
) -> None:
    """Charge only authenticated requests before database checkout."""

    require_telemetry_rate_budget()


def _authorize_event(auth: AuthContext, event: ForgeEventV1Submission) -> None:
    """Require an explicitly scoped and identity-bound canonical service key."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )

    # AuthorForge has a stricter content-free analytics contract. Even a
    # correctly bound telemetry key cannot use this attributes-bearing route.
    if event.service_name == "authorforge":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "authorforge_canonical_telemetry_forbidden"},
        )

    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:write" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_write_scope_required"},
        )

    expected_binding = {
        "service_name": event.service_name,
        "environment": event.environment,
        "tenant_ref": event.tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )


def _storage_values(
    event: ForgeEventV1Submission,
    digest: str,
    *,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    values = event.model_dump(mode="python")
    values["event_digest"] = digest
    if received_at is not None:
        values["received_at"] = received_at
    return values


def _binding_matches(
    record: ForgeEventV1Record,
    event: ForgeEventV1Submission,
    digest: str,
) -> bool:
    return (
        record.event_digest == digest
        and record.schema_version == event.schema_version
        and record.service_name == event.service_name
        and record.service_instance_id == event.service_instance_id
        and record.environment == event.environment
        and record.tenant_ref == event.tenant_ref
    )


def _persist_sqlite(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    """Exercise equivalent identity behavior in the unit-test database."""

    values = _storage_values(event, digest, received_at=datetime.now(UTC))
    statement = (
        sqlite_insert(ForgeEventV1Record.__table__)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = db.execute(statement)
    if result.rowcount == 1:
        return "inserted"

    record = db.execute(
        select(ForgeEventV1Record).where(ForgeEventV1Record.event_id == event.event_id)
    ).scalar_one()
    if _binding_matches(record, event, digest):
        return "exact_replay"
    raise EventIdentityConflict("event_identity_conflict")


def _persist_postgresql(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    """Invoke the migration-owned atomic identity transaction."""

    candidate = json.dumps(
        event.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    outcome = db.execute(
        text(
            """
            SELECT ingest_forge_event_v1(
                CAST(:candidate AS jsonb),
                CAST(:event_digest AS char(64))
            )
            """
        ),
        {"candidate": candidate, "event_digest": digest},
    ).scalar_one()
    if outcome == "event_identity_conflict":
        raise EventIdentityConflict(outcome)
    if outcome not in {"inserted", "exact_replay"}:
        raise RuntimeError("canonical telemetry ingest returned an unknown outcome")
    return outcome


def _persist_event(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return _persist_postgresql(db, event, digest)
    if dialect == "sqlite":
        return _persist_sqlite(db, event, digest)
    raise RuntimeError("canonical telemetry ingest requires PostgreSQL")


def _check_result_values(
    evidence: ForgeCheckEvidenceSubmissionV1,
    digest: str,
) -> dict[str, Any]:
    result = evidence.result
    return {
        "result_id": result.result_id,
        "payload_digest": digest,
        "payload": result.model_dump(mode="json"),
        "run_id": result.run_id,
        "check_id": result.check_id,
        "check_revision": result.check_revision,
        "definition_sha256": result.definition_sha256,
        "environment": evidence.environment,
        "tenant_ref": evidence.tenant_ref,
        "evaluation_mode": result.evaluation_mode,
        "status": result.status,
        "reason_code": result.reason_code,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "duration_ms": result.duration_ms,
        "assertion_passed": result.assertion_passed,
        "slo_included": result.slo.included,
        "uptime_included": result.slo.uptime_included,
        "baseline_included": result.slo.baseline_included,
        "cost_units_observed": result.cost_units_observed,
        "privacy_class": result.privacy_class,
        "correlation_id": result.correlation_id,
        "trace_id": result.trace_id,
    }


def _check_receipt_values(
    evidence: ForgeCheckEvidenceSubmissionV1,
    digest: str,
) -> dict[str, Any]:
    receipt = evidence.receipt
    return {
        "receipt_id": receipt.receipt_id,
        "payload_digest": digest,
        "payload": receipt.model_dump(mode="json"),
        "run_id": receipt.run_id,
        "result_id": receipt.result_id,
        "check_id": receipt.check_id,
        "definition_sha256": receipt.definition_sha256,
        "environment": evidence.environment,
        "tenant_ref": evidence.tenant_ref,
        "source_repository": receipt.source.repository,
        "source_commit": receipt.source.commit,
        "source_path": receipt.source.path,
        "runner_service_name": receipt.runner.service_name,
        "runner_version": receipt.runner.version,
        "trigger": receipt.trigger,
        "evaluation_mode": receipt.evaluation_mode,
        "status": receipt.status,
        "started_at": receipt.started_at,
        "observed_at": receipt.observed_at,
        "slo_included": receipt.slo.included,
        "uptime_included": receipt.slo.uptime_included,
        "baseline_included": receipt.slo.baseline_included,
        "slo_reason": receipt.slo.reason,
        "max_cost_units": receipt.cost.max_cost_units,
        "observed_cost_units": receipt.cost.observed_cost_units,
        "cost_unit": receipt.cost.unit,
        "kill_switch_ref": receipt.kill_switch.ref,
        "kill_switch_enabled": receipt.kill_switch.enabled,
        "evidence_refs": [str(value) for value in receipt.evidence_refs],
    }


def _insert_check_row(
    db: Session,
    model: type[ForgeCheckResultV1Record] | type[ForgeCheckRunReceiptV1Record],
    values: dict[str, Any],
    key: str,
) -> bool:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = (
            postgresql_insert(model.__table__)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[key])
        )
    elif dialect == "sqlite":
        statement = (
            sqlite_insert(model.__table__)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[key])
        )
    else:
        raise RuntimeError("canonical check evidence requires PostgreSQL")
    return db.execute(statement).rowcount == 1


def _persist_check_evidence(
    db: Session,
    evidence: ForgeCheckEvidenceSubmissionV1,
    result_digest: str,
    receipt_digest: str,
) -> str:
    result_inserted = _insert_check_row(
        db,
        ForgeCheckResultV1Record,
        _check_result_values(evidence, result_digest),
        "result_id",
    )
    stored_result = db.execute(
        select(ForgeCheckResultV1Record).where(
            ForgeCheckResultV1Record.result_id == evidence.result.result_id
        )
    ).scalar_one()
    if (
        stored_result.payload_digest != result_digest
        or stored_result.environment != evidence.environment
        or stored_result.tenant_ref != evidence.tenant_ref
    ):
        raise CheckEvidenceIdentityConflict("check_result_identity_conflict")

    receipt_inserted = _insert_check_row(
        db,
        ForgeCheckRunReceiptV1Record,
        _check_receipt_values(evidence, receipt_digest),
        "receipt_id",
    )
    receipt_by_id = db.execute(
        select(ForgeCheckRunReceiptV1Record).where(
            ForgeCheckRunReceiptV1Record.receipt_id == evidence.receipt.receipt_id
        )
    ).scalar_one_or_none()
    receipt_by_result = db.execute(
        select(ForgeCheckRunReceiptV1Record).where(
            ForgeCheckRunReceiptV1Record.result_id == evidence.result.result_id
        )
    ).scalar_one_or_none()
    stored_receipt = receipt_by_id or receipt_by_result
    if (
        stored_receipt is None
        or (
            receipt_by_id is not None
            and receipt_by_result is not None
            and receipt_by_id.receipt_id != receipt_by_result.receipt_id
        )
        or stored_receipt.receipt_id != evidence.receipt.receipt_id
        or stored_receipt.payload_digest != receipt_digest
        or stored_receipt.environment != evidence.environment
        or stored_receipt.tenant_ref != evidence.tenant_ref
    ):
        raise CheckEvidenceIdentityConflict("check_receipt_identity_conflict")
    return "inserted" if result_inserted or receipt_inserted else "exact_replay"


def _incident_candidate_values(
    submission: IncidentCandidateSubmissionV1,
    digest: str,
) -> dict[str, Any]:
    candidate = submission.candidate
    provenance = candidate.analysis_provenance
    authority = candidate.authority
    return {
        "candidate_id": candidate.candidate_id,
        "payload_digest": digest,
        "payload": candidate.model_dump(mode="json"),
        "fingerprint_version": candidate.deduplication.fingerprint_version,
        "fingerprint_sha256": candidate.deduplication.fingerprint_sha256,
        "environment": submission.environment,
        "tenant_ref": submission.tenant_ref,
        "correlation_id": candidate.correlation_id,
        "trace_ids": candidate.trace_ids,
        "window_clock_basis": candidate.window.clock_basis,
        "window_start_at": candidate.window.start_at,
        "window_end_at": candidate.window.end_at,
        "suspected_cause_code": candidate.suspected_cause.cause_code,
        "confidence_basis_points": candidate.confidence.score_basis_points,
        "confidence_method": candidate.confidence.method,
        "uncertainty_state": candidate.uncertainty.state,
        "privacy_class": candidate.privacy_class,
        "analysis_kind": provenance.analysis_kind,
        "producer_service": provenance.producer_service,
        "producer_version": provenance.producer_version,
        "provider": provenance.provider,
        "model": provenance.model,
        "prompt_sha256": provenance.prompt_sha256,
        "model_response_sha256": provenance.model_response_sha256,
        "run_receipt_ref": provenance.run_receipt_ref,
        "candidate_only": authority.candidate_only,
        "can_repair": authority.can_repair,
        "can_rollback": authority.can_rollback,
        "can_notify": authority.can_notify,
        "can_promote": authority.can_promote,
        "requires_human_decision": authority.requires_human_decision,
        "source_overwritten": authority.source_overwritten,
        "created_at": candidate.created_at,
    }


def _persist_incident_candidate(
    db: Session,
    submission: IncidentCandidateSubmissionV1,
    digest: str,
) -> tuple[str, IncidentCandidateV1Record]:
    candidate = submission.candidate
    values = _incident_candidate_values(submission, digest)
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = (
            postgresql_insert(IncidentCandidateV1Record.__table__)
            .values(**values)
            .on_conflict_do_nothing()
        )
    elif dialect == "sqlite":
        statement = (
            sqlite_insert(IncidentCandidateV1Record.__table__)
            .values(**values)
            .on_conflict_do_nothing()
        )
    else:
        raise RuntimeError("incident candidates require PostgreSQL")
    inserted = db.execute(statement).rowcount == 1
    if inserted:
        record = db.get(IncidentCandidateV1Record, candidate.candidate_id)
        if record is None:
            raise RuntimeError("incident candidate insert was not readable")
        return "inserted", record

    by_id = db.get(IncidentCandidateV1Record, candidate.candidate_id)
    if by_id is not None:
        if (
            by_id.payload_digest == digest
            and by_id.fingerprint_sha256
            == candidate.deduplication.fingerprint_sha256
            and by_id.environment == submission.environment
            and by_id.tenant_ref == submission.tenant_ref
        ):
            return "exact_replay", by_id
        raise IncidentCandidateIdentityConflict(
            "incident_candidate_identity_conflict"
        )

    by_fingerprint = db.execute(
        select(IncidentCandidateV1Record).where(
            IncidentCandidateV1Record.fingerprint_sha256
            == candidate.deduplication.fingerprint_sha256
        )
    ).scalar_one_or_none()
    if by_fingerprint is not None:
        if (
            by_fingerprint.environment != submission.environment
            or by_fingerprint.tenant_ref != submission.tenant_ref
        ):
            raise IncidentCandidateIdentityConflict(
                "incident_candidate_scope_conflict"
            )
        return "deduplicated", by_fingerprint
    raise IncidentCandidateIdentityConflict(
        "incident_candidate_identity_conflict"
    )


@router.get(
    "/capabilities/forge-event-v1",
    response_model=ForgeTelemetrySinkCapabilityV1,
)
def get_forge_event_v1_capability(
    _auth: AuthContext = Depends(require_api_key),
) -> ForgeTelemetrySinkCapabilityV1:
    """Return the exact active canonical sink capability."""

    return forge_telemetry_sink_capability()


@router.post(
    "/checks/evidence",
    response_model=ForgeCheckEvidenceIngestResponseV1,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def ingest_forge_check_evidence(
    evidence: ForgeCheckEvidenceSubmissionV1,
    response: Response,
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeCheckEvidenceIngestResponseV1:
    """Persist one debug-only result and its directly linked receipt."""

    if not forge_check_evidence_write_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "forge_check_evidence_write_disabled"},
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    _authorize_check_evidence_write(auth, evidence)
    result_digest = forge_check_payload_digest(evidence.result)
    receipt_digest = forge_check_payload_digest(evidence.receipt)
    try:
        identity_outcome = _persist_check_evidence(
            db,
            evidence,
            result_digest,
            receipt_digest,
        )
        record = db.execute(
            select(ForgeCheckResultV1Record).where(
                ForgeCheckResultV1Record.result_id == evidence.result.result_id
            )
        ).scalar_one()
        db.commit()
    except CheckEvidenceIdentityConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc)},
        ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    if identity_outcome == "exact_replay":
        response.status_code = status.HTTP_200_OK
    return ForgeCheckEvidenceIngestResponseV1(
        result_id=evidence.result.result_id,
        receipt_id=evidence.receipt.receipt_id,
        result_digest=result_digest,
        receipt_digest=receipt_digest,
        received_at=record.received_at,
        identity_outcome=identity_outcome,
    )


@router.get(
    "/checks/results",
    response_model=ForgeCheckEvidenceReadV1,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def read_forge_check_evidence(
    environment: str = Query(pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    tenant_ref: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    check_id: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    limit: int = Query(default=50, ge=1, le=MAX_CHECK_EVIDENCE_ITEMS),
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeCheckEvidenceReadV1:
    """Return a bounded, scope-bound result and receipt projection."""

    if not forge_check_evidence_read_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "forge_check_evidence_read_disabled"},
        )
    _authorize_check_evidence_read(
        auth,
        environment=environment,
        tenant_ref=tenant_ref,
    )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    statement = (
        select(ForgeCheckResultV1Record, ForgeCheckRunReceiptV1Record)
        .join(
            ForgeCheckRunReceiptV1Record,
            ForgeCheckRunReceiptV1Record.result_id
            == ForgeCheckResultV1Record.result_id,
        )
        .where(
            ForgeCheckResultV1Record.environment == environment,
            ForgeCheckRunReceiptV1Record.environment == environment,
        )
        .order_by(
            ForgeCheckRunReceiptV1Record.observed_at.desc(),
            ForgeCheckRunReceiptV1Record.receipt_id,
        )
        .limit(limit + 1)
    )
    if tenant_ref is None:
        statement = statement.where(
            ForgeCheckResultV1Record.tenant_ref.is_(None),
            ForgeCheckRunReceiptV1Record.tenant_ref.is_(None),
        )
    else:
        statement = statement.where(
            ForgeCheckResultV1Record.tenant_ref == tenant_ref,
            ForgeCheckRunReceiptV1Record.tenant_ref == tenant_ref,
        )
    if check_id is not None:
        statement = statement.where(ForgeCheckResultV1Record.check_id == check_id)
    try:
        rows = list(db.execute(statement).all())
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    partial = len(rows) > limit
    observed_at = datetime.now(UTC)
    items: list[ForgeCheckEvidenceReadItemV1] = []
    for result_record, receipt_record in rows[:limit]:
        items.append(
            ForgeCheckEvidenceReadItemV1(
                result=result_record.payload,
                receipt=receipt_record.payload,
                result_received_at=result_record.received_at,
                receipt_received_at=receipt_record.received_at,
            )
        )
        size_probe = ForgeCheckEvidenceReadV1(
            environment=environment,
            tenant_ref=tenant_ref,
            shared_state="partial",
            items=items,
            observed_at=observed_at,
        )
        if len(size_probe.model_dump_json().encode("utf-8")) > (
            MAX_CHECK_EVIDENCE_RESPONSE_BYTES
        ):
            items.pop()
            partial = True
            break

    return ForgeCheckEvidenceReadV1(
        environment=environment,
        tenant_ref=tenant_ref,
        shared_state="partial" if partial else ("available" if items else "missing"),
        items=items,
        observed_at=observed_at,
    )


@router.get(
    "/correlations/{correlation_id}",
    response_model=ForgeEventCorrelationReadV1,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def read_forge_event_correlation(
    correlation_id: UUID,
    environment: str = Query(pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    tenant_ref: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeEventCorrelationReadV1:
    """Return a payload-free correlation projection under exact scope binding."""

    if not forge_event_correlation_read_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_correlation_disabled"},
        )
    scopes = _authorize_correlation_read(
        auth,
        environment=environment,
        tenant_ref=tenant_ref,
    )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    try:
        observed_scopes = {
            (row.environment, row.tenant_ref)
            for row in db.execute(
                select(
                    ForgeEventV1Record.environment,
                    ForgeEventV1Record.tenant_ref,
                )
                .where(ForgeEventV1Record.correlation_id == correlation_id)
                .distinct()
                .limit(2)
            ).all()
        }
        records = list(
            db.execute(
                select(ForgeEventV1Record)
                .where(ForgeEventV1Record.correlation_id == correlation_id)
                .order_by(ForgeEventV1Record.occurred_at, ForgeEventV1Record.event_id)
                .limit(MAX_CORRELATION_EVENTS + 1)
            ).scalars()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    requested_scope = (environment, tenant_ref)
    if any(scope != requested_scope for scope in observed_scopes):
        logger.warning(
            "Canonical Forge telemetry correlation scope conflict",
            extra={"correlation_id": str(correlation_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "correlation_scope_conflict"},
        )

    partial = len(records) > MAX_CORRELATION_EVENTS
    records = records[:MAX_CORRELATION_EVENTS]
    can_read_restricted = "telemetry:read:restricted" in scopes
    summaries: list[ForgeEventCorrelationSummaryV1] = []
    observed_at = datetime.now(UTC)
    for record in records:
        restricted = (
            record.privacy_class in {"restricted", "confidential"}
            and not can_read_restricted
        )
        if restricted:
            detail_state = "restricted"
        elif not record.sampled:
            detail_state = "sampled"
        elif record.trace_id is None:
            detail_state = "missing"
        else:
            detail_state = "available"
        summaries.append(
            ForgeEventCorrelationSummaryV1(
                event_id=record.event_id,
                occurred_at=record.occurred_at,
                received_at=record.received_at,
                service_name=record.service_name,
                event_type=None if restricted else record.event_type,
                severity=record.severity,
                outcome=record.outcome,
                trace_id=None if restricted else record.trace_id,
                span_id=None if restricted else record.span_id,
                parent_span_id=None if restricted else record.parent_span_id,
                privacy_class=record.privacy_class,
                retention_class=record.retention_class,
                detail_state=detail_state,
            )
        )
        size_probe = ForgeEventCorrelationReadV1(
            correlation_id=correlation_id,
            environment=environment,
            tenant_ref=tenant_ref,
            shared_state="partial",
            events=summaries,
            observed_at=observed_at,
        )
        if len(size_probe.model_dump_json().encode("utf-8")) > (
            MAX_CORRELATION_RESPONSE_BYTES
        ):
            summaries.pop()
            partial = True
            break

    return ForgeEventCorrelationReadV1(
        correlation_id=correlation_id,
        environment=environment,
        tenant_ref=tenant_ref,
        shared_state="partial"
        if partial
        else ("available" if summaries else "missing"),
        events=summaries,
        observed_at=observed_at,
    )


@router.get(
    "/retention/shadow",
    response_model=TelemetryRetentionShadowReadV1,
)
def read_telemetry_retention_shadow(
    environment: str = Query(min_length=1, max_length=128),
    tenant_ref: str | None = Query(default=None, max_length=128),
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> TelemetryRetentionShadowReadV1:
    """Return bounded, read-only CP5 shadow decisions and aggregates."""

    if not telemetry_retention_shadow_read_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_retention_shadow_read_disabled"},
        )
    scopes = _authorize_retention_shadow_read(
        auth,
        environment=environment,
        tenant_ref=tenant_ref,
    )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )

    decision_query = (
        select(
            TelemetryRetentionDecisionV1Record,
            TelemetryDerivationReceiptV1Record,
        )
        .join(
            TelemetryDerivationReceiptV1Record,
            TelemetryRetentionDecisionV1Record.receipt_id
            == TelemetryDerivationReceiptV1Record.receipt_id,
        )
        .where(
            TelemetryRetentionDecisionV1Record.environment == environment,
            TelemetryRetentionDecisionV1Record.policy_mode == RETENTION_POLICY_MODE,
        )
        .order_by(
            TelemetryRetentionDecisionV1Record.window_end_at.desc(),
            TelemetryRetentionDecisionV1Record.decision_id,
        )
        .limit(MAX_RETENTION_SHADOW_ITEMS + 1)
    )
    aggregate_query = (
        select(
            TelemetryRoutineAggregateV1Record,
            TelemetryDerivationReceiptV1Record,
        )
        .join(
            TelemetryDerivationReceiptV1Record,
            TelemetryRoutineAggregateV1Record.receipt_id
            == TelemetryDerivationReceiptV1Record.receipt_id,
        )
        .where(
            TelemetryRoutineAggregateV1Record.environment == environment,
            TelemetryRoutineAggregateV1Record.policy_mode == RETENTION_POLICY_MODE,
        )
        .order_by(
            TelemetryRoutineAggregateV1Record.window_end_at.desc(),
            TelemetryRoutineAggregateV1Record.aggregate_id,
        )
        .limit(MAX_RETENTION_SHADOW_ITEMS + 1)
    )
    if tenant_ref is None:
        decision_query = decision_query.where(
            TelemetryRetentionDecisionV1Record.tenant_ref.is_(None)
        )
        aggregate_query = aggregate_query.where(
            TelemetryRoutineAggregateV1Record.tenant_ref.is_(None)
        )
    else:
        decision_query = decision_query.where(
            TelemetryRetentionDecisionV1Record.tenant_ref == tenant_ref
        )
        aggregate_query = aggregate_query.where(
            TelemetryRoutineAggregateV1Record.tenant_ref == tenant_ref
        )

    try:
        raw_decisions = list(db.execute(decision_query).all())
        raw_aggregates = list(db.execute(aggregate_query).all())
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    partial = (
        len(raw_decisions) > MAX_RETENTION_SHADOW_ITEMS
        or len(raw_aggregates) > MAX_RETENTION_SHADOW_ITEMS
    )
    raw_decisions = raw_decisions[:MAX_RETENTION_SHADOW_ITEMS]
    raw_aggregates = raw_aggregates[:MAX_RETENTION_SHADOW_ITEMS]
    can_read_restricted = "telemetry:read:retention:restricted" in scopes
    restricted_count = 0
    decisions: list[TelemetryRetentionDecisionReadItemV1] = []
    aggregates: list[TelemetryRoutineAggregateReadItemV1] = []
    observed_at = datetime.now(UTC)

    try:
        for record, receipt_record in raw_decisions:
            if (
                record.privacy_class in {"restricted", "confidential"}
                and not can_read_restricted
            ):
                restricted_count += 1
                continue
            receipt = TelemetryDerivationReceiptV1.model_validate(
                receipt_record.payload
            )
            decisions.append(
                TelemetryRetentionDecisionReadItemV1(
                    decision_id=record.decision_id,
                    source_kind=record.source_kind,
                    source_ref=record.source_ref,
                    source_sha256=record.source_sha256,
                    source_received_at=record.source_received_at,
                    service_or_check=record.service_or_check,
                    environment=record.environment,
                    tenant_ref=record.tenant_ref,
                    privacy_class=record.privacy_class,
                    retention_class=record.retention_class,
                    legal_class=record.legal_class,
                    action=record.action,
                    reason_code=record.reason_code,
                    projected_delete_at=record.projected_delete_at,
                    applied=record.applied,
                    source_overwritten=record.source_overwritten,
                    receipt=receipt,
                )
            )
            size_probe = _retention_shadow_response(
                environment=environment,
                tenant_ref=tenant_ref,
                decisions=decisions,
                aggregates=aggregates,
                observed_at=observed_at,
                shared_state="partial",
            )
            if len(size_probe.model_dump_json().encode()) > (
                MAX_RETENTION_SHADOW_RESPONSE_BYTES
            ):
                decisions.pop()
                partial = True
                break

        remaining = MAX_RETENTION_SHADOW_ITEMS - len(decisions)
        if len(raw_aggregates) > remaining:
            partial = True
        for record, receipt_record in raw_aggregates[:remaining]:
            if (
                record.privacy_class in {"restricted", "confidential"}
                and not can_read_restricted
            ):
                restricted_count += 1
                continue
            receipt = TelemetryDerivationReceiptV1.model_validate(
                receipt_record.payload
            )
            aggregate = TelemetryRoutineAggregatePayloadV1.model_validate(
                record.payload
            )
            aggregates.append(
                TelemetryRoutineAggregateReadItemV1(
                    aggregate=aggregate,
                    receipt=receipt,
                )
            )
            size_probe = _retention_shadow_response(
                environment=environment,
                tenant_ref=tenant_ref,
                decisions=decisions,
                aggregates=aggregates,
                observed_at=observed_at,
                shared_state="partial",
            )
            if len(size_probe.model_dump_json().encode()) > (
                MAX_RETENTION_SHADOW_RESPONSE_BYTES
            ):
                aggregates.pop()
                partial = True
                break
    except (TypeError, ValueError) as exc:
        logger.error(
            "CP5 telemetry retention projection rejected stored evidence",
            extra={"environment": environment, "tenant_ref": tenant_ref},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_retention_evidence_invalid"},
        ) from exc

    if restricted_count:
        partial = bool(decisions or aggregates) or partial
    if decisions or aggregates:
        shared_state = "partial" if partial else "available"
    elif restricted_count:
        shared_state = "restricted"
    else:
        shared_state = "missing"
    return _retention_shadow_response(
        environment=environment,
        tenant_ref=tenant_ref,
        decisions=decisions,
        aggregates=aggregates,
        observed_at=observed_at,
        shared_state=shared_state,
    )


def _retention_shadow_response(
    *,
    environment: str,
    tenant_ref: str | None,
    decisions: list[TelemetryRetentionDecisionReadItemV1],
    aggregates: list[TelemetryRoutineAggregateReadItemV1],
    observed_at: datetime,
    shared_state: str,
) -> TelemetryRetentionShadowReadV1:
    return TelemetryRetentionShadowReadV1(
        environment=environment,
        tenant_ref=tenant_ref,
        policy_id=RETENTION_POLICY_ID,
        policy_version=RETENTION_POLICY_VERSION,
        policy_sha256=RETENTION_POLICY_SHA256,
        policy_mode=RETENTION_POLICY_MODE,
        clock_basis=RETENTION_CLOCK_BASIS,
        deletion_enabled=False,
        shared_state=shared_state,
        decisions=decisions,
        aggregates=aggregates,
        observed_at=observed_at,
    )


@router.post(
    "/incidents/candidates",
    response_model=IncidentCandidateIngestResponseV1,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def ingest_incident_candidate(
    submission: IncidentCandidateSubmissionV1,
    response: Response,
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> IncidentCandidateIngestResponseV1:
    """Persist one source-proved candidate without granting action authority."""

    if not incident_candidate_write_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "incident_candidate_write_disabled"},
        )
    _authorize_incident_candidate_write(auth, submission)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    digest = incident_candidate_payload_digest(submission.candidate)
    try:
        verify_incident_candidate_sources(db, submission.candidate)
        identity_outcome, record = _persist_incident_candidate(
            db,
            submission,
            digest,
        )
        db.commit()
        db.refresh(record)
    except IncidentCandidateSourceError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": str(exc)},
        ) from exc
    except IncidentCandidateIdentityConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc)},
        ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    if identity_outcome != "inserted":
        response.status_code = status.HTTP_200_OK
    return IncidentCandidateIngestResponseV1(
        candidate_id=record.candidate_id,
        candidate_digest=record.payload_digest,
        fingerprint_sha256=record.fingerprint_sha256,
        received_at=record.received_at,
        identity_outcome=identity_outcome,
    )


@router.get(
    "/incidents/candidates",
    response_model=IncidentCandidateReadV1,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def read_incident_candidates(
    environment: str = Query(pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    tenant_ref: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    limit: int = Query(default=25, ge=1, le=MAX_INCIDENT_CANDIDATE_ITEMS),
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> IncidentCandidateReadV1:
    """Return a bounded, read-only candidate projection to Forge_Command."""

    if not incident_candidate_read_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "incident_candidate_read_disabled"},
        )
    scopes = _authorize_incident_candidate_read(
        auth,
        environment=environment,
        tenant_ref=tenant_ref,
    )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )

    statement = (
        select(IncidentCandidateV1Record)
        .where(IncidentCandidateV1Record.environment == environment)
        .order_by(
            IncidentCandidateV1Record.created_at.desc(),
            IncidentCandidateV1Record.candidate_id,
        )
        .limit(limit + 1)
    )
    if tenant_ref is None:
        statement = statement.where(IncidentCandidateV1Record.tenant_ref.is_(None))
    else:
        statement = statement.where(
            IncidentCandidateV1Record.tenant_ref == tenant_ref
        )
    try:
        records = list(db.execute(statement).scalars())
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    partial = len(records) > limit
    restricted_count = 0
    can_read_restricted = (
        "telemetry:read:incident-candidates:restricted" in scopes
    )
    candidates: list[IncidentCandidateReadItemV1] = []
    observed_at = datetime.now(UTC)
    try:
        for record in records[:limit]:
            if (
                record.privacy_class in {"restricted", "confidential"}
                and not can_read_restricted
            ):
                restricted_count += 1
                continue
            candidate = IncidentCandidateV1.model_validate(record.payload)
            digest = incident_candidate_payload_digest(candidate)
            if (
                digest != record.payload_digest
                or candidate.candidate_id != record.candidate_id
                or candidate.environment != environment
                or candidate.tenant_ref != tenant_ref
                or candidate.deduplication.fingerprint_version
                != record.fingerprint_version
                or candidate.deduplication.fingerprint_sha256
                != record.fingerprint_sha256
                or candidate.analysis_provenance.analysis_kind
                != record.analysis_kind
                or candidate.analysis_provenance.producer_service
                != record.producer_service
                or candidate.analysis_provenance.producer_version
                != record.producer_version
                or candidate.analysis_provenance.provider != record.provider
                or candidate.analysis_provenance.model != record.model
                or candidate.analysis_provenance.prompt_sha256
                != record.prompt_sha256
                or candidate.analysis_provenance.model_response_sha256
                != record.model_response_sha256
                or candidate.analysis_provenance.run_receipt_ref
                != record.run_receipt_ref
                or record.candidate_only is not True
                or record.can_repair is not False
                or record.can_rollback is not False
                or record.can_notify is not False
                or record.can_promote is not False
                or record.requires_human_decision is not True
                or record.source_overwritten is not False
                or candidate.authority.candidate_only is not True
                or candidate.authority.can_repair is not False
                or candidate.authority.can_rollback is not False
                or candidate.authority.can_notify is not False
                or candidate.authority.can_promote is not False
                or candidate.authority.requires_human_decision is not True
                or candidate.authority.source_overwritten is not False
            ):
                raise ValueError("stored incident candidate mismatch")
            candidates.append(
                IncidentCandidateReadItemV1(
                    candidate=candidate,
                    candidate_digest=digest,
                    received_at=record.received_at,
                )
            )
            size_probe = IncidentCandidateReadV1(
                environment=environment,
                tenant_ref=tenant_ref,
                shared_state="partial",
                candidates=candidates,
                observed_at=observed_at,
            )
            if len(size_probe.model_dump_json().encode()) > (
                MAX_INCIDENT_CANDIDATE_RESPONSE_BYTES
            ):
                candidates.pop()
                partial = True
                break
    except (TypeError, ValueError) as exc:
        logger.error(
            "CP6 incident candidate projection rejected stored evidence",
            extra={"environment": environment, "tenant_ref": tenant_ref},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "incident_candidate_evidence_invalid"},
        ) from exc

    if restricted_count:
        partial = bool(candidates) or partial
    if candidates:
        shared_state = "partial" if partial else "available"
    elif restricted_count:
        shared_state = "restricted"
    else:
        shared_state = "missing"
    return IncidentCandidateReadV1(
        environment=environment,
        tenant_ref=tenant_ref,
        shared_state=shared_state,
        candidates=candidates,
        observed_at=observed_at,
    )


@router.post(
    "/events",
    response_model=ForgeEventV1IngestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def ingest_forge_event_v1(
    event: ForgeEventV1Submission,
    response: Response,
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeEventV1IngestResponse:
    """Persist one canonical event without aliases, fallback, or dual-write."""

    if not forge_event_v1_write_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_disabled"},
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    _authorize_event(auth, event)
    digest = event_digest(event)

    try:
        identity_outcome = _persist_event(db, event, digest)
        record = db.execute(
            select(ForgeEventV1Record).where(
                ForgeEventV1Record.event_id == event.event_id
            )
        ).scalar_one()
        db.commit()
    except EventIdentityConflict as exc:
        db.rollback()
        logger.warning(
            "Canonical Forge telemetry event identity conflict",
            extra={"event_id": str(event.event_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "event_identity_conflict",
                "event_id": str(event.event_id),
            },
        ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        logger.error(
            "Canonical Forge telemetry persistence failed",
            extra={"event_id": str(event.event_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    if identity_outcome == "exact_replay":
        response.status_code = status.HTTP_200_OK
    logger.info(
        "Canonical Forge telemetry event persisted",
        extra={
            "event_id": str(event.event_id),
            "identity_outcome": identity_outcome,
            "key_id": auth.key_id,
        },
    )
    return ForgeEventV1IngestResponse(
        event_id=event.event_id,
        event_digest=digest,
        received_at=record.received_at,
        identity_outcome=identity_outcome,
    )

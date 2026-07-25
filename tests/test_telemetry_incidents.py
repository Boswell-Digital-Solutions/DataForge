from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Response
from forge_telemetry import validate_incident_candidate_v1

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    ingest_incident_candidate,
    read_incident_candidates,
)
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeEventV1Record,
    IncidentCandidateV1Record,
)
from app.models.telemetry_schemas import IncidentCandidateSubmissionV1
from app.telemetry_incidents import build_deterministic_incident_candidate


WINDOW_START = datetime(2026, 7, 25, 12, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 25, 13, tzinfo=UTC)
CREATED_AT = WINDOW_END + timedelta(minutes=1)
CORRELATION_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


@pytest.fixture(autouse=True)
def enable_incident_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAFORGE_INCIDENT_CANDIDATE_WRITE_ENABLED", "true")
    monkeypatch.setenv("DATAFORGE_INCIDENT_CANDIDATE_READ_ENABLED", "true")


def _auth(
    *,
    service_name: str,
    scopes: list[str],
    environment: str = "test",
    tenant_ref: str | None = None,
) -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id=f"cp6-{service_name}",
            key_prefix="cp6-proof",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": service_name,
                "environment": environment,
                "tenant_ref": tenant_ref,
                "scopes": scopes,
            },
        ),
    )


def _writer(
    *,
    service_name: str = "dataforge",
    scopes: list[str] | None = None,
    environment: str = "test",
    tenant_ref: str | None = None,
) -> AuthContext:
    return _auth(
        service_name=service_name,
        scopes=scopes or ["telemetry:write:incident-candidates"],
        environment=environment,
        tenant_ref=tenant_ref,
    )


def _reader(
    *,
    scopes: list[str] | None = None,
    service_name: str = "forge_command",
    environment: str = "test",
    tenant_ref: str | None = None,
) -> AuthContext:
    return _auth(
        service_name=service_name,
        scopes=scopes or ["telemetry:read:incident-candidates"],
        environment=environment,
        tenant_ref=tenant_ref,
    )


def _check(
    *,
    result_id: UUID | None = None,
    privacy_class: str = "internal",
    tenant_ref: str | None = None,
) -> ForgeCheckResultV1Record:
    result_id = result_id or uuid4()
    started_at = WINDOW_START + timedelta(minutes=9)
    received_at = WINDOW_START + timedelta(minutes=10)
    return ForgeCheckResultV1Record(
        result_id=result_id,
        payload_digest=hashlib.sha256(str(result_id).encode()).hexdigest(),
        payload={"schema_version": "ForgeCheckResult.v1"},
        run_id=uuid4(),
        check_id="bds.dataforge.cp6.failure.debug",
        check_revision=1,
        definition_sha256="1" * 64,
        environment="test",
        tenant_ref=tenant_ref,
        evaluation_mode="debug",
        status="failed",
        reason_code="assertion_failed",
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=1),
        duration_ms=1000,
        assertion_passed=False,
        slo_included=False,
        uptime_included=False,
        baseline_included=False,
        cost_units_observed=1,
        privacy_class=privacy_class,
        correlation_id=CORRELATION_ID,
        trace_id=TRACE_ID,
        received_at=received_at,
    )


def _event(
    *,
    event_id: UUID | None = None,
    privacy_class: str = "internal",
    tenant_ref: str | None = None,
) -> ForgeEventV1Record:
    event_id = event_id or uuid4()
    received_at = WINDOW_START + timedelta(minutes=5)
    return ForgeEventV1Record(
        event_id=event_id,
        event_digest=hashlib.sha256(str(event_id).encode()).hexdigest(),
        schema_version="ForgeEvent.v1",
        occurred_at=received_at - timedelta(seconds=1),
        received_at=received_at,
        service_name="dataforge",
        service_instance_id="dataforge-test-1",
        environment="test",
        tenant_ref=tenant_ref,
        event_type="telemetry.cp6.correlated_failure",
        severity="error",
        outcome="fail",
        evidence_class="operational",
        correlation_id=CORRELATION_ID,
        trace_id=TRACE_ID,
        span_id="00f067aa0ba902b7",
        parent_span_id=None,
        attributes={},
        metrics={},
        privacy_class=privacy_class,
        retention_class="long",
        sampled=True,
        sample_rate=None,
        sampling_reason="always_on",
    )


def _candidate(db, *, privacy_class: str = "internal"):
    check = _check(privacy_class=privacy_class)
    event = _event(privacy_class=privacy_class)
    db.add_all([check, event])
    db.commit()
    return build_deterministic_incident_candidate(
        check,
        [event],
        window_start_at=WINDOW_START,
        window_end_at=WINDOW_END,
        created_at=CREATED_AT,
    )


def _submission(candidate) -> IncidentCandidateSubmissionV1:
    return IncidentCandidateSubmissionV1(
        schema_version="forge.dataforge.incident-candidate.v1",
        environment="test",
        tenant_ref=None,
        candidate=candidate,
    )


def test_builder_exposes_evidence_uncertainty_and_no_action_authority(db) -> None:
    candidate = _candidate(db)

    assert candidate.suspected_cause.cause_code == "correlated_service_failure"
    assert len(candidate.alternatives) == 2
    assert candidate.confidence.score_basis_points == 7200
    assert candidate.uncertainty.state == "partial"
    assert set(candidate.missing_evidence) == {
        "baseline_deviation_evidence",
        "configuration_change_evidence",
        "deployment_change_evidence",
    }
    assert candidate.analysis_provenance.analysis_kind == "deterministic_rules"
    assert candidate.analysis_provenance.producer_service == "dataforge"
    assert candidate.analysis_provenance.provider is None
    assert candidate.analysis_provenance.model is None
    assert candidate.analysis_provenance.prompt_sha256 is None
    assert candidate.analysis_provenance.model_response_sha256 is None
    assert candidate.analysis_provenance.run_receipt_ref is None
    assert candidate.authority.classification == "derived_candidate"
    assert candidate.authority.candidate_only is True
    assert candidate.authority.can_repair is False
    assert candidate.authority.can_rollback is False
    assert candidate.authority.can_notify is False
    assert candidate.authority.can_promote is False
    assert candidate.authority.requires_human_decision is True
    assert candidate.authority.source_overwritten is False


def test_ingest_is_source_proved_idempotent_and_fingerprint_deduplicated(db) -> None:
    candidate = _candidate(db)
    submission = _submission(candidate)

    inserted = ingest_incident_candidate(
        submission,
        Response(),
        db,
        _writer(),
    )
    replay_response = Response()
    replay = ingest_incident_candidate(
        submission,
        replay_response,
        db,
        _writer(),
    )

    second_payload = candidate.model_dump(mode="json")
    second_payload["candidate_id"] = str(uuid4())
    second_candidate = validate_incident_candidate_v1(second_payload)
    dedup_response = Response()
    deduplicated = ingest_incident_candidate(
        _submission(second_candidate),
        dedup_response,
        db,
        _writer(),
    )

    assert inserted.identity_outcome == "inserted"
    assert replay.identity_outcome == "exact_replay"
    assert replay_response.status_code == 200
    assert deduplicated.identity_outcome == "deduplicated"
    assert dedup_response.status_code == 200
    assert deduplicated.candidate_id == candidate.candidate_id
    assert db.query(IncidentCandidateV1Record).count() == 1


def test_ingest_rejects_changed_or_unverifiable_source_evidence(db) -> None:
    candidate = _candidate(db)
    event = db.query(ForgeEventV1Record).one()
    event.event_digest = "f" * 64
    db.commit()

    with pytest.raises(HTTPException) as error:
        ingest_incident_candidate(
            _submission(candidate),
            Response(),
            db,
            _writer(),
        )

    assert error.value.status_code == 422
    assert error.value.detail == {"code": "incident_candidate_source_mismatch"}
    assert db.query(IncidentCandidateV1Record).count() == 0


@pytest.mark.parametrize(
    ("auth", "code"),
    (
        (
            _writer(scopes=["telemetry:write"]),
            "incident_candidate_write_scope_required",
        ),
        (
            _writer(service_name="other"),
            "telemetry_subject_binding_mismatch",
        ),
        (
            _writer(environment="production"),
            "telemetry_subject_binding_mismatch",
        ),
    ),
)
def test_ingest_requires_exact_producer_scope_binding(db, auth, code) -> None:
    candidate = _candidate(db)

    with pytest.raises(HTTPException) as error:
        ingest_incident_candidate(
            _submission(candidate),
            Response(),
            db,
            auth,
        )

    assert error.value.status_code == 403
    assert error.value.detail == {"code": code}


def test_read_is_scope_bound_and_redacts_restricted_candidates(db) -> None:
    candidate = _candidate(db, privacy_class="restricted")
    ingest_incident_candidate(
        _submission(candidate),
        Response(),
        db,
        _writer(),
    )

    hidden = read_incident_candidates("test", None, 25, db, _reader())
    visible = read_incident_candidates(
        "test",
        None,
        25,
        db,
        _reader(
            scopes=[
                "telemetry:read:incident-candidates",
                "telemetry:read:incident-candidates:restricted",
            ]
        ),
    )

    assert hidden.shared_state == "restricted"
    assert hidden.candidate_only is True
    assert hidden.actions_enabled is False
    assert hidden.candidates == []
    assert visible.shared_state == "available"
    assert len(visible.candidates) == 1
    assert visible.candidates[0].candidate.authority.candidate_only is True


def test_read_rejects_corrupt_action_columns(db) -> None:
    candidate = _candidate(db)
    ingest_incident_candidate(
        _submission(candidate),
        Response(),
        db,
        _writer(),
    )
    record = db.query(IncidentCandidateV1Record).one()
    record.can_repair = True
    db.commit()

    with pytest.raises(HTTPException) as error:
        read_incident_candidates("test", None, 25, db, _reader())

    assert error.value.status_code == 503
    assert error.value.detail == {"code": "incident_candidate_evidence_invalid"}


def test_kill_switches_and_route_methods_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    db,
) -> None:
    candidate = _candidate(db)
    monkeypatch.setenv("DATAFORGE_INCIDENT_CANDIDATE_WRITE_ENABLED", "false")
    with pytest.raises(HTTPException) as write_error:
        ingest_incident_candidate(
            _submission(candidate),
            Response(),
            db,
            _writer(),
        )
    assert write_error.value.status_code == 503
    assert write_error.value.detail == {
        "code": "incident_candidate_write_disabled"
    }

    monkeypatch.setenv("DATAFORGE_INCIDENT_CANDIDATE_READ_ENABLED", "false")
    with pytest.raises(HTTPException) as read_error:
        read_incident_candidates("test", None, 25, db, _reader())
    assert read_error.value.status_code == 503
    assert read_error.value.detail == {
        "code": "incident_candidate_read_disabled"
    }

    routes = [
        route
        for route in app.routes
        if route.path == "/api/v1/telemetry/incidents/candidates"
    ]
    assert {frozenset(route.methods) for route in routes} == {
        frozenset({"GET"}),
        frozenset({"POST"}),
    }

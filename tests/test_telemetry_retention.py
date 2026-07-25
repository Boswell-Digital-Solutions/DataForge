from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    MAX_RETENTION_SHADOW_ITEMS,
    read_telemetry_retention_shadow,
)
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeEventV1Record,
    TelemetryDerivationReceiptV1Record,
    TelemetryRetentionDecisionV1Record,
    TelemetryRoutineAggregateV1Record,
)
from app.telemetry_retention import (
    RETENTION_POLICY_PATH,
    RETENTION_POLICY_SHA256,
    run_shadow_retention,
)


WINDOW_START = datetime(2026, 7, 25, 12, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 25, 13, tzinfo=UTC)


@pytest.fixture(autouse=True)
def enable_shadow_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED",
        "true",
    )


def _reader(
    *,
    environment: str = "test",
    tenant_ref: str | None = None,
    scopes: list[str] | None = None,
    service_name: str = "forge_command",
) -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="cp5-reader",
            key_prefix="cp5-read",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": service_name,
                "environment": environment,
                "tenant_ref": tenant_ref,
                "scopes": scopes or ["telemetry:read:retention"],
            },
        ),
    )


def _event(
    *,
    event_id: UUID | None = None,
    received_at: datetime | None = None,
    outcome: str = "ok",
    severity: str = "info",
    evidence_class: str = "operational",
    privacy_class: str = "internal",
    retention_class: str = "short",
    environment: str = "test",
    tenant_ref: str | None = None,
    trace_id: str | None = None,
) -> ForgeEventV1Record:
    event_id = event_id or uuid4()
    received_at = received_at or (WINDOW_START + timedelta(minutes=5))
    return ForgeEventV1Record(
        event_id=event_id,
        event_digest=hashlib.sha256(str(event_id).encode()).hexdigest(),
        schema_version="ForgeEvent.v1",
        occurred_at=received_at - timedelta(seconds=1),
        received_at=received_at,
        service_name="dataforge",
        service_instance_id="dataforge-test-1",
        environment=environment,
        tenant_ref=tenant_ref,
        event_type="telemetry.cp5.proof",
        severity=severity,
        outcome=outcome,
        evidence_class=evidence_class,
        correlation_id=None,
        trace_id=trace_id,
        span_id="00f067aa0ba902b7" if trace_id else None,
        parent_span_id=None,
        attributes={},
        metrics={},
        privacy_class=privacy_class,
        retention_class=retention_class,
        sampled=True,
        sample_rate=None,
        sampling_reason="always_on",
    )


def _slow_check() -> ForgeCheckResultV1Record:
    result_id = uuid4()
    started_at = WINDOW_START + timedelta(minutes=10)
    return ForgeCheckResultV1Record(
        result_id=result_id,
        payload_digest=hashlib.sha256(str(result_id).encode()).hexdigest(),
        payload={"schema_version": "ForgeCheckResult.v1"},
        run_id=uuid4(),
        check_id="bds.dataforge.cp5.slow.debug",
        check_revision=1,
        definition_sha256="1" * 64,
        environment="test",
        tenant_ref=None,
        evaluation_mode="debug",
        status="passed",
        reason_code="assertion_passed",
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=2500),
        duration_ms=2500,
        assertion_passed=True,
        slo_included=False,
        uptime_included=False,
        baseline_included=False,
        cost_units_observed=1,
        privacy_class="internal",
        correlation_id=None,
        trace_id=None,
        received_at=started_at + timedelta(seconds=3),
    )


def _run(db, source_limit: int = 500):
    return run_shadow_retention(
        db,
        window_start_at=WINDOW_START,
        window_end_at=WINDOW_END,
        environment="test",
        tenant_ref=None,
        source_limit=source_limit,
    )


def test_policy_is_digest_bound_and_shadow_only() -> None:
    assert hashlib.sha256(RETENTION_POLICY_PATH.read_bytes()).hexdigest() == (
        RETENTION_POLICY_SHA256
    )


def test_shadow_run_classifies_every_source_and_never_rewrites_it(db) -> None:
    routine = _event()
    failed = _event(outcome="fail", severity="error")
    legal = _event(retention_class="legal_hold")
    governed = _event(privacy_class="restricted", evidence_class="audit")
    sampled_trace = _event(trace_id="4bf92f3577b34da6a3ce929d0e0e4736")
    slow = _slow_check()
    db.add_all([routine, failed, legal, governed, sampled_trace, slow])
    db.commit()
    source_snapshot = {
        str(record.event_id): (
            record.event_digest,
            record.received_at,
            record.retention_class,
        )
        for record in db.query(ForgeEventV1Record).all()
    }

    result = _run(db)

    assert result.source_count == 6
    assert result.decision_count == 6
    assert result.aggregate_count == 1
    assert result.deletion_count == 0
    assert result.source_update_count == 0
    decisions = db.query(TelemetryRetentionDecisionV1Record).all()
    assert {item.reason_code for item in decisions} == {
        "routine_success_short",
        "failure_long",
        "legal_hold",
        "governed_evidence_long",
        "slow_check_long",
        "sampled_normal_trace_short",
    }
    assert all(item.applied is False for item in decisions)
    assert all(item.source_overwritten is False for item in decisions)
    assert (
        next(
            item for item in decisions if item.reason_code == "legal_hold"
        ).projected_delete_at
        is None
    )
    assert source_snapshot == {
        str(record.event_id): (
            record.event_digest,
            record.received_at,
            record.retention_class,
        )
        for record in db.query(ForgeEventV1Record).all()
    }
    assert db.get(ForgeCheckResultV1Record, slow.result_id).duration_ms == 2500

    receipts = db.query(TelemetryDerivationReceiptV1Record).all()
    # Six source-decision receipts plus the routine aggregate receipt.
    assert len(receipts) == 7
    assert all(item.policy_mode == "shadow" for item in receipts)
    assert all(item.clock_basis == "received_at" for item in receipts)
    assert all(item.decision_applied is False for item in receipts)
    assert all(item.source_overwritten is False for item in receipts)


def test_shadow_replay_is_idempotent_and_oversized_window_fails_closed(db) -> None:
    db.add_all([_event() for _ in range(3)])
    db.commit()

    with pytest.raises(
        ValueError,
        match="retention_window_source_limit_exceeded",
    ):
        _run(db, source_limit=2)
    assert db.query(TelemetryRetentionDecisionV1Record).count() == 0

    first = _run(db, source_limit=3)
    counts = (
        db.query(TelemetryRetentionDecisionV1Record).count(),
        db.query(TelemetryRoutineAggregateV1Record).count(),
        db.query(TelemetryDerivationReceiptV1Record).count(),
    )
    second = _run(db, source_limit=3)

    assert first.partial is False
    assert second.partial is False
    assert counts == (
        db.query(TelemetryRetentionDecisionV1Record).count(),
        db.query(TelemetryRoutineAggregateV1Record).count(),
        db.query(TelemetryDerivationReceiptV1Record).count(),
    )


def test_shadow_read_is_scope_bound_and_redacts_classified_records(db) -> None:
    db.add(_event(privacy_class="confidential", evidence_class="audit"))
    db.commit()
    _run(db)

    hidden = read_telemetry_retention_shadow(
        "test",
        None,
        db,
        _reader(),
    )
    assert hidden.shared_state == "restricted"
    assert hidden.decisions == []
    assert hidden.aggregates == []
    assert hidden.deletion_enabled is False
    assert hidden.clock_basis == "received_at"

    visible = read_telemetry_retention_shadow(
        "test",
        None,
        db,
        _reader(
            scopes=[
                "telemetry:read:retention",
                "telemetry:read:retention:restricted",
            ]
        ),
    )
    assert visible.shared_state == "available"
    assert len(visible.decisions) == 1
    assert visible.decisions[0].receipt.policy.mode == "shadow"
    assert visible.decisions[0].applied is False


@pytest.mark.parametrize(
    ("auth", "code"),
    (
        (
            _reader(scopes=["telemetry:read"]),
            "telemetry_retention_read_scope_required",
        ),
        (
            _reader(service_name="other"),
            "telemetry_subject_binding_mismatch",
        ),
        (
            _reader(environment="production"),
            "telemetry_subject_binding_mismatch",
        ),
        (
            _reader(tenant_ref="other"),
            "telemetry_subject_binding_mismatch",
        ),
    ),
)
def test_shadow_read_requires_exact_reader_binding(db, auth, code) -> None:
    with pytest.raises(HTTPException) as error:
        read_telemetry_retention_shadow("test", None, db, auth)
    assert error.value.status_code == 403
    assert error.value.detail == {"code": code}


def test_shadow_read_kill_switch_and_route_methods_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    db,
) -> None:
    monkeypatch.setenv(
        "DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED",
        "false",
    )
    with pytest.raises(HTTPException) as error:
        read_telemetry_retention_shadow("test", None, db, _reader())
    assert error.value.status_code == 503
    assert error.value.detail == {"code": "telemetry_retention_shadow_read_disabled"}

    retention_routes = [
        route
        for route in app.routes
        if route.path.startswith("/api/v1/telemetry/retention")
    ]
    assert len(retention_routes) == 1
    assert retention_routes[0].methods == {"GET"}


def test_shadow_projection_has_finite_item_bound(db) -> None:
    db.add_all([_event() for _ in range(MAX_RETENTION_SHADOW_ITEMS + 2)])
    db.commit()
    _run(db)

    response = read_telemetry_retention_shadow(
        "test",
        None,
        db,
        _reader(),
    )
    assert response.shared_state == "partial"
    assert len(response.decisions) + len(response.aggregates) <= (
        MAX_RETENTION_SHADOW_ITEMS
    )

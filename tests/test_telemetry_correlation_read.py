from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException, Response

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    MAX_CORRELATION_RESPONSE_BYTES,
    ingest_forge_event_v1,
    read_forge_event_correlation,
)
from app.auth import ApiKeyInfo
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import ForgeEventV1Submission


CORRELATION_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture(autouse=True)
def enable_correlation_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED", "true")


def _auth(
    *,
    environment: str = "development",
    tenant_ref: str | None = "bds-internal",
    scopes: list[str] | None = None,
    service_name: str = "forge_command",
) -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="cp3-reader",
            key_prefix="cp3-reader",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": service_name,
                "environment": environment,
                "tenant_ref": tenant_ref,
                "scopes": scopes if scopes is not None else ["telemetry:read"],
            },
        ),
    )


def _writer() -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="cp3-writer",
            key_prefix="cp3-writr",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": "forgesmithy",
                "environment": "development",
                "tenant_ref": "bds-internal",
                "scopes": ["telemetry:write"],
            },
        ),
    )


def _event(
    *,
    privacy_class: str = "internal",
    sampled: bool = True,
) -> ForgeEventV1Submission:
    return ForgeEventV1Submission.model_validate(
        {
            "schema_version": "ForgeEvent.v1",
            "event_id": "9cc52ee7-68d0-4683-a308-f8c327a54386",
            "occurred_at": "2026-07-24T14:30:00Z",
            "service_name": "forgesmithy",
            "service_instance_id": "forgesmithy-development-1",
            "environment": "development",
            "tenant_ref": "bds-internal",
            "event_type": "telemetry.correlation.proof",
            "severity": "info",
            "outcome": "ok",
            "evidence_class": "operational",
            "correlation_id": str(CORRELATION_ID),
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "00f067aa0ba902b7",
            "parent_span_id": None,
            "attributes": {"CANARY_SECRET": "must-never-cross-read-boundary"},
            "metrics": {},
            "privacy_class": privacy_class,
            "retention_class": "short",
            "sampled": sampled,
            "sample_rate": None,
            "sampling_reason": "always_on" if sampled else "required_stub",
        }
    )


def _persist(db, event: ForgeEventV1Submission) -> None:
    ingest_forge_event_v1(event, Response(), db, _writer())


def test_correlation_read_returns_minimal_scope_bound_projection(db) -> None:
    _persist(db, _event())
    response = read_forge_event_correlation(
        CORRELATION_ID,
        "development",
        "bds-internal",
        db,
        _auth(),
    )
    assert response.shared_state == "available"
    assert len(response.events) == 1
    assert response.events[0].detail_state == "available"
    assert response.events[0].trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    serialized = response.model_dump_json()
    assert "attributes" not in serialized
    assert "metrics" not in serialized
    assert "CANARY_SECRET" not in serialized


def test_missing_correlation_is_explicit(db) -> None:
    response = read_forge_event_correlation(
        CORRELATION_ID,
        "development",
        "bds-internal",
        db,
        _auth(),
    )
    assert response.shared_state == "missing"
    assert response.events == []


def test_correlation_read_kill_switch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    db,
) -> None:
    monkeypatch.setenv("DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED", "false")

    with pytest.raises(HTTPException) as error:
        read_forge_event_correlation(
            CORRELATION_ID,
            "development",
            "bds-internal",
            db,
            _auth(),
        )

    assert error.value.status_code == 503
    assert error.value.detail == {"code": "telemetry_correlation_disabled"}


@pytest.mark.parametrize(
    ("auth", "code"),
    [
        (_auth(scopes=["telemetry:write"]), "telemetry_read_scope_required"),
        (_auth(environment="production"), "telemetry_subject_binding_mismatch"),
        (_auth(tenant_ref="other"), "telemetry_subject_binding_mismatch"),
        (_auth(service_name="other"), "telemetry_subject_binding_mismatch"),
    ],
)
def test_read_requires_exact_reader_scope_binding(db, auth, code) -> None:
    with pytest.raises(HTTPException) as error:
        read_forge_event_correlation(
            CORRELATION_ID,
            "development",
            "bds-internal",
            db,
            auth,
        )
    assert error.value.status_code == 403
    assert error.value.detail == {"code": code}


def test_scope_collision_fails_closed_without_returning_events(db) -> None:
    _persist(db, _event())
    stored = db.query(ForgeEventV1Record).one()
    stored.environment = "production"
    db.commit()

    with pytest.raises(HTTPException) as error:
        read_forge_event_correlation(
            CORRELATION_ID,
            "development",
            "bds-internal",
            db,
            _auth(),
        )
    assert error.value.status_code == 409
    assert error.value.detail == {"code": "correlation_scope_conflict"}


def test_classified_trace_link_is_redacted_without_restricted_scope(db) -> None:
    _persist(db, _event(privacy_class="confidential"))
    response = read_forge_event_correlation(
        CORRELATION_ID,
        "development",
        "bds-internal",
        db,
        _auth(),
    )
    event = response.events[0]
    assert event.detail_state == "restricted"
    assert event.event_type is None
    assert event.trace_id is None
    assert event.span_id is None


def test_unsampled_event_reports_sampled_detail_state(db) -> None:
    _persist(db, _event(sampled=False))
    response = read_forge_event_correlation(
        CORRELATION_ID,
        "development",
        "bds-internal",
        db,
        _auth(),
    )
    assert response.events[0].detail_state == "sampled"


def test_correlation_projection_is_byte_bounded_and_reports_partial(db) -> None:
    for index in range(6):
        event = _event().model_copy(
            update={
                "event_id": UUID(int=index + 1),
                "event_type": f"e{'x' * 50_000}",
            }
        )
        _persist(db, event)

    response = read_forge_event_correlation(
        CORRELATION_ID,
        "development",
        "bds-internal",
        db,
        _auth(),
    )

    assert response.shared_state == "partial"
    assert 0 < len(response.events) < 6
    assert len(response.model_dump_json().encode("utf-8")) <= (
        MAX_CORRELATION_RESPONSE_BYTES
    )

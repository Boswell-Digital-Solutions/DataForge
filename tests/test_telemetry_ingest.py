"""Regression coverage for the Forge Telemetry HTTP ingress."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import ingest_telemetry_events
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import TelemetryEventRecord
from app.models.telemetry_schemas import TelemetryIngestBatch


def _auth(*, service: str = "forgesmithy", scopes: list[str] | None = None) -> AuthContext:
    metadata: dict[str, object] = {"service": service}
    if scopes is not None:
        metadata["scopes"] = scopes
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="test-key",
            key_prefix="test-prefx",
            created_at=datetime.now(UTC).isoformat(),
            metadata=metadata,
        ),
    )


def _event(event_id: str | None = None) -> dict:
    return {
        "event_id": event_id or str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "ForgeSmithy",
        "event_type": "session_start",
        "severity": "info",
        "correlation_id": str(uuid4()),
        "metadata": {"session_id": "session-1", "agent_type": "reviewer"},
        "metrics": None,
    }


def _batch(event: dict) -> TelemetryIngestBatch:
    return TelemetryIngestBatch.model_validate({"events": [event]})


def test_telemetry_ingest_route_is_mounted():
    assert "/api/v1/telemetry/events:batch" in {
        route.path for route in app.routes
    }


def test_ingest_persists_v03_event_and_normalizes_service(db):
    event = _event()
    response = ingest_telemetry_events(_batch(event), db, _auth())

    assert response.model_dump(mode="json", by_alias=True) == {
        "schemaVersion": "forge.telemetry.ingest.v1",
        "accepted": 1,
        "duplicates": 0,
        "eventIds": [event["event_id"]],
    }
    record = db.query(TelemetryEventRecord).one()
    assert record.service == "forgesmithy"
    assert record.event_type == "session_start"
    assert record.event_metadata["session_id"] == "session-1"


def test_ingest_is_idempotent_by_event_id(db):
    event = _event()
    first = ingest_telemetry_events(_batch(event), db, _auth())
    second = ingest_telemetry_events(_batch(event), db, _auth())

    assert first.accepted == 1
    assert second.accepted == 0
    assert second.duplicates == 1
    assert db.query(TelemetryEventRecord).count() == 1


def test_ingest_rejects_service_outside_key_binding(db):
    with pytest.raises(HTTPException) as error:
        ingest_telemetry_events(_batch(_event()), db, _auth(service="authorforge"))

    assert error.value.status_code == 403


def test_generic_ingest_never_accepts_authorforge(db):
    event = _event()
    event["service"] = "AuthorForge"
    event["metadata"] = {"manuscript": "must-remain-local"}

    with pytest.raises(HTTPException) as error:
        ingest_telemetry_events(
            _batch(event),
            db,
            _auth(service="authorforge", scopes=["telemetry:write"]),
        )

    assert error.value.status_code == 403
    assert db.query(TelemetryEventRecord).count() == 0


def test_ingest_rejects_key_without_declared_write_scope(db):
    with pytest.raises(HTTPException) as error:
        ingest_telemetry_events(
            _batch(_event()),
            db,
            _auth(scopes=["telemetry:read"]),
        )

    assert error.value.status_code == 403


def test_ingest_rejects_oversized_or_invalid_payloads():
    oversized = _event()
    oversized["metadata"] = {"detail": "x" * 9000}
    with pytest.raises(ValidationError):
        _batch(oversized)

    invalid_type = _event()
    invalid_type["event_type"] = "invalid event type"
    with pytest.raises(ValidationError):
        _batch(invalid_type)

"""Regression coverage for the Forge Telemetry HTTP ingress."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import rfc8785
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import ingest_telemetry_events
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import TelemetryEventRecord
from app.models.telemetry_schemas import (
    MAX_CANONICAL_EVENT_BYTES,
    TelemetryIngestBatch,
    TelemetryIngestEvent,
)


def _auth(
    *, service: str = "forgesmithy", scopes: list[str] | None = None
) -> AuthContext:
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


def _event_with_canonical_size(target_bytes: int) -> dict:
    event = _event("00000000-0000-0000-0000-000000000001")
    event["timestamp"] = "2026-07-23T00:00:00Z"
    event["service"] = "forgesmithy"
    event["event_type"] = "boundary"
    event["correlation_id"] = None
    event["metadata"] = {f"chunk_{index}": "x" * 8192 for index in range(7)}
    event["metadata"]["tail"] = ""
    remaining = target_bytes - len(rfc8785.dumps(event))
    assert 0 <= remaining <= 8192
    event["metadata"]["tail"] = "x" * remaining
    assert len(rfc8785.dumps(event)) == target_bytes
    return event


def test_telemetry_ingest_route_is_mounted():
    assert "/api/v1/telemetry/events:batch" in {route.path for route in app.routes}


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


def test_ingest_enforces_64_kib_across_the_complete_canonical_event():
    accepted = _event_with_canonical_size(MAX_CANONICAL_EVENT_BYTES)
    assert (
        len(
            rfc8785.dumps(
                TelemetryIngestEvent.model_validate(accepted).model_dump(mode="json")
            )
        )
        == MAX_CANONICAL_EVENT_BYTES
    )

    rejected = _event_with_canonical_size(MAX_CANONICAL_EVENT_BYTES + 1)
    with pytest.raises(
        ValidationError,
        match="telemetry event exceeds 65536 canonical bytes",
    ):
        TelemetryIngestEvent.model_validate(rejected)


def test_ingest_does_not_treat_metadata_and_metrics_as_separate_64_kib_budgets():
    event = _event()
    event["metadata"] = {f"metadata_{index}": "m" * 7000 for index in range(5)}
    event["metrics"] = {f"metric_{index}": "n" * 7000 for index in range(5)}

    assert len(rfc8785.dumps(event["metadata"])) < MAX_CANONICAL_EVENT_BYTES
    assert len(rfc8785.dumps(event["metrics"])) < MAX_CANONICAL_EVENT_BYTES
    with pytest.raises(
        ValidationError,
        match="telemetry event exceeds 65536 canonical bytes",
    ):
        TelemetryIngestEvent.model_validate(event)

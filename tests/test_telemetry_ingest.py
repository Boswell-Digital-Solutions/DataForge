"""Regression coverage for the canonical ForgeEvent.v1 HTTP ingress."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import rfc8785
from fastapi import HTTPException, Response
from pydantic import ValidationError

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    get_forge_event_v1_capability,
    ingest_forge_event_v1,
)
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import (
    CONTRACT_AUTHORITY_COMMIT,
    EVENT_SIZE_VIOLATION_CODE,
    FORGE_EVENT_V1_SCHEMA_SHA256,
    MAX_CANONICAL_EVENT_BYTES,
    SINK_CAPABILITY_FIXTURE_SHA256,
    ForgeEventV1Submission,
    event_digest,
)


CAPABILITY_PATH = (
    Path(__file__).parent.parent
    / "app"
    / "models"
    / "contracts"
    / "forge_telemetry_sink_capability.v1.json"
)


def _auth(
    *,
    service_name: str = "forgesmithy",
    environment: str = "staging",
    tenant_ref: str | None = None,
    scopes: list[str] | None = None,
) -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="test-key",
            key_prefix="test-prefx",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": service_name,
                "environment": environment,
                "tenant_ref": tenant_ref,
                "scopes": scopes if scopes is not None else ["telemetry:write"],
            },
        ),
    )


def _event(event_id: str | None = None) -> dict:
    return {
        "schema_version": "ForgeEvent.v1",
        "event_id": event_id or str(uuid4()),
        "occurred_at": "2026-07-23T18:00:00Z",
        "service_name": "forgesmithy",
        "service_instance_id": "forgesmithy-staging-1",
        "environment": "staging",
        "tenant_ref": None,
        "event_type": "session.started",
        "severity": "info",
        "outcome": "ok",
        "evidence_class": "operational",
        "correlation_id": str(uuid4()),
        "trace_id": "0123456789abcdef0123456789abcdef",
        "span_id": "0123456789abcdef",
        "parent_span_id": None,
        "attributes": {"session_id": "session-1", "agent_type": "reviewer"},
        "metrics": {"duration_ms": 12},
        "privacy_class": "internal",
        "retention_class": "standard",
        "sampled": True,
        "sample_rate": None,
        "sampling_reason": "always_on",
    }


def _submission(payload: dict | None = None) -> ForgeEventV1Submission:
    return ForgeEventV1Submission.model_validate(payload or _event())


def _ingest(
    db,
    event: ForgeEventV1Submission,
    auth: AuthContext | None = None,
) -> tuple[object, Response]:
    response = Response()
    result = ingest_forge_event_v1(event, response, db, auth or _auth())
    return result, response


def _event_with_canonical_size(target_bytes: int) -> dict:
    event = _event("00000000-0000-4000-8000-000000000001")
    event["correlation_id"] = None
    event["trace_id"] = None
    event["span_id"] = None
    event["attributes"] = {"tail": ""}
    event["metrics"] = {}
    remaining = target_bytes - len(rfc8785.dumps(event))
    assert remaining >= 0
    event["attributes"]["tail"] = "x" * remaining
    assert len(rfc8785.dumps(event)) == target_bytes
    return event


def test_only_canonical_telemetry_routes_are_mounted():
    paths = {route.path for route in app.routes}
    assert "/api/v1/telemetry/capabilities/forge-event-v1" in paths
    assert "/api/v1/telemetry/events" in paths
    assert "/api/v1/telemetry/events:batch" not in paths


def test_capability_pins_admitted_contract_and_has_no_legacy_modes():
    assert CONTRACT_AUTHORITY_COMMIT == "236872abeeda52cc0f5e8834ebcceaa1a945fc47"
    assert hashlib.sha256(CAPABILITY_PATH.read_bytes()).hexdigest() == (
        SINK_CAPABILITY_FIXTURE_SHA256
    )
    capability = get_forge_event_v1_capability(_auth())
    assert capability.write_enabled is True
    assert capability.event_schema_sha256 == FORGE_EVENT_V1_SCHEMA_SHA256
    assert capability.max_canonical_event_bytes == 65536
    assert capability.pre_v1_fallback is False
    assert capability.dual_write is False
    assert len(capability.supported_fields) == 24


def test_ingest_persists_canonical_event_with_sink_time(db):
    event = _submission()
    result, response = _ingest(db, event)

    assert response.status_code == 200
    assert result.identity_outcome == "inserted"
    assert result.event_id == event.event_id
    assert result.event_digest == event_digest(event)

    record = db.query(ForgeEventV1Record).one()
    assert record.service_name == "forgesmithy"
    assert record.event_type == "session.started"
    assert record.received_at is not None
    assert record.event_digest == result.event_digest


def test_exact_replay_preserves_sink_time_and_content_identity(db):
    event = _submission()
    first, _ = _ingest(db, event)
    second, replay_response = _ingest(db, event)

    assert first.identity_outcome == "inserted"
    assert second.identity_outcome == "exact_replay"
    assert replay_response.status_code == 200
    assert second.received_at == first.received_at
    assert second.event_digest == first.event_digest
    assert db.query(ForgeEventV1Record).count() == 1


def test_same_event_id_with_different_content_is_a_conflict(db):
    payload = _event()
    _ingest(db, _submission(payload))
    payload["event_type"] = "session.failed"

    with pytest.raises(HTTPException) as error:
        _ingest(db, _submission(payload))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "event_identity_conflict"
    assert db.query(ForgeEventV1Record).count() == 1


@pytest.mark.parametrize(
    ("auth", "code"),
    [
        (_auth(service_name="authorforge"), "telemetry_subject_binding_mismatch"),
        (_auth(environment="production"), "telemetry_subject_binding_mismatch"),
        (_auth(tenant_ref="tenant-a"), "telemetry_subject_binding_mismatch"),
        (_auth(scopes=["telemetry:read"]), "telemetry_write_scope_required"),
    ],
)
def test_ingest_requires_exact_service_environment_tenant_and_scope_binding(
    db,
    auth,
    code,
):
    with pytest.raises(HTTPException) as error:
        _ingest(db, _submission(), auth)

    assert error.value.status_code == 403
    assert error.value.detail["code"] == code


def test_pre_v1_shape_and_sink_owned_fields_are_rejected():
    pre_v1 = {
        "event_id": str(uuid4()),
        "timestamp": "2026-07-23T18:00:00Z",
        "service": "forgesmithy",
        "event_type": "session.started",
        "severity": "info",
        "metadata": {},
        "metrics": {},
    }
    with pytest.raises(ValidationError):
        _submission(pre_v1)

    for sink_field in ("received_at", "event_digest"):
        payload = _event()
        payload[sink_field] = "2026-07-23T18:00:01Z"
        with pytest.raises(ValidationError):
            _submission(payload)


def test_unsupported_schema_boolean_metric_and_zero_trace_fail_closed():
    payload = _event()
    payload["schema_version"] = "ForgeEvent.v2"
    with pytest.raises(ValidationError) as error:
        _submission(payload)
    assert error.value.errors()[0]["type"] == "unsupported_sink_schema"

    payload = _event()
    payload["metrics"] = {"healthy": True}
    with pytest.raises(ValidationError):
        _submission(payload)

    payload = _event()
    payload["trace_id"] = "0" * 32
    with pytest.raises(ValidationError):
        _submission(payload)


def test_ingest_enforces_64_kib_over_complete_producer_projection():
    accepted = _event_with_canonical_size(MAX_CANONICAL_EVENT_BYTES)
    assert len(rfc8785.dumps(_submission(accepted).model_dump(mode="json"))) == 65536

    rejected = _event_with_canonical_size(MAX_CANONICAL_EVENT_BYTES + 1)
    with pytest.raises(ValidationError) as error:
        _submission(rejected)
    assert error.value.errors()[0]["type"] == EVENT_SIZE_VIOLATION_CODE


def test_writer_kill_switch_disables_capability_and_ingest(db, monkeypatch):
    monkeypatch.setenv("DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED", "false")
    assert get_forge_event_v1_capability(_auth()).write_enabled is False

    with pytest.raises(HTTPException) as error:
        _ingest(db, _submission())

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "telemetry_disabled"
    assert db.query(ForgeEventV1Record).count() == 0


def test_runtime_capability_copy_matches_admitted_fixture():
    expected = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
    actual = get_forge_event_v1_capability(_auth()).model_dump(mode="json")
    assert actual == expected

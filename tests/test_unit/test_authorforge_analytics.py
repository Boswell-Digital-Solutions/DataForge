"""AuthorForge's cloud boundary accepts only the strict analytics envelope."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.requests import Request

from app.api.authorforge_boundary_router import reject_authorforge_content
from app.api.routes.events_router import ingest_authorforge_analytics
from app.api.routes import events_router as events_module
from app.main import app, request_validation_exception_handler
from app.models import authorforge_analytics_schemas as analytics_schemas
from app.models.authorforge_analytics_models import AuthorForgeAnalyticsRecord
from app.models.authorforge_analytics_schemas import AuthorForgeAnalyticsEnvelopeV1


def valid_envelope() -> dict:
    return {
        "schema_version": "AuthorForgeAnalyticsEnvelope.v1",
        "policy_version": "authorforge-analytics-policy.v1",
        "event_id": "5eb1b0cc-86bb-475b-a9c8-48f487fa6071",
        "occurred_at": "2026-07-20T16:00:00Z",
        "product": "authorforge",
        "application": "desktop",
        "build_version": "1.4.0",
        "installation_pseudonym": "afi_0123456789abcdef0123456789abcdef",
        "project_pseudonym": "afp_fedcba9876543210fedcba9876543210",
        "feature_id": "draft-evaluate",
        "workflow_id": "revision-pass",
        "execution_lane": "local",
        "route_classification": "local_only",
        "content_authority": "authorforge_embedded_database",
        "event_type": "workflow_completed",
        "action": "complete",
        "status": "success",
        "outcome": "accepted",
        "operation_count": 1,
        "duration_ms": 37,
        "offline": True,
    }


@pytest.mark.unit
def test_valid_envelope_maps_only_named_dimensions():
    envelope = AuthorForgeAnalyticsEnvelopeV1.model_validate(valid_envelope())

    assert envelope.product == "authorforge"
    assert envelope.bounded_metrics() == {"operation_count": 1, "duration_ms": 37}
    assert set(envelope.bounded_dimensions()) <= set(
        AuthorForgeAnalyticsEnvelopeV1.model_fields
    )
    assert "manuscript" not in envelope.bounded_dimensions()
    assert "metadata" not in envelope.model_dump()


@pytest.mark.unit
@pytest.mark.parametrize(
    "forbidden_key",
    [
        "manuscript",
        "chapter_text",
        "notes",
        "prompt",
        "model_response",
        "research_excerpt",
        "worldbuilding",
        "embedding_vector",
        "file_path",
        "raw_logs",
        "email",
        "user_identity",
        "attachment",
        "metadata",
        "arbitrary_safe_looking_field",
    ],
)
def test_content_identity_and_arbitrary_fields_fail_closed(forbidden_key):
    payload = valid_envelope()
    payload[forbidden_key] = "PRIVATE-CONTENT-MUST-NOT-PASS"

    with pytest.raises(ValidationError):
        AuthorForgeAnalyticsEnvelopeV1.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("installation_pseudonym", "alice@example.com"),
        ("project_pseudonym", "raw-project-id"),
        ("event_type", "free_form_event"),
        ("execution_lane", "unbounded-lane"),
        ("duration_ms", 604_800_001),
        ("build_version", "x" * 65),
    ],
)
def test_identity_cardinality_and_size_bounds(field, value):
    payload = valid_envelope()
    payload[field] = value

    with pytest.raises(ValidationError):
        AuthorForgeAnalyticsEnvelopeV1.model_validate(payload)


@pytest.mark.unit
def test_total_envelope_size_is_bounded(monkeypatch):
    monkeypatch.setattr(analytics_schemas, "MAX_ENVELOPE_BYTES", 100)

    with pytest.raises(ValidationError):
        AuthorForgeAnalyticsEnvelopeV1.model_validate(valid_envelope())


@pytest.mark.unit
@pytest.mark.parametrize(
    "updates",
    [
        {"route_classification": "local_only", "execution_lane": "hybrid"},
        {"route_classification": "cloud_model_api", "execution_lane": "local"},
        {
            "route_classification": "cloud_model_api",
            "execution_lane": "cloud_model",
            "offline": True,
        },
        {
            "route_classification": "cloud_model_api",
            "execution_lane": "cloud_model",
            "provider_id": "local",
        },
    ],
)
def test_execution_routing_combinations_fail_closed(updates):
    payload = valid_envelope()
    payload.update(updates)

    with pytest.raises(ValidationError):
        AuthorForgeAnalyticsEnvelopeV1.model_validate(payload)


@pytest.mark.unit
def test_dedicated_api_key_requires_authorforge_write_scope(monkeypatch):
    monkeypatch.setattr(
        events_module,
        "validate_api_key",
        lambda token: SimpleNamespace(
            id="key-id",
            metadata={"service": "authorforge", "scopes": ["analytics:write"]},
        ),
    )
    assert events_module.verify_authorforge_analytics_key("Bearer test-key") == "key-id"

    monkeypatch.setattr(
        events_module,
        "validate_api_key",
        lambda token: SimpleNamespace(
            id="key-id",
            metadata={"service": "authorforge", "scopes": ["analytics:read"]},
        ),
    )
    with pytest.raises(HTTPException) as raised:
        events_module.verify_authorforge_analytics_key("Bearer test-key")
    assert raised.value.status_code == 403


@pytest.mark.unit
def test_dedicated_endpoint_is_idempotent(db):
    envelope = AuthorForgeAnalyticsEnvelopeV1.model_validate(valid_envelope())
    first = ingest_authorforge_analytics(envelope, db, "test-key-id")
    second = ingest_authorforge_analytics(envelope, db, "test-key-id")

    assert first.status == "accepted"
    assert second.status == "duplicate"
    record = db.get(
        AuthorForgeAnalyticsRecord,
        UUID("5eb1b0cc-86bb-475b-a9c8-48f487fa6071"),
    )
    assert record.schema_version == "AuthorForgeAnalyticsEnvelope.v1"
    assert record.canonical_bytes == len(envelope.canonical_bytes())
    assert record.event_digest == envelope.event_digest()
    assert record.dimensions["content_authority"] == "authorforge_embedded_database"
    assert set(record.metrics) == {"operation_count", "duration_ms"}
    assert "PRIVATE" not in str(record.dimensions)


@pytest.mark.unit
def test_dedicated_endpoint_rejects_same_id_with_different_content(db):
    first = AuthorForgeAnalyticsEnvelopeV1.model_validate(valid_envelope())
    changed_payload = valid_envelope()
    changed_payload["duration_ms"] = 38
    changed = AuthorForgeAnalyticsEnvelopeV1.model_validate(changed_payload)

    ingest_authorforge_analytics(first, db, "test-key-id")
    with pytest.raises(HTTPException) as raised:
        ingest_authorforge_analytics(changed, db, "test-key-id")

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "authorforge_analytics_identity_conflict"
    stored = db.get(AuthorForgeAnalyticsRecord, first.event_id)
    assert stored.event_digest == first.event_digest()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejected_payload_is_not_echoed_or_logged(caplog):
    payload = deepcopy(valid_envelope())
    payload["manuscript"] = "PRIVATE-MANUSCRIPT-SENTINEL"

    with pytest.raises(ValidationError) as raised:
        AuthorForgeAnalyticsEnvelopeV1.model_validate(payload)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/events/authorforge-analytics",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1),
            "scheme": "http",
        }
    )
    response = await request_validation_exception_handler(
        request,
        RequestValidationError(raised.value.errors(), body=payload),
    )

    assert response.status_code == 422
    assert b"PRIVATE-MANUSCRIPT-SENTINEL" not in response.body
    assert "PRIVATE-MANUSCRIPT-SENTINEL" not in caplog.text


@pytest.mark.unit
def test_retired_authorforge_content_api_rejects_without_inspection(caplog):
    with pytest.raises(HTTPException) as raised:
        reject_authorforge_content("anything/chapters")

    assert raised.value.status_code == 410
    assert raised.value.detail["code"] == "authorforge_content_local_only"
    assert "PRIVATE-MANUSCRIPT" not in caplog.text


@pytest.mark.unit
def test_production_app_mounts_only_tombstone_and_dedicated_analytics_route():
    route_methods = {
        (route.path, frozenset(route.methods or ()))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert (
        "/api/v1/events/authorforge-analytics",
        frozenset({"POST"}),
    ) in route_methods
    assert any(path == "/api/projects/{retired_path:path}" for path, _ in route_methods)
    assert not any(path.startswith("/api/projects/{project_id}") for path, _ in route_methods)
    analytics_route = next(
        route
        for route in app.routes
        if route.path == "/api/v1/events/authorforge-analytics"
    )
    assert analytics_route.status_code == 202

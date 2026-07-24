"""Exercise the canonical HTTP handler against the migrated PostgreSQL shape."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, Response
from sqlalchemy import select

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    get_forge_event_v1_capability,
    ingest_forge_event_v1,
)
from app.auth import ApiKeyInfo
from app.database import SessionLocal
from app.main import app
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import ForgeEventV1Submission


def _auth() -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="migration-proof-key",
            key_prefix="migration-",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": "neuroforge",
                "environment": "staging",
                "tenant_ref": None,
                "scopes": ["telemetry:write"],
            },
        ),
    )


def _payload() -> dict:
    return {
        "schema_version": "ForgeEvent.v1",
        "event_id": "55555555-5555-4555-8555-555555555555",
        "occurred_at": "2026-07-23T19:00:00Z",
        "service_name": "neuroforge",
        "service_instance_id": "neuroforge-staging-1",
        "environment": "staging",
        "tenant_ref": None,
        "event_type": "inference.completed",
        "severity": "info",
        "outcome": "ok",
        "evidence_class": "operational",
        "correlation_id": None,
        "trace_id": None,
        "span_id": None,
        "parent_span_id": None,
        "attributes": {"model": "proof-model"},
        "metrics": {"duration_ms": 21},
        "privacy_class": "internal",
        "retention_class": "standard",
        "sampled": False,
        "sample_rate": None,
        "sampling_reason": "rate_limited",
    }


def main() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/telemetry/events" in paths
    assert "/api/v1/telemetry/events:batch" not in paths

    auth = _auth()
    capability = get_forge_event_v1_capability(auth)
    assert capability.write_enabled is True
    assert capability.pre_v1_fallback is False
    assert capability.dual_write is False
    assert len(capability.supported_fields) == 24

    event = ForgeEventV1Submission.model_validate(_payload())
    with SessionLocal() as session:
        first = ingest_forge_event_v1(event, Response(), session, auth)
        replay_response = Response()
        replay = ingest_forge_event_v1(event, replay_response, session, auth)
        assert first.identity_outcome == "inserted"
        assert replay.identity_outcome == "exact_replay"
        assert first.received_at == replay.received_at
        assert first.event_digest == replay.event_digest
        assert replay_response.status_code == 200

        conflict_payload = _payload()
        conflict_payload["event_type"] = "inference.failed"
        try:
            ingest_forge_event_v1(
                ForgeEventV1Submission.model_validate(conflict_payload),
                Response(),
                session,
                auth,
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail["code"] == "event_identity_conflict"
        else:
            raise AssertionError("same-ID/different-content event was not rejected")

        stored = session.execute(
            select(ForgeEventV1Record).where(
                ForgeEventV1Record.event_id == event.event_id
            )
        ).scalar_one()
        assert stored.received_at == first.received_at

    print("FORGE_EVENT_V1_POSTGRES_API_OK")


if __name__ == "__main__":
    main()

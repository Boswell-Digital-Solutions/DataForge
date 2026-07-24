"""Pinned real-caller proof for DataForge's own canonical telemetry."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api import search
from app.telemetry_client import DataForgeTelemetry
from forge_telemetry import (
    ForgeEventTransportError,
    ForgeEventV1IngestReceipt,
    forge_event_digest,
)


ROOT = Path(__file__).resolve().parents[1]
FORGE_TELEMETRY_COMMIT = "9390ea322a6fb03482bb62e8d7ce1f37c697d909"


class FakeCanonicalTransport:
    def __init__(self, outcome: str = "inserted") -> None:
        self.outcome = outcome
        self.events = []
        self.shutdown_calls = 0

    async def submit_async(self, event):
        self.events.append(event)
        if self.outcome == "failed":
            raise ForgeEventTransportError(
                "telemetry_persistence_unavailable",
                status_code=503,
                retryable=True,
            )
        return ForgeEventV1IngestReceipt.model_validate(
            {
                "schema_version": "forge.dataforge.telemetry.ingest.v1",
                "event_id": str(event.event_id),
                "event_digest": forge_event_digest(event),
                "received_at": "2026-07-23T23:30:00Z",
                "identity_outcome": self.outcome,
            }
        )

    async def verify_capability_async(self):
        return SimpleNamespace(
            write_enabled=True,
            event_schema_versions=["ForgeEvent.v1"],
            event_schema_sha256="6" * 64,
            max_canonical_event_bytes=65536,
        )

    def async_status(self):
        return {
            "max_workers": 4,
            "max_queue": 16,
            "capacity": 20,
            "pending": 0,
            "queued": 0,
            "live_workers": 0,
            "closed": False,
        }

    async def shutdown_async(self):
        self.shutdown_calls += 1
        return True


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["inserted", "exact_replay"])
async def test_dataforge_accepts_only_canonical_sink_receipts(
    monkeypatch,
    outcome,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
    )
    transport = FakeCanonicalTransport(outcome)
    client._transport = transport

    assert await client.emit_search(
        search_kind="semantic",
        succeeded=True,
        correlation_id="request-correlation",
        metrics={
            "duration_ms": 12.5,
            "embedding_duration_ms": 5.0,
            "results_count": 3,
        },
    )

    event = transport.events[0]
    assert event.schema_version == "ForgeEvent.v1"
    assert event.service_name == "dataforge"
    assert event.environment == "staging"
    assert event.tenant_ref is None
    assert event.event_type == "search.completed"
    assert event.severity == "info"
    assert event.outcome == "ok"
    assert event.evidence_class == "operational"
    assert event.attributes == {"search_kind": "semantic"}
    assert event.metrics == {
        "duration_ms": 12.5,
        "embedding_duration_ms": 5.0,
        "results_count": 3.0,
        "latency_ms": 12.5,
    }
    assert event.privacy_class == "internal"
    assert event.sampled is True


@pytest.mark.asyncio
async def test_dataforge_failure_event_omits_search_and_exception_content(
    monkeypatch,
) -> None:
    secret = "CANARY_SUPER_SECRET"
    monkeypatch.setenv("ENVIRONMENT", "development")
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
    )
    transport = FakeCanonicalTransport()
    client._transport = transport

    assert await client.emit_search(
        search_kind="hybrid",
        succeeded=False,
        correlation_id=secret,
        metrics={
            "duration_ms": 9,
            secret: 42,
        },
    )

    event_bytes = json.dumps(
        transport.events[0].model_dump(mode="json"),
        sort_keys=True,
    )
    assert secret not in event_bytes
    assert transport.events[0].event_type == "search.failed"
    assert transport.events[0].metrics == {
        "duration_ms": 9.0,
        "latency_ms": 9.0,
    }


@pytest.mark.asyncio
async def test_dataforge_transport_failure_is_value_free() -> None:
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
    )
    client._transport = FakeCanonicalTransport("failed")

    assert not await client.emit_search(
        search_kind="keyword",
        succeeded=False,
        correlation_id=None,
        metrics={"duration_ms": 3},
    )
    assert client._last_error == "telemetry_persistence_unavailable"


def test_dataforge_has_no_broader_key_or_url_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DATAFORGE_TELEMETRY_BASE_URL", raising=False)
    monkeypatch.delenv("DATAFORGE_TELEMETRY_API_KEY", raising=False)
    monkeypatch.setenv("DATAFORGE_API_KEY", "broad-service-key")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://dataforge.example.test")
    client = DataForgeTelemetry()

    assert client._get_transport() is None
    assert client._last_error == "telemetry_configuration_missing"


@pytest.mark.asyncio
async def test_dataforge_health_and_shutdown_are_bounded() -> None:
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
    )
    transport = FakeCanonicalTransport()
    client._transport = transport

    status = await client.status()
    assert status["enabled"] is True
    assert status["async"]["capacity"] == 20
    assert "api_key" not in json.dumps(status).lower()

    await client.close()
    assert transport.shutdown_calls == 1
    assert client._transport is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search_function", "search_kind"),
    [
        (search.semantic_search, "semantic"),
        (search.keyword_search, "keyword"),
        (search.hybrid_search, "hybrid"),
    ],
)
async def test_supported_fallback_searches_emit_canonical_outcomes(
    db,
    monkeypatch,
    search_function,
    search_kind,
) -> None:
    emitter = AsyncMock(return_value=True)
    monkeypatch.setattr(
        search,
        "telemetry",
        SimpleNamespace(emit_search=emitter),
    )

    response = await search_function(
        db=db,
        query="CANARY_PRIVATE_QUERY",
        correlation_id="request-correlation",
    )

    assert response.total_results == 0
    emitter.assert_awaited_once()
    emitted = emitter.await_args.kwargs
    assert emitted["search_kind"] == search_kind
    assert emitted["succeeded"] is True
    assert set(emitted["metrics"]) == {"duration_ms", "results_count"}
    assert "CANARY_PRIVATE_QUERY" not in json.dumps(emitted, default=str)


def test_dataforge_pins_only_the_canonical_transport() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    search_source = (ROOT / "app" / "api" / "search.py").read_text(
        encoding="utf-8"
    )
    producer_source = (ROOT / "app" / "telemetry_client.py").read_text(
        encoding="utf-8"
    )

    assert f"forge-telemetry.git@{FORGE_TELEMETRY_COMMIT}" in requirements
    assert "forge-telemetry.git@v0.3.0" not in requirements
    assert "TelemetryClient" not in search_source
    assert "telemetry.emit(" not in search_source
    assert "await telemetry.emit_search(" in search_source
    assert "ForgeEventV1HttpTransport" in producer_source
    assert not (ROOT / "examples" / "telemetry_example.py").exists()
    assert not (ROOT / "examples" / "test_telemetry.py").exists()
    assert not (
        ROOT / "docs" / "archive" / "TELEMETRY_INTEGRATION_STATUS.md"
    ).exists()

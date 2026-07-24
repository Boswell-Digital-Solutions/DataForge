"""Pinned real-caller proof for DataForge's own canonical telemetry."""

from __future__ import annotations

import asyncio
import json
import os
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
FORGE_TELEMETRY_COMMIT = "6f45ef69c20eb804f251219fd5ea621d10729db0"


class FakeCanonicalTransport:
    def __init__(self, outcome: str = "inserted") -> None:
        self.outcome = outcome
        self.events = []
        self.shutdown_calls = 0

    async def submit_async(self, event):
        return self.submit(event)

    def submit(self, event):
        self.events.append(event)
        if self.outcome == "failed":
            raise ForgeEventTransportError(
                "telemetry_persistence_unavailable",
                status_code=503,
                retryable=True,
            )
        if self.outcome == "indeterminate":
            raise ForgeEventTransportError(
                "telemetry_transport_indeterminate",
                retryable=False,
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
async def test_opt_in_spool_queues_then_persists_with_linked_evidence(
    tmp_path,
) -> None:
    private_dir = tmp_path / "private-telemetry"
    private_dir.mkdir(mode=0o700)
    os.chmod(private_dir, 0o700)
    spool_path = private_dir / "spool.sqlite3"
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="CANARY_DEDICATED_TELEMETRY_KEY",
        spool_path=spool_path,
    )
    transport = FakeCanonicalTransport()
    client._transport = transport

    assert await client.emit_search(
        search_kind="semantic",
        succeeded=True,
        correlation_id=None,
        metrics={"duration_ms": 4},
    )
    assert transport.events == []

    before = client._spool.status()
    assert before["states"]["queued"] == 1
    assert before["limits"] == {
        "max_entries": 512,
        "max_bytes": 32 * 1024 * 1024,
        "drain_batch_size": 4,
        "max_delivery_attempts": 5,
        "circuit_failure_threshold": 3,
        "circuit_open_s": 15.0,
    }
    assert "CANARY_DEDICATED_TELEMETRY_KEY" not in spool_path.read_bytes().decode(
        "utf-8",
        errors="ignore",
    )

    result = await client.drain_once()

    assert result.persisted == 1
    assert result.receipts[0].previous_receipt_id is not None
    assert len(transport.events) == 1
    assert client._spool.status()["total_entries"] == 0

    status = await client.status()
    assert status["delivery_mode"] == "sqlite_spool"
    assert status["emit_queued"] == 1
    assert status["drain"]["persisted"] == 1
    assert "CANARY_DEDICATED_TELEMETRY_KEY" not in json.dumps(status)

    await client.close()
    assert transport.shutdown_calls == 1


@pytest.mark.asyncio
async def test_spool_retry_is_bounded_and_not_busy_looped(tmp_path) -> None:
    private_dir = tmp_path / "private-telemetry"
    private_dir.mkdir(mode=0o700)
    os.chmod(private_dir, 0o700)
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
        spool_path=private_dir / "spool.sqlite3",
    )
    transport = FakeCanonicalTransport("failed")
    client._transport = transport

    assert await client.emit_search(
        search_kind="keyword",
        succeeded=True,
        correlation_id=None,
        metrics={"duration_ms": 4},
    )
    first = await client.drain_once()
    immediate = await client.drain_once()

    assert first.retry_scheduled == 1
    assert immediate.attempted == 0
    assert len(transport.events) == 1
    assert client._spool.status()["states"]["retry_wait"] == 1

    await client.close()


@pytest.mark.asyncio
async def test_spool_circuit_stops_unavailable_sink_batch(tmp_path) -> None:
    private_dir = tmp_path / "private-telemetry"
    private_dir.mkdir(mode=0o700)
    os.chmod(private_dir, 0o700)
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
        spool_path=private_dir / "spool.sqlite3",
    )
    transport = FakeCanonicalTransport("failed")
    client._transport = transport
    for _ in range(4):
        assert await client.emit_search(
            search_kind="keyword",
            succeeded=True,
            correlation_id=None,
            metrics={"duration_ms": 4},
        )

    opened = await client.drain_once()
    suppressed = await client.drain_once()

    assert opened.attempted == 3
    assert opened.retry_scheduled == 3
    assert opened.circuit_open is True
    assert suppressed.attempted == 0
    assert suppressed.circuit_open is True
    assert len(transport.events) == 3
    assert client._spool.status()["states"]["queued"] == 1
    assert client._spool.status()["circuit"]["open"] is True

    await client.close()


@pytest.mark.asyncio
async def test_spool_never_retries_indeterminate_pilot_event(tmp_path) -> None:
    private_dir = tmp_path / "private-telemetry"
    private_dir.mkdir(mode=0o700)
    os.chmod(private_dir, 0o700)
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
        spool_path=private_dir / "spool.sqlite3",
    )
    transport = FakeCanonicalTransport("indeterminate")
    client._transport = transport
    assert await client.emit_search(
        search_kind="hybrid",
        succeeded=True,
        correlation_id=None,
        metrics={"duration_ms": 4},
    )

    first = await client.drain_once()
    paused = await client.drain_once()

    assert first.indeterminate == 1
    assert paused.attempted == 0
    assert len(transport.events) == 1
    assert client._spool.status()["states"]["indeterminate"] == 1

    await client.close()


@pytest.mark.asyncio
async def test_opt_in_spool_lifecycle_has_one_bounded_worker(tmp_path) -> None:
    private_dir = tmp_path / "private-telemetry"
    private_dir.mkdir(mode=0o700)
    os.chmod(private_dir, 0o700)
    client = DataForgeTelemetry(
        base_url="https://dataforge.example.test",
        api_key="telemetry-key",
        spool_path=private_dir / "spool.sqlite3",
        drain_interval_s=60.0,
        drain_timeout_s=1.0,
    )
    transport = FakeCanonicalTransport()
    client._transport = transport

    assert await client.start()
    await asyncio.sleep(0)
    status = await client.status()

    assert status["drain"]["running"] is True
    assert status["spool"]["async"]["max_workers"] == 1
    assert status["spool"]["async"]["capacity"] == 1

    await client.close()
    assert client._drain_task is None
    assert client._spool is None
    assert transport.shutdown_calls == 1


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
    search_source = (ROOT / "app" / "api" / "search.py").read_text(encoding="utf-8")
    producer_source = (ROOT / "app" / "telemetry_client.py").read_text(encoding="utf-8")

    assert f"forge-telemetry.git@{FORGE_TELEMETRY_COMMIT}" in requirements
    assert "forge-telemetry.git@v0.3.0" not in requirements
    assert "TelemetryClient" not in search_source
    assert "telemetry.emit(" not in search_source
    assert "await telemetry.emit_search(" in search_source
    assert "ForgeEventV1HttpTransport" in producer_source
    assert "SQLiteSpoolTransport" in producer_source
    assert not (ROOT / "examples" / "telemetry_example.py").exists()
    assert not (ROOT / "examples" / "test_telemetry.py").exists()
    assert not (ROOT / "docs" / "archive" / "TELEMETRY_INTEGRATION_STATUS.md").exists()

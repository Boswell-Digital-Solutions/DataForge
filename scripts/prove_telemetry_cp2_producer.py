"""Measured real-producer proof for DataForge's CP2 recovery pilot."""

from __future__ import annotations

import asyncio
import json
import resource
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.telemetry_client import DataForgeTelemetry
from forge_telemetry import (
    ForgeEventV1IngestReceipt,
    forge_event_digest,
)


class _FixtureSink:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, event):
        self.submissions += 1
        return ForgeEventV1IngestReceipt(
            schema_version="forge.dataforge.telemetry.ingest.v1",
            event_id=event.event_id,
            event_digest=forge_event_digest(event),
            received_at=datetime.now(UTC),
            identity_outcome="inserted",
        )

    async def submit_async(self, event):
        return self.submit(event)

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
        return True


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, round((percentile / 100) * (len(ordered) - 1))),
    )
    return ordered[index]


async def prove(event_count: int = 512) -> dict[str, object]:
    if event_count != 512:
        raise ValueError("the CP2 producer proof is fixed at 512 events")
    api_key = "CANARY_CP2_PRODUCER_KEY"
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    with tempfile.TemporaryDirectory(prefix="dataforge-telemetry-cp2-") as directory:
        private_dir = Path(directory)
        private_dir.chmod(0o700)
        spool_path = private_dir / "dataforge-search.sqlite3"
        initial_sink = _FixtureSink()
        producer = DataForgeTelemetry(
            base_url="https://dataforge.example.test",
            api_key=api_key,
            spool_path=spool_path,
        )
        producer._transport = initial_sink

        enqueue_ms: list[float] = []
        for index in range(event_count):
            started = time.perf_counter_ns()
            accepted = await producer.emit_search(
                search_kind=("semantic" if index % 2 == 0 else "hybrid"),
                succeeded=True,
                correlation_id=None,
                metrics={"duration_ms": 4, "results_count": index % 8},
            )
            enqueue_ms.append((time.perf_counter_ns() - started) / 1_000_000)
            if not accepted:
                raise AssertionError("bounded producer admission failed early")

        overflow_accepted = await producer.emit_search(
            search_kind="keyword",
            succeeded=False,
            correlation_id=None,
            metrics={"duration_ms": 5},
        )
        if overflow_accepted:
            raise AssertionError("full spool did not reject newest event")
        queued_status = producer._spool.status()
        queued_file_bytes = spool_path.stat().st_size
        if api_key.encode() in spool_path.read_bytes():
            raise AssertionError("API key entered the recovery database")

        await producer.close()

        recovered_sink = _FixtureSink()
        recovered = DataForgeTelemetry(
            base_url="https://dataforge.example.test",
            api_key=api_key,
            spool_path=spool_path,
        )
        recovered._transport = recovered_sink
        if (
            recovered._get_spool(recovered_sink).status()["total_entries"]
            != event_count
        ):
            raise AssertionError("restart did not recover every queued event")

        drain_started = time.perf_counter_ns()
        drain_passes = 0
        persisted = 0
        while recovered._spool.status()["total_entries"]:
            result = await recovered.drain_once()
            if result is None:
                raise AssertionError("bounded drain returned no result")
            drain_passes += 1
            persisted += result.persisted
            if drain_passes > event_count:
                raise AssertionError("drain did not make finite progress")
        drain_ms = (time.perf_counter_ns() - drain_started) / 1_000_000
        final_status = await recovered.status()
        await recovered.close()

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "schema_version": "dataforge.telemetry.cp2_producer_proof.v1",
        "result": "passed",
        "events": event_count,
        "overflow_policy": {
            "newest_rejected": not overflow_accepted,
            "queued_entries": queued_status["total_entries"],
        },
        "enqueue_latency_ms": {
            "p50": round(statistics.median(enqueue_ms), 6),
            "p95": round(_percentile(enqueue_ms, 95), 6),
            "p99": round(_percentile(enqueue_ms, 99), 6),
            "max": round(max(enqueue_ms), 6),
        },
        "queued_file_bytes": queued_file_bytes,
        "restart_recovered_entries": event_count,
        "drain": {
            "passes": drain_passes,
            "persisted": persisted,
            "duration_ms": round(drain_ms, 6),
            "events_per_second": round(
                event_count / max(drain_ms / 1000, 0.000001),
                3,
            ),
        },
        "resources": {
            "max_rss_delta_kib": max(0, rss_after - rss_before),
            "spool_worker_capacity": final_status["spool"]["async"]["capacity"],
            "http_worker_capacity": final_status["async"]["capacity"],
        },
        "secret_absence": True,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(prove()), sort_keys=True))
    print("CP2_DATAFORGE_PRODUCER_PROOF_OK")

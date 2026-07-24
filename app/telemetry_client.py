"""Canonical, privacy-bounded telemetry producer for DataForge operations."""

from __future__ import annotations

import asyncio
import logging
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Mapping
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5


logger = logging.getLogger(__name__)

SearchKind = Literal["semantic", "keyword", "hybrid"]
_SEARCH_METRICS = frozenset(
    {
        "duration_ms",
        "embedding_duration_ms",
        "db_query_duration_ms",
        "results_count",
        "avg_similarity",
        "avg_rank",
        "semantic_duration_ms",
        "keyword_duration_ms",
        "rrf_duration_ms",
        "semantic_results",
        "keyword_results",
        "avg_rrf_score",
    }
)

# Evidence-derived pilot bounds. The SDK validates these against its hard
# ceilings; changing them requires a new measured proof.
_SPOOL_MAX_ENTRIES = 512
_SPOOL_MAX_BYTES = 32 * 1024 * 1024
_SPOOL_DRAIN_BATCH_SIZE = 4
_SPOOL_MAX_DELIVERY_ATTEMPTS = 5
_SPOOL_RETRY_BACKOFF_INITIAL_S = 1.0
_SPOOL_RETRY_BACKOFF_MAX_S = 30.0
_SPOOL_CIRCUIT_FAILURE_THRESHOLD = 3
_SPOOL_CIRCUIT_OPEN_S = 15.0
_SPOOL_INFLIGHT_LEASE_S = 30.0
_SPOOL_ASYNC_SHUTDOWN_TIMEOUT_S = 15.0
_SPOOL_DRAIN_INTERVAL_S = 5.0
_SPOOL_DRAIN_TIMEOUT_S = 15.0


class DataForgeTelemetry:
    """Own DataForge's strict ForgeEvent.v1 producer and transport lifecycle."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float | None = None,
        spool_path: str | os.PathLike[str] | None = None,
        drain_interval_s: float | None = None,
        drain_timeout_s: float | None = None,
    ) -> None:
        self.base_url = (
            base_url
            if base_url is not None
            else os.getenv("DATAFORGE_TELEMETRY_BASE_URL", "")
        )
        self._api_key = (
            api_key
            if api_key is not None
            else os.getenv("DATAFORGE_TELEMETRY_API_KEY", "")
        )
        self.timeout_s = (
            timeout_s if timeout_s is not None else self._configured_timeout()
        )
        configured_spool_path = (
            str(spool_path)
            if spool_path is not None
            else os.getenv("DATAFORGE_TELEMETRY_SPOOL_PATH", "")
        )
        self.spool_path = (
            Path(configured_spool_path).expanduser() if configured_spool_path else None
        )
        self.drain_interval_s = (
            drain_interval_s
            if drain_interval_s is not None
            else self._configured_positive_float(
                "DATAFORGE_TELEMETRY_DRAIN_INTERVAL_SECONDS",
                _SPOOL_DRAIN_INTERVAL_S,
                maximum=60.0,
            )
        )
        self.drain_timeout_s = (
            drain_timeout_s
            if drain_timeout_s is not None
            else self._configured_positive_float(
                "DATAFORGE_TELEMETRY_DRAIN_TIMEOUT_SECONDS",
                _SPOOL_DRAIN_TIMEOUT_S,
                maximum=60.0,
            )
        )
        self._transport: Any | None = None
        self._spool: Any | None = None
        self._drain_task: asyncio.Task[None] | None = None
        self._drain_stop: asyncio.Event | None = None
        self._closed = False
        self._emit_attempts = 0
        self._emit_succeeded = 0
        self._emit_queued = 0
        self._emit_failed = 0
        self._drain_passes = 0
        self._drain_persisted = 0
        self._drain_retry_scheduled = 0
        self._drain_indeterminate = 0
        self._drain_quarantined = 0
        self._drain_failed = 0
        self._last_error: str | None = None

    @staticmethod
    def _configured_timeout() -> float:
        try:
            return float(os.getenv("DATAFORGE_TELEMETRY_TIMEOUT", "5"))
        except ValueError:
            return float("nan")

    @staticmethod
    def _configured_positive_float(
        name: str,
        default: float,
        *,
        maximum: float,
    ) -> float:
        try:
            value = float(os.getenv(name, str(default)))
        except ValueError:
            return float("nan")
        if not math.isfinite(value) or value <= 0 or value > maximum:
            return float("nan")
        return value

    def _get_transport(self) -> Any | None:
        if self._closed:
            self._last_error = "telemetry_transport_closed"
            return None
        if self._transport is not None:
            return self._transport
        if not self.base_url or not self._api_key:
            self._last_error = "telemetry_configuration_missing"
            return None
        try:
            from forge_telemetry import ForgeEventV1HttpTransport

            self._transport = ForgeEventV1HttpTransport(
                self.base_url,
                self._api_key,
                timeout_s=self.timeout_s,
                allow_insecure_loopback=(
                    urlparse(self.base_url).hostname
                    in {"127.0.0.1", "::1", "localhost"}
                ),
            )
            return self._transport
        except Exception:
            self._last_error = "telemetry_transport_configuration_invalid"
            logger.warning(
                "Canonical telemetry transport unavailable",
                extra={"error_code": self._last_error},
            )
            return None

    def _get_spool(self, downstream: Any | None = None) -> Any | None:
        if self._spool is not None:
            return self._spool
        if self.spool_path is None:
            return None
        if self._closed:
            self._last_error = "telemetry_transport_closed"
            return None
        downstream = downstream or self._get_transport()
        if downstream is None:
            return None
        try:
            from forge_telemetry import SQLiteSpoolTransport, SpoolLimits

            self._spool = SQLiteSpoolTransport(
                self.spool_path,
                downstream,
                limits=SpoolLimits(
                    max_entries=_SPOOL_MAX_ENTRIES,
                    max_bytes=_SPOOL_MAX_BYTES,
                    drain_batch_size=_SPOOL_DRAIN_BATCH_SIZE,
                    max_delivery_attempts=_SPOOL_MAX_DELIVERY_ATTEMPTS,
                    retry_backoff_initial_s=_SPOOL_RETRY_BACKOFF_INITIAL_S,
                    retry_backoff_max_s=_SPOOL_RETRY_BACKOFF_MAX_S,
                    circuit_failure_threshold=(_SPOOL_CIRCUIT_FAILURE_THRESHOLD),
                    circuit_open_s=_SPOOL_CIRCUIT_OPEN_S,
                    inflight_lease_s=_SPOOL_INFLIGHT_LEASE_S,
                    async_shutdown_timeout_s=(_SPOOL_ASYNC_SHUTDOWN_TIMEOUT_S),
                ),
            )
            return self._spool
        except Exception:
            self._last_error = "telemetry_spool_configuration_invalid"
            logger.warning(
                "Canonical telemetry recovery spool unavailable",
                extra={"error_code": self._last_error},
            )
            return None

    async def start(self) -> bool:
        """Start the single caller-owned drain loop for the opt-in spool."""

        if self._closed:
            self._last_error = "telemetry_transport_closed"
            return False
        if self.spool_path is None:
            return True
        if self._drain_task is not None and not self._drain_task.done():
            return True
        if not math.isfinite(self.drain_interval_s) or not math.isfinite(
            self.drain_timeout_s
        ):
            self._last_error = "telemetry_spool_configuration_invalid"
            return False
        transport = self._get_transport()
        if transport is None or self._get_spool(transport) is None:
            return False
        self._drain_stop = asyncio.Event()
        self._drain_task = asyncio.create_task(
            self._drain_loop(),
            name="dataforge-telemetry-spool-drain",
        )
        return True

    async def _drain_loop(self) -> None:
        assert self._drain_stop is not None
        while not self._drain_stop.is_set():
            await self.drain_once()
            try:
                await asyncio.wait_for(
                    self._drain_stop.wait(),
                    timeout=self.drain_interval_s,
                )
            except TimeoutError:
                continue

    async def drain_once(self) -> Any | None:
        """Run one bounded pass; indeterminate rows remain paused."""

        spool = self._get_spool()
        if spool is None:
            return None
        try:
            result = await spool.drain_once_async(timeout_s=self.drain_timeout_s)
            self._drain_passes += 1
            self._drain_persisted += result.persisted
            self._drain_retry_scheduled += result.retry_scheduled
            self._drain_indeterminate += result.indeterminate
            self._drain_quarantined += result.quarantined
            if result.indeterminate:
                self._last_error = "telemetry_spool_indeterminate"
            elif result.quarantined:
                self._last_error = "telemetry_spool_quarantined"
            elif result.retry_scheduled:
                self._last_error = "telemetry_spool_retry_scheduled"
            elif result.persisted:
                self._last_error = None
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._drain_failed += 1
            self._last_error = getattr(
                exc,
                "code",
                "telemetry_spool_drain_failed",
            )
            logger.warning(
                "Canonical telemetry recovery drain failed",
                extra={"error_code": self._last_error},
            )
            return None

    async def emit_search(
        self,
        *,
        search_kind: SearchKind,
        succeeded: bool,
        correlation_id: UUID | str | None,
        metrics: Mapping[str, int | float],
    ) -> bool:
        """Submit one allowlisted search outcome without search input content."""

        self._emit_attempts += 1
        try:
            transport = self._get_transport()
            if transport is None:
                self._emit_failed += 1
                return False
            event = self._search_event(
                search_kind=search_kind,
                succeeded=succeeded,
                correlation_id=correlation_id,
                metrics=metrics,
            )
            if self.spool_path is not None or self._spool is not None:
                spool = self._get_spool(transport)
                if spool is None:
                    self._emit_failed += 1
                    return False
                receipt = spool.enqueue(event)
                if receipt.aggregate_status != "accepted_not_persisted":
                    self._emit_failed += 1
                    self._last_error = "telemetry_spool_capacity_exceeded"
                    return False
                self._emit_succeeded += 1
                self._emit_queued += 1
                self._last_error = None
                logger.debug(
                    "Canonical DataForge telemetry queued",
                    extra={
                        "event_id": str(receipt.event_id),
                        "event_type": event.event_type,
                    },
                )
                return True
            receipt = await transport.submit_async(event)
            self._emit_succeeded += 1
            self._last_error = None
            logger.debug(
                "Canonical DataForge telemetry persisted",
                extra={
                    "event_id": str(receipt.event_id),
                    "event_type": event.event_type,
                    "identity_outcome": receipt.identity_outcome,
                },
            )
            return True
        except Exception as exc:
            self._emit_failed += 1
            self._last_error = getattr(exc, "code", "telemetry_emission_failed")
            logger.warning(
                "Canonical DataForge telemetry failed",
                extra={"error_code": self._last_error},
            )
            return False

    @staticmethod
    def _search_event(
        *,
        search_kind: SearchKind,
        succeeded: bool,
        correlation_id: UUID | str | None,
        metrics: Mapping[str, int | float],
    ) -> Any:
        from forge_telemetry import validate_forge_event_v1

        if search_kind not in {"semantic", "keyword", "hybrid"}:
            raise ValueError("unsupported_dataforge_search_kind")
        safe_metrics: dict[str, int | float] = {}
        for name, value in metrics.items():
            if name not in _SEARCH_METRICS:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("invalid_dataforge_search_metric")
            safe_metrics[name] = value
        if "duration_ms" in safe_metrics:
            safe_metrics["latency_ms"] = safe_metrics["duration_ms"]

        return validate_forge_event_v1(
            {
                "schema_version": "ForgeEvent.v1",
                "event_id": str(uuid4()),
                "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "service_name": "dataforge",
                "service_instance_id": None,
                "environment": os.getenv("ENVIRONMENT", "development").lower(),
                "tenant_ref": None,
                "event_type": ("search.completed" if succeeded else "search.failed"),
                "severity": "info" if succeeded else "error",
                "outcome": "ok" if succeeded else "fail",
                "evidence_class": "operational",
                "correlation_id": DataForgeTelemetry._correlation_uuid(correlation_id),
                "trace_id": None,
                "span_id": None,
                "parent_span_id": None,
                "attributes": {"search_kind": search_kind},
                "metrics": safe_metrics,
                "privacy_class": "internal",
                "retention_class": "standard",
                "sampled": True,
                "sample_rate": None,
                "sampling_reason": "always_on",
            }
        )

    @staticmethod
    def _correlation_uuid(value: UUID | str | None) -> str | None:
        if value is None:
            return None
        try:
            return str(UUID(str(value)))
        except (ValueError, AttributeError, TypeError):
            return str(uuid5(NAMESPACE_URL, str(value)))

    async def status(self) -> dict[str, Any]:
        """Return only non-secret target, capability, counters, and worker state."""

        target = urlparse(self.base_url)
        result: dict[str, Any] = {
            "enabled": False,
            "target": {
                "host": target.hostname,
                "port": str(target.port) if target.port else None,
                "path": target.path.rstrip("/") or "/",
            },
            "emit_attempts": self._emit_attempts,
            "emit_succeeded": self._emit_succeeded,
            "emit_queued": self._emit_queued,
            "emit_failed": self._emit_failed,
            "delivery_mode": (
                "sqlite_spool" if self.spool_path is not None else "direct_http"
            ),
            "last_error": self._last_error,
            "drain": {
                "running": (
                    self._drain_task is not None and not self._drain_task.done()
                ),
                "passes": self._drain_passes,
                "persisted": self._drain_persisted,
                "retry_scheduled": self._drain_retry_scheduled,
                "indeterminate": self._drain_indeterminate,
                "quarantined": self._drain_quarantined,
                "failed": self._drain_failed,
            },
        }
        transport = self._get_transport()
        if transport is None:
            result["reason"] = self._last_error
            return result
        try:
            capability = await transport.verify_capability_async()
            result["enabled"] = capability.write_enabled
            result["event_schema_version"] = capability.event_schema_versions[0]
            result["event_schema_sha256"] = capability.event_schema_sha256
            result["max_canonical_event_bytes"] = capability.max_canonical_event_bytes
            result["async"] = transport.async_status()
            if self.spool_path is not None:
                spool = self._get_spool(transport)
                if spool is None:
                    result["reason"] = self._last_error
                    result["enabled"] = False
                else:
                    result["spool"] = spool.status()
        except Exception as exc:
            result["reason"] = getattr(
                exc,
                "code",
                "telemetry_capability_unavailable",
            )
        return result

    async def close(self) -> None:
        """Stop drain admission and observe both finite shutdown deadlines."""

        transport = self._transport
        spool = self._spool
        drain_task = self._drain_task
        drain_stop = self._drain_stop
        self._closed = True
        if drain_stop is not None:
            drain_stop.set()
        if drain_task is not None and not drain_task.done():
            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass
        self._drain_task = None
        self._drain_stop = None
        if spool is not None:
            try:
                if not await spool.shutdown_async():
                    self._last_error = "telemetry_spool_shutdown_timeout"
            except Exception as exc:
                self._last_error = getattr(
                    exc,
                    "code",
                    "telemetry_spool_shutdown_failed",
                )
        self._spool = None
        self._transport = None
        if transport is None:
            return
        try:
            if not await transport.shutdown_async():
                self._last_error = "telemetry_shutdown_timeout"
        except Exception as exc:
            self._last_error = getattr(exc, "code", "telemetry_shutdown_failed")


telemetry = DataForgeTelemetry()

"""Canonical, privacy-bounded telemetry producer for DataForge operations."""

from __future__ import annotations

import logging
import math
import os
from datetime import UTC, datetime
from typing import Any, Literal, Mapping
from urllib.parse import urlparse
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL


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


class DataForgeTelemetry:
    """Own DataForge's strict ForgeEvent.v1 producer and transport lifecycle."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float | None = None,
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
            timeout_s
            if timeout_s is not None
            else self._configured_timeout()
        )
        self._transport: Any | None = None
        self._emit_attempts = 0
        self._emit_succeeded = 0
        self._emit_failed = 0
        self._last_error: str | None = None

    @staticmethod
    def _configured_timeout() -> float:
        try:
            return float(os.getenv("DATAFORGE_TELEMETRY_TIMEOUT", "5"))
        except ValueError:
            return float("nan")

    def _get_transport(self) -> Any | None:
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
                "event_type": (
                    "search.completed" if succeeded else "search.failed"
                ),
                "severity": "info" if succeeded else "error",
                "outcome": "ok" if succeeded else "fail",
                "evidence_class": "operational",
                "correlation_id": DataForgeTelemetry._correlation_uuid(
                    correlation_id
                ),
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
            "emit_failed": self._emit_failed,
            "last_error": self._last_error,
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
            result["max_canonical_event_bytes"] = (
                capability.max_canonical_event_bytes
            )
            result["async"] = transport.async_status()
        except Exception as exc:
            result["reason"] = getattr(
                exc,
                "code",
                "telemetry_capability_unavailable",
            )
        return result

    async def close(self) -> None:
        """Close admission and wait the SDK's finite shutdown deadline."""

        transport = self._transport
        self._transport = None
        if transport is None:
            return
        try:
            if not await transport.shutdown_async():
                self._last_error = "telemetry_shutdown_timeout"
        except Exception as exc:
            self._last_error = getattr(exc, "code", "telemetry_shutdown_failed")


telemetry = DataForgeTelemetry()

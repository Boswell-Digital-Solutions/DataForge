"""Bounded HTTP contract for Forge Telemetry v0.3 event ingestion."""

import hashlib
import json
import math
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any
from uuid import UUID, uuid4

import rfc8785
from forge_telemetry import TelemetryEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError


MAX_BATCH_EVENTS = 100
MAX_BATCH_JSON_BYTES = 256 * 1024
TELEMETRY_RESOURCE_BOUNDS_SHA256 = (
    "6729e46ea46544095c1e7dd8bcdb9df9eec84df1889b9e4439db6b3f998eb919"
)


def _load_telemetry_resource_bounds() -> dict[str, Any]:
    name = "telemetry_resource_bounds.v1.json"
    try:
        content = files("app.models").joinpath("contracts", name).read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"required telemetry contract is unavailable: {name}"
        ) from exc
    if hashlib.sha256(content).hexdigest() != TELEMETRY_RESOURCE_BOUNDS_SHA256:
        raise RuntimeError(f"telemetry contract digest mismatch: {name}")
    payload = json.loads(content)
    if (
        payload.get("schema_version") != "forge.telemetry.resource_bounds.v1"
        or payload.get("remaining_bounds_status") != "unapproved"
        or payload.get("canonical_event", {}).get("serialization") != "rfc8785"
        or payload.get("canonical_event", {}).get("scope") != "complete_redacted_event"
        or payload.get("canonical_event", {}).get("producer_override")
        != "stricter_only"
    ):
        raise RuntimeError("telemetry resource-bound contract content is invalid")
    return payload


_TELEMETRY_RESOURCE_BOUNDS = _load_telemetry_resource_bounds()
MAX_CANONICAL_EVENT_BYTES = _TELEMETRY_RESOURCE_BOUNDS["canonical_event"]["max_bytes"]
EVENT_SIZE_VIOLATION_CODE = _TELEMETRY_RESOURCE_BOUNDS["canonical_event"][
    "violation_error_code"
]
# Compatibility name retained for callers that imported the former constant.
# The budget applies to the complete canonical event, not to each JSON field.
MAX_EVENT_JSON_BYTES = MAX_CANONICAL_EVENT_BYTES
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 2048
MAX_JSON_KEY_CHARS = 128
MAX_JSON_STRING_CHARS = 8192


def _canonical_json_bytes(value: Any, field_name: str) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _validate_json_value(value: dict[str, Any] | None, field_name: str) -> None:
    if value is None:
        return

    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ValueError(f"{field_name} exceeds {MAX_JSON_NODES} JSON nodes")
        if depth > MAX_JSON_DEPTH:
            raise ValueError(f"{field_name} exceeds JSON depth {MAX_JSON_DEPTH}")

        if isinstance(item, dict):
            for key, child in item.items():
                if len(key) > MAX_JSON_KEY_CHARS:
                    raise ValueError(
                        f"{field_name} contains a key longer than {MAX_JSON_KEY_CHARS} characters"
                    )
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            if len(item) > MAX_JSON_STRING_CHARS:
                raise ValueError(
                    f"{field_name} contains a string longer than {MAX_JSON_STRING_CHARS} characters"
                )
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError(f"{field_name} contains a non-finite number")

    try:
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


class TelemetryIngestEvent(TelemetryEvent):
    """forge-telemetry event with ingress-specific storage bounds."""

    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service: str = Field(min_length=1, max_length=50)
    event_type: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    severity: str = Field(default="info", min_length=1, max_length=20)
    correlation_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_json_fields(self) -> "TelemetryIngestEvent":
        _validate_json_value(self.metadata, "metadata")
        _validate_json_value(self.metrics, "metrics")
        encoded = _canonical_json_bytes(
            self.model_dump(mode="json"),
            "telemetry event",
        )
        if len(encoded) > MAX_CANONICAL_EVENT_BYTES:
            raise PydanticCustomError(
                EVENT_SIZE_VIOLATION_CODE,
                "telemetry event exceeds {max_bytes} canonical bytes",
                {"max_bytes": MAX_CANONICAL_EVENT_BYTES},
            )
        return self


class TelemetryIngestBatch(BaseModel):
    """Atomic, bounded group of generic telemetry events."""

    events: list[TelemetryIngestEvent] = Field(
        min_length=1,
        max_length=MAX_BATCH_EVENTS,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_encoded_size(self) -> "TelemetryIngestBatch":
        encoded = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > MAX_BATCH_JSON_BYTES:
            raise ValueError(
                f"telemetry batch exceeds {MAX_BATCH_JSON_BYTES} encoded bytes"
            )
        return self


class TelemetryIngestResponse(BaseModel):
    """Acknowledgement for newly inserted and idempotently replayed events."""

    schema_version: str = "forge.telemetry.ingest.v1"
    accepted: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    event_ids: list[UUID]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

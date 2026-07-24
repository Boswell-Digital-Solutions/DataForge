"""Canonical ForgeEvent.v1 HTTP and capability contracts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timedelta
from importlib.resources import files
from typing import Any, Literal
from uuid import UUID

import rfc8785
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


CONTRACT_AUTHORITY_COMMIT = "1b84d2d666d4bfaa64aaf76ca0b323c78e99f84d"
FORGE_EVENT_V1_SCHEMA_SHA256 = (
    "6050b55c8633cc66f3a63b71b56a636cf93df39680557c41a5967ee9cf40c100"
)
EVENT_DIGEST_PROFILE_SHA256 = (
    "a2efa964ab0b908ca2cbdf97fec06355aad3169414c0dcb2f3f992900b656637"
)
EXPECTED_ERRORS_PROFILE_SHA256 = (
    "4dd477babf8c5c83bc02daf2c1951778d01294f307bb50a551f7160129669dbd"
)
SINK_CAPABILITY_FIXTURE_SHA256 = (
    "0584c14eb06bf094d9703b19fced8b0fdbd2065461104ab3c1befaba28d2d286"
)
TELEMETRY_RESOURCE_BOUNDS_SHA256 = (
    "6729e46ea46544095c1e7dd8bcdb9df9eec84df1889b9e4439db6b3f998eb919"
)
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
TRACE_ID_PATTERN = re.compile(r"^(?!0{32}$)[0-9a-f]{32}$")
SPAN_ID_PATTERN = re.compile(r"^(?!0{16}$)[0-9a-f]{16}$")


def _load_contract_json(name: str, expected_sha256: str) -> dict[str, Any]:
    try:
        content = files("app.models").joinpath("contracts", name).read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"required telemetry contract is unavailable: {name}"
        ) from exc
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise RuntimeError(f"telemetry contract digest mismatch: {name}")
    return json.loads(content)


_TELEMETRY_RESOURCE_BOUNDS = _load_contract_json(
    "telemetry_resource_bounds.v1.json",
    TELEMETRY_RESOURCE_BOUNDS_SHA256,
)
MAX_CANONICAL_EVENT_BYTES = _TELEMETRY_RESOURCE_BOUNDS["canonical_event"]["max_bytes"]
EVENT_SIZE_VIOLATION_CODE = _TELEMETRY_RESOURCE_BOUNDS["canonical_event"][
    "violation_error_code"
]
_EXPECTED_ERRORS_PROFILE = _load_contract_json(
    "forge_event_expected_errors.v1.json",
    EXPECTED_ERRORS_PROFILE_SHA256,
)
INVALID_EVENT_JSON = _EXPECTED_ERRORS_PROFILE["boundary_error_codes"]["invalid_json"]
SINK_OWNED_FIELD = _EXPECTED_ERRORS_PROFILE["boundary_error_codes"][
    "producer_submitted_sink_field"
]
UNSUPPORTED_SINK_SCHEMA = _EXPECTED_ERRORS_PROFILE["shared_error_codes"][
    "unsupported_schema"
]
EVENT_SCHEMA_VIOLATION = _EXPECTED_ERRORS_PROFILE["shared_error_codes"][
    "schema_violation"
]


def forge_event_validation_error_code(errors: list[dict[str, Any]]) -> str:
    """Collapse Pydantic/FastAPI details into the admitted value-free code."""

    error_types = {str(error.get("type")) for error in errors}
    if "json_invalid" in error_types:
        return INVALID_EVENT_JSON
    if UNSUPPORTED_SINK_SCHEMA in error_types:
        return UNSUPPORTED_SINK_SCHEMA
    if EVENT_SIZE_VIOLATION_CODE in error_types:
        return EVENT_SIZE_VIOLATION_CODE
    if SINK_OWNED_FIELD in error_types:
        return SINK_OWNED_FIELD
    if any(tuple(error.get("loc", ()))[-1:] == ("received_at",) for error in errors):
        return SINK_OWNED_FIELD
    return EVENT_SCHEMA_VIOLATION


class ForgeEventV1Submission(BaseModel):
    """Producer-authored canonical event; sink-owned fields are not accepted."""

    schema_version: str
    event_id: UUID
    occurred_at: datetime
    service_name: str
    service_instance_id: str | None
    environment: str
    tenant_ref: str | None
    event_type: str
    severity: Literal["info", "warning", "error", "critical"]
    outcome: Literal[
        "ok",
        "warn",
        "fail",
        "cancelled",
        "insufficient_signal",
        "blocked",
    ]
    evidence_class: Literal["diagnostic", "operational", "audit", "security"]
    correlation_id: UUID | None
    trace_id: str | None
    span_id: str | None
    parent_span_id: str | None
    attributes: dict[str, Any]
    metrics: dict[str, Any]
    privacy_class: Literal["public", "internal", "restricted", "confidential"]
    retention_class: Literal["ephemeral", "short", "standard", "long", "legal_hold"]
    sampled: StrictBool
    sample_rate: float | None = Field(gt=0, le=1)
    sampling_reason: Literal[
        "always_on",
        "probabilistic",
        "rate_limited",
        "required_stub",
        "policy",
    ]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def schema_version_is_supported(cls, value: Any) -> Any:
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != "ForgeEvent.v1"
        ):
            raise PydanticCustomError(
                UNSUPPORTED_SINK_SCHEMA,
                "sink does not support the submitted event schema",
            )
        if "received_at" in value:
            raise PydanticCustomError(
                SINK_OWNED_FIELD,
                "producer submission contains a sink-owned field",
            )
        occurred_at = value.get("occurred_at")
        if not isinstance(occurred_at, str) or not occurred_at.endswith("Z"):
            raise ValueError("occurred_at must use the canonical UTC representation")
        return value

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("occurred_at must be timezone-aware UTC")
        return value

    @field_validator(
        "service_name",
        "service_instance_id",
        "environment",
        "tenant_ref",
        "event_type",
    )
    @classmethod
    def identifier_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and IDENTIFIER_PATTERN.fullmatch(value) is None:
            raise ValueError("identifier must use the canonical lowercase grammar")
        return value

    @field_validator("trace_id")
    @classmethod
    def trace_id_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and TRACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace_id must be a nonzero lowercase 32-hex identifier")
        return value

    @field_validator("span_id", "parent_span_id")
    @classmethod
    def span_id_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and SPAN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("span identifiers must be nonzero lowercase 16-hex values")
        return value

    @field_validator("sample_rate", mode="before")
    @classmethod
    def sample_rate_is_a_number(cls, value: Any) -> Any:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("sample_rate must be a number or null")
        return value

    @model_validator(mode="after")
    def validate_semantics_and_size(self) -> ForgeEventV1Submission:
        if self.trace_id is None and (
            self.span_id is not None or self.parent_span_id is not None
        ):
            raise ValueError("span identifiers require trace_id")
        if self.span_id is None and self.parent_span_id is not None:
            raise ValueError("parent_span_id requires span_id")
        if self.parent_span_id is not None and self.parent_span_id == self.span_id:
            raise ValueError("parent_span_id cannot equal span_id")

        if self.sampling_reason == "probabilistic":
            if self.sample_rate is None:
                raise ValueError("probabilistic sampling requires sample_rate")
        elif self.sample_rate is not None:
            raise ValueError("sample_rate is only valid for probabilistic sampling")

        admitted_reasons = (
            {"always_on", "probabilistic", "policy"}
            if self.sampled
            else {"rate_limited", "required_stub", "policy"}
        )
        if self.sampling_reason not in admitted_reasons:
            raise ValueError("sampled and sampling_reason are inconsistent")

        for name, value in self.metrics.items():
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"metric {name!r} must be a finite non-boolean number")
        try:
            canonical = canonical_submission_bytes(self)
        except (TypeError, ValueError) as exc:
            raise ValueError("event fields must be RFC 8785 JSON serializable") from exc
        if len(canonical) > MAX_CANONICAL_EVENT_BYTES:
            raise PydanticCustomError(
                EVENT_SIZE_VIOLATION_CODE,
                "telemetry event exceeds {max_bytes} canonical bytes",
                {"max_bytes": MAX_CANONICAL_EVENT_BYTES},
            )
        return self


def canonical_submission_bytes(event: ForgeEventV1Submission) -> bytes:
    """Return the admitted RFC 8785 producer projection."""

    return rfc8785.dumps(event.model_dump(mode="json"))


def event_digest(event: ForgeEventV1Submission) -> str:
    """Return the admitted content digest for one producer projection."""

    return hashlib.sha256(canonical_submission_bytes(event)).hexdigest()


class ForgeTelemetrySinkCapabilityV1(BaseModel):
    schema_version: Literal["ForgeTelemetrySinkCapability.v1"]
    storage_schema_version: Literal["forge.dataforge.telemetry.v1"]
    event_schema_versions: list[Literal["ForgeEvent.v1"]]
    event_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_digest_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonicalization: Literal["RFC8785-JCS"]
    resource_bounds_schema_version: Literal["forge.telemetry.resource_bounds.v1"]
    resource_bounds_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_canonical_event_bytes: Literal[65536]
    supported_fields: list[str]
    received_at_owner: Literal["sink"]
    content_bound_identity: Literal[True]
    identity_outcomes: list[Literal["inserted", "exact_replay", "identity_conflict"]]
    pre_v1_fallback: Literal[False]
    dual_write: Literal[False]
    write_enabled: bool

    model_config = ConfigDict(extra="forbid")


_SINK_CAPABILITY = ForgeTelemetrySinkCapabilityV1.model_validate(
    _load_contract_json(
        "forge_telemetry_sink_capability.v1.json",
        SINK_CAPABILITY_FIXTURE_SHA256,
    )
)
if (
    _SINK_CAPABILITY.event_schema_sha256 != FORGE_EVENT_V1_SCHEMA_SHA256
    or _SINK_CAPABILITY.event_digest_profile_sha256 != EVENT_DIGEST_PROFILE_SHA256
    or _SINK_CAPABILITY.resource_bounds_sha256 != TELEMETRY_RESOURCE_BOUNDS_SHA256
):
    raise RuntimeError("telemetry capability does not pin the admitted contract hashes")


def forge_telemetry_sink_capability() -> ForgeTelemetrySinkCapabilityV1:
    """Return the admitted capability with the runtime kill-switch state."""

    capability = _SINK_CAPABILITY.model_copy(deep=True)
    capability.write_enabled = forge_event_v1_write_enabled()
    return capability


def forge_event_v1_write_enabled() -> bool:
    """Fail closed unless the canonical writer is explicitly enabled."""

    return (
        os.getenv("DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED", "false").lower() == "true"
    )


class ForgeEventV1IngestResponse(BaseModel):
    schema_version: Literal["forge.dataforge.telemetry.ingest.v1"] = (
        "forge.dataforge.telemetry.ingest.v1"
    )
    event_id: UUID
    event_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    received_at: datetime
    identity_outcome: Literal["inserted", "exact_replay"]

    model_config = ConfigDict(extra="forbid")

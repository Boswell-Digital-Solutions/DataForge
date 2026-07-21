"""Strict, content-free AuthorForge analytics contract.

This is the AuthorForge-specific, fail-closed specialization of the canonical
Forge telemetry event record.  It deliberately has no free-form metadata or
metrics dictionaries: every accepted field is named, bounded, and coarse.
"""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

MAX_ENVELOPE_BYTES = 4096
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,95}$")
_PSEUDONYM_PATTERNS = {
    "installation_pseudonym": re.compile(r"^afi_[0-9a-f]{32}$"),
    "project_pseudonym": re.compile(r"^afp_[0-9a-f]{32}$"),
    "run_pseudonym": re.compile(r"^afr_[0-9a-f]{32}$"),
    "tenant_pseudonym": re.compile(r"^aft_[0-9a-f]{32}$"),
}

# Normalized key fragments that indicate content, identity, raw diagnostics, or
# an attempt to smuggle an arbitrary container through the analytics surface.
FORBIDDEN_KEY_FRAGMENTS = frozenset(
    {
        "annotation",
        "attachment",
        "audio",
        "chapter",
        "character",
        "content",
        "document",
        "email",
        "embedding",
        "evidence",
        "exceptionmessage",
        "excerpt",
        "filename",
        "filepath",
        "image",
        "lore",
        "manuscript",
        "metadata",
        "name",
        "note",
        "path",
        "prompt",
        "quotation",
        "rawlog",
        "reasoning",
        "requestbody",
        "research",
        "response",
        "scene",
        "stacktrace",
        "text",
        "title",
        "user",
        "vector",
        "worldbuilding",
    }
)


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


class AuthorForgeAnalyticsEnvelopeV1(BaseModel):
    """Approved minimized analytics only; never AuthorForge user content."""

    schema_version: Literal["AuthorForgeAnalyticsEnvelope.v1"]
    policy_version: Literal["authorforge-analytics-policy.v1"]
    event_id: UUID
    occurred_at: AwareDatetime

    product: Literal["authorforge"]
    application: Literal["desktop", "local_service", "cli"]
    build_version: str = Field(min_length=1, max_length=64)

    installation_pseudonym: str | None = Field(default=None, max_length=36)
    project_pseudonym: str | None = Field(default=None, max_length=36)
    run_pseudonym: str | None = Field(default=None, max_length=36)
    tenant_pseudonym: str | None = Field(default=None, max_length=36)

    feature_id: str | None = Field(default=None, max_length=64)
    workflow_id: str | None = Field(default=None, max_length=64)
    execution_lane: Literal["local", "cloud_model", "hybrid"]
    route_classification: Literal["local_only", "cloud_model_api"]
    content_authority: Literal["authorforge_embedded_database"]

    event_type: Literal[
        "feature_invoked",
        "workflow_completed",
        "workflow_failed",
        "model_request_completed",
        "route_selected",
        "evaluation_recorded",
        "receipt_recorded",
    ]
    action: Literal["start", "complete", "evaluate", "route", "rollback"] | None = None
    status: Literal["success", "failure", "cancelled", "partial"] | None = None
    outcome: Literal[
        "accepted",
        "rejected",
        "abstained",
        "rolled_back",
        "human_review",
    ] | None = None

    operation_count: int | None = Field(default=None, ge=0, le=1_000_000_000)
    item_count: int | None = Field(default=None, ge=0, le=1_000_000_000)
    input_token_count: int | None = Field(default=None, ge=0, le=100_000_000)
    output_token_count: int | None = Field(default=None, ge=0, le=100_000_000)
    duration_ms: int | None = Field(default=None, ge=0, le=604_800_000)
    latency_ms: int | None = Field(default=None, ge=0, le=604_800_000)
    cost_microusd: int | None = Field(default=None, ge=0, le=1_000_000_000_000)

    provider_id: Literal[
        "local", "openai", "anthropic", "google", "xai", "mistral", "cohere"
    ] | None = None
    model_id: str | None = Field(default=None, max_length=96)
    error_category: Literal[
        "authentication",
        "authorization",
        "configuration",
        "database",
        "network",
        "payload_schema",
        "rate_limit",
        "timeout",
        "upstream",
        "unknown",
    ] | None = None
    error_code: str | None = Field(default=None, max_length=64)
    review_state: Literal[
        "accepted", "rejected", "abstained", "rolled_back", "human_review"
    ] | None = None
    receipt_version: str | None = Field(default=None, max_length=64)
    evaluation_version: str | None = Field(default=None, max_length=64)

    cache_hit: bool | None = None
    offline: bool | None = None
    rollback_performed: bool | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_content_bearing_keys(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for raw_key in value:
                if raw_key in cls.model_fields:
                    continue
                key = _normalized_key(raw_key)
                if any(fragment in key for fragment in FORBIDDEN_KEY_FRAGMENTS):
                    raise ValueError("content-bearing or identity field is forbidden")
        return value

    @field_validator("build_version", "receipt_version", "evaluation_version")
    @classmethod
    def validate_version(cls, value: str | None) -> str | None:
        if value is not None and not _VERSION_RE.fullmatch(value):
            raise ValueError("version must be an opaque bounded identifier")
        return value

    @field_validator("feature_id", "workflow_id", "error_code")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is not None and not _SLUG_RE.fullmatch(value):
            raise ValueError("identifier must be a lowercase bounded slug")
        return value

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: str | None) -> str | None:
        if value is not None and not _MODEL_RE.fullmatch(value):
            raise ValueError("model identifier is not approved")
        return value

    @field_validator(*_PSEUDONYM_PATTERNS)
    @classmethod
    def validate_pseudonym(cls, value: str | None, info) -> str | None:
        if value is not None and not _PSEUDONYM_PATTERNS[info.field_name].fullmatch(value):
            raise ValueError("identifier must be a rotatable pseudonym")
        return value

    @model_validator(mode="after")
    def enforce_contract(self) -> "AuthorForgeAnalyticsEnvelopeV1":
        if self.route_classification == "local_only" and self.execution_lane != "local":
            raise ValueError("local-only routing requires the local execution lane")
        if self.route_classification == "cloud_model_api" and self.execution_lane == "local":
            raise ValueError("cloud routing requires a cloud or hybrid execution lane")
        if self.offline and self.route_classification != "local_only":
            raise ValueError("offline operation must be classified local-only")
        if self.provider_id == "local" and self.route_classification == "cloud_model_api":
            raise ValueError("local provider cannot be classified as cloud routing")
        if self.model_id is not None and self.provider_id is None:
            raise ValueError("provider_id is required when model_id is present")
        if self.error_code is not None and self.error_category is None:
            raise ValueError("error_category is required when error_code is present")
        if len(self.model_dump_json(exclude_none=True).encode("utf-8")) > MAX_ENVELOPE_BYTES:
            raise ValueError("analytics envelope exceeds the size limit")
        return self

    def canonical_metadata(self) -> dict[str, Any]:
        """Map bounded dimensions onto the existing canonical events record."""
        keys = (
            "schema_version",
            "policy_version",
            "product",
            "application",
            "build_version",
            "installation_pseudonym",
            "project_pseudonym",
            "run_pseudonym",
            "tenant_pseudonym",
            "feature_id",
            "workflow_id",
            "execution_lane",
            "route_classification",
            "content_authority",
            "action",
            "status",
            "outcome",
            "provider_id",
            "model_id",
            "error_category",
            "error_code",
            "review_state",
            "receipt_version",
            "evaluation_version",
            "cache_hit",
            "offline",
            "rollback_performed",
        )
        return {
            key: getattr(self, key)
            for key in keys
            if getattr(self, key) is not None
        }

    def canonical_metrics(self) -> dict[str, int]:
        keys = (
            "operation_count",
            "item_count",
            "input_token_count",
            "output_token_count",
            "duration_ms",
            "latency_ms",
            "cost_microusd",
        )
        return {
            key: getattr(self, key)
            for key in keys
            if getattr(self, key) is not None
        }


class AuthorForgeAnalyticsIngestResponse(BaseModel):
    event_id: UUID
    status: Literal["accepted", "duplicate"]

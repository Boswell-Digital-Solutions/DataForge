"""Strict versioned contracts for the internal cloud-image state boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


JobStatus = Literal[
    "requested",
    "accepted",
    "queued",
    "planning",
    "generating_candidates",
    "capturing_artifacts",
    "quality_reviewing",
    "pending_forgeimages_validation",
    "replacement_required",
    "generating_replacements",
    "asset_validated",
    "fulfilled",
    "partial",
    "failed",
    "blocked",
    "expired",
    "cancelled",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class CloudImageJobRecordV1(StrictModel):
    schema_version: Literal["cloud_image_job_record.v1"]
    job_id: str = Field(min_length=1, max_length=96)
    request_id: str = Field(min_length=1, max_length=96)
    correlation_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    source_service: str = Field(min_length=1, max_length=128)
    caller_identity: str = Field(min_length=1, max_length=256)
    app_id: str = Field(min_length=2, max_length=64)
    use_case: str = Field(min_length=2, max_length=96)
    provider_override: str | None = Field(default=None, min_length=1, max_length=64)
    policy_block_code: str | None = Field(default=None, min_length=1, max_length=128)
    status: JobStatus
    requested_count: int = Field(ge=1, le=12)
    accepted_final_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    replacement_round: int = Field(ge=0)
    max_replacement_rounds: int = Field(ge=0)
    max_total_candidates: int = Field(ge=1)
    max_cost_usd: Decimal = Field(ge=0)
    fulfillment_limits_exhausted: bool
    deadline_at: datetime
    created_at: datetime
    updated_at: datetime
    terminal_at: datetime | None = None

    @field_validator("deadline_at", "created_at", "updated_at", "terminal_at")
    @classmethod
    def _timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("job timestamps must include a timezone")
        return None if value is None else value.astimezone(UTC)

    @model_validator(mode="after")
    def _counts_are_bounded(self) -> "CloudImageJobRecordV1":
        if self.accepted_final_count > self.requested_count:
            raise ValueError("accepted_final_count cannot exceed requested_count")
        if self.max_total_candidates < self.requested_count:
            raise ValueError("max_total_candidates cannot be less than requested_count")
        return self


class ProtectedRequestEnvelopeV1(StrictModel):
    """Opaque AES-GCM envelope. DataForge never receives plaintext request fields."""

    schema_version: Literal["cloud_image_protected_request.v1"]
    algorithm: Literal["A256GCM"]
    key_ref: str = Field(min_length=1, max_length=256)
    nonce_b64: str = Field(min_length=16, max_length=64)
    aad_b64: str = Field(min_length=1, max_length=512)
    ciphertext: str = Field(min_length=24, max_length=256_000)
    ciphertext_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_request_fingerprint: str = Field(
        pattern=r"^hmac-sha256:[0-9a-f]{64}$"
    )
    created_at: datetime
    retention_until: datetime

    @field_validator("created_at", "retention_until")
    @classmethod
    def _envelope_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("envelope timestamps must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _valid_retention_window(self) -> "ProtectedRequestEnvelopeV1":
        if self.retention_until <= self.created_at:
            raise ValueError("retention_until must follow created_at")
        return self


_ALLOWED_DETAIL_KEYS = frozenset(
    {
        "code",
        "from_status",
        "operation_id",
        "provider_id",
        "reason_code",
        "source_job_id",
        "to_status",
    }
)


class CloudImageAuditEventV1(StrictModel):
    schema_version: Literal["cloud_image_audit_event.v1"] = (
        "cloud_image_audit_event.v1"
    )
    event_id: str = Field(min_length=1, max_length=96)
    event_type: str = Field(min_length=1, max_length=128)
    caller_identity: str = Field(min_length=1, max_length=256)
    app_id: str = Field(min_length=2, max_length=64)
    correlation_id: str = Field(min_length=1, max_length=256)
    job_id: str = Field(min_length=1, max_length=96)
    details: dict[str, str] = Field(default_factory=dict)
    created_at: datetime

    @field_validator("details")
    @classmethod
    def _details_are_value_bounded(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = set(value) - _ALLOWED_DETAIL_KEYS
        if unknown:
            raise ValueError(f"unsupported event detail keys: {sorted(unknown)}")
        if any(len(item) > 256 for item in value.values()):
            raise ValueError("event detail values are limited to 256 characters")
        return value

    @field_validator("created_at")
    @classmethod
    def _event_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event created_at must include a timezone")
        return value.astimezone(UTC)


class CloudImageCreateRequestV1(StrictModel):
    schema_version: Literal["cloud_image_state_create.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    job: CloudImageJobRecordV1
    protected_request: ProtectedRequestEnvelopeV1
    events: list[CloudImageAuditEventV1] = Field(min_length=1, max_length=4)
    retry_source_job_id: str | None = Field(default=None, min_length=1, max_length=96)

    @model_validator(mode="after")
    def _consistent_create(self) -> "CloudImageCreateRequestV1":
        if self.operation_fingerprint != self.protected_request.semantic_request_fingerprint:
            raise ValueError("operation fingerprint must match protected request fingerprint")
        if any(event.job_id != self.job.job_id for event in self.events):
            raise ValueError("all events must refer to the created job")
        return self


class CloudImageTransitionRequestV1(StrictModel):
    schema_version: Literal["cloud_image_state_transition.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    expected_row_version: int = Field(ge=1)
    expected_status: JobStatus
    updated_job: CloudImageJobRecordV1
    event: CloudImageAuditEventV1


class CloudImageAppendEventRequestV1(StrictModel):
    schema_version: Literal["cloud_image_state_append_event.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    expected_row_version: int = Field(ge=1)
    event: CloudImageAuditEventV1


class CloudImageJobStateResponseV1(StrictModel):
    schema_version: Literal["cloud_image_job_state.v1"] = "cloud_image_job_state.v1"
    job: CloudImageJobRecordV1
    row_version: int = Field(ge=1)
    created: bool = False
    replayed: bool = False


class CloudImageRetrySourceResponseV1(StrictModel):
    schema_version: Literal["cloud_image_retry_source.v1"] = (
        "cloud_image_retry_source.v1"
    )
    job: CloudImageJobRecordV1
    row_version: int = Field(ge=1)
    protected_request: ProtectedRequestEnvelopeV1


class CloudImageEventListResponseV1(StrictModel):
    schema_version: Literal["cloud_image_event_list.v1"] = "cloud_image_event_list.v1"
    job_id: str
    events: list[CloudImageAuditEventV1]

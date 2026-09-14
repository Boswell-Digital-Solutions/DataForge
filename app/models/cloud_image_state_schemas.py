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
    semantic_request_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
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
        "attempt_id",
        "code",
        "fencing_token",
        "from_status",
        "operation_id",
        "outbox_id",
        "provider_id",
        "reason_code",
        "retry_class",
        "source_job_id",
        "stage",
        "to_status",
    }
)


class CloudImageAuditEventV1(StrictModel):
    schema_version: Literal["cloud_image_audit_event.v1"] = "cloud_image_audit_event.v1"
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
        if (
            self.operation_fingerprint
            != self.protected_request.semantic_request_fingerprint
        ):
            raise ValueError(
                "operation fingerprint must match protected request fingerprint"
            )
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


WorkerStage = Literal[
    "planning",
    "generation",
    "capture",
    "quality_review",
    "forgeimages_validation",
    "replacement",
    "terminalization",
]
RetryClass = Literal["none", "retryable", "permanent", "unknown_outcome"]
AttemptStatus = Literal[
    "started",
    "succeeded",
    "retryable_failure",
    "permanent_failure",
    "reconciliation_required",
]


class CloudImageLeaseGuardV1(StrictModel):
    worker_id: str = Field(min_length=1, max_length=128)
    stage: WorkerStage
    fencing_token: int = Field(ge=1)


class CloudImageLeaseOperationV1(StrictModel):
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")


class CloudImageLeaseClaimRequestV1(CloudImageLeaseOperationV1):
    schema_version: Literal["cloud_image_lease_claim.v1"]
    worker_id: str = Field(min_length=1, max_length=128)
    stage: WorkerStage
    lease_seconds: int = Field(ge=5, le=300)


class CloudImageLeaseRenewRequestV1(CloudImageLeaseOperationV1):
    schema_version: Literal["cloud_image_lease_renew.v1"]
    lease: CloudImageLeaseGuardV1
    lease_seconds: int = Field(ge=5, le=300)


class CloudImageLeaseReleaseRequestV1(CloudImageLeaseOperationV1):
    schema_version: Literal["cloud_image_lease_release.v1"]
    lease: CloudImageLeaseGuardV1
    reason_code: str = Field(min_length=1, max_length=128)


class CloudImageLeaseExpireRequestV1(CloudImageLeaseOperationV1):
    schema_version: Literal["cloud_image_lease_expire.v1"]
    lease: CloudImageLeaseGuardV1
    reason_code: str = Field(min_length=1, max_length=128)


class CloudImageLeaseResponseV1(StrictModel):
    schema_version: Literal["cloud_image_lease.v1"] = "cloud_image_lease.v1"
    job_id: str = Field(min_length=1, max_length=96)
    worker_id: str = Field(min_length=1, max_length=128)
    stage: WorkerStage
    fencing_token: int = Field(ge=1)
    acquired_at: datetime
    renewed_at: datetime
    expires_at: datetime
    released_at: datetime | None = None
    release_reason: str | None = Field(default=None, min_length=1, max_length=128)
    replayed: bool = False

    @field_validator("acquired_at", "renewed_at", "expires_at", "released_at")
    @classmethod
    def _lease_timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("lease timestamps must include a timezone")
        return None if value is None else value.astimezone(UTC)


class CloudImageWorkerTransitionRequestV1(StrictModel):
    schema_version: Literal["cloud_image_worker_transition.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    expected_row_version: int = Field(ge=1)
    expected_status: JobStatus
    lease: CloudImageLeaseGuardV1
    attempt_id: str = Field(min_length=1, max_length=128)
    updated_job: CloudImageJobRecordV1
    event: CloudImageAuditEventV1


class CloudImageStageAttemptStartRequestV1(StrictModel):
    schema_version: Literal["cloud_image_stage_attempt_start.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    attempt_id: str = Field(min_length=1, max_length=128)
    stage: WorkerStage
    attempt_number: int = Field(ge=1)
    lease: CloudImageLeaseGuardV1


class CloudImageStageAttemptCompleteRequestV1(StrictModel):
    schema_version: Literal["cloud_image_stage_attempt_complete.v1"]
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")
    lease: CloudImageLeaseGuardV1
    status: AttemptStatus
    retry_class: RetryClass
    failure_code: str | None = Field(default=None, min_length=1, max_length=128)
    result_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    next_attempt_at: datetime | None = None

    @field_validator("next_attempt_at")
    @classmethod
    def _attempt_timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("next_attempt_at must include a timezone")
        return None if value is None else value.astimezone(UTC)

    @model_validator(mode="after")
    def _outcome_is_consistent(self) -> "CloudImageStageAttemptCompleteRequestV1":
        expected_retry = {
            "succeeded": "none",
            "retryable_failure": "retryable",
            "permanent_failure": "permanent",
            "reconciliation_required": "unknown_outcome",
            "started": "none",
        }[self.status]
        if self.retry_class != expected_retry:
            raise ValueError("attempt status and retry_class disagree")
        if self.status == "retryable_failure" and self.next_attempt_at is None:
            raise ValueError("retryable failure requires next_attempt_at")
        if self.status == "succeeded" and self.result_digest is None:
            raise ValueError("succeeded attempt requires result_digest")
        if self.status not in {"started", "succeeded"} and self.failure_code is None:
            raise ValueError("failed or unknown attempt outcome requires failure_code")
        if self.status != "retryable_failure" and self.next_attempt_at is not None:
            raise ValueError("only retryable failure may schedule a next attempt")
        return self


class CloudImageStageAttemptV1(StrictModel):
    schema_version: Literal["cloud_image_stage_attempt.v1"] = (
        "cloud_image_stage_attempt.v1"
    )
    attempt_id: str
    operation_id: str
    operation_fingerprint: str
    job_id: str
    stage: WorkerStage
    attempt_number: int = Field(ge=1)
    fencing_token: int = Field(ge=1)
    status: AttemptStatus
    retry_class: RetryClass
    failure_code: str | None = None
    result_digest: str | None = None
    next_attempt_at: datetime | None = None
    started_at: datetime
    completed_at: datetime | None = None
    transitioned_to_status: JobStatus | None = None
    transitioned_row_version: int | None = Field(default=None, ge=1)
    transitioned_at: datetime | None = None
    replayed: bool = False

    @field_validator("next_attempt_at", "started_at", "completed_at", "transitioned_at")
    @classmethod
    def _record_timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("attempt timestamps must include a timezone")
        return None if value is None else value.astimezone(UTC)


class CloudImageStageAttemptListV1(StrictModel):
    schema_version: Literal["cloud_image_stage_attempt_list.v1"] = (
        "cloud_image_stage_attempt_list.v1"
    )
    job_id: str
    attempts: list[CloudImageStageAttemptV1]


class CloudImageOutboxOperationV1(StrictModel):
    operation_id: str = Field(min_length=1, max_length=128)
    operation_fingerprint: str = Field(pattern=r"^hmac-sha256:[0-9a-f]{64}$")


class CloudImageOutboxClaimRequestV1(CloudImageOutboxOperationV1):
    schema_version: Literal["cloud_image_outbox_claim.v1"]
    dispatcher_id: str = Field(min_length=1, max_length=128)
    max_items: int = Field(ge=1, le=100)
    lease_seconds: int = Field(ge=5, le=300)


class CloudImageOutboxSettleRequestV1(CloudImageOutboxOperationV1):
    schema_version: Literal["cloud_image_outbox_settle.v1"]
    dispatcher_id: str = Field(min_length=1, max_length=128)
    claim_token: int = Field(ge=1)
    outcome: Literal["published", "retry", "dead_letter"]
    error_code: str | None = Field(default=None, min_length=1, max_length=128)
    retry_after_seconds: int | None = Field(default=None, ge=1, le=86_400)

    @model_validator(mode="after")
    def _settlement_is_consistent(self) -> "CloudImageOutboxSettleRequestV1":
        if self.outcome == "retry" and self.retry_after_seconds is None:
            raise ValueError("retry settlement requires retry_after_seconds")
        if self.outcome != "published" and self.error_code is None:
            raise ValueError("failed settlement requires error_code")
        return self


class CloudImageOutboxItemV1(StrictModel):
    schema_version: Literal["cloud_image_outbox_item.v1"] = "cloud_image_outbox_item.v1"
    outbox_id: str
    event_id: str
    aggregate_id: str
    event_type: str
    payload: dict[str, object]
    created_at: datetime
    published_at: datetime | None = None
    delivery_attempts: int = Field(ge=0)
    next_attempt_at: datetime
    claim_owner: str | None = None
    claim_token: int = Field(ge=0)
    claim_expires_at: datetime | None = None
    last_error_code: str | None = None
    dead_lettered_at: datetime | None = None
    replayed: bool = False

    @field_validator(
        "created_at",
        "published_at",
        "next_attempt_at",
        "claim_expires_at",
        "dead_lettered_at",
    )
    @classmethod
    def _outbox_timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("outbox timestamps must include a timezone")
        return None if value is None else value.astimezone(UTC)


class CloudImageOutboxClaimResponseV1(StrictModel):
    schema_version: Literal["cloud_image_outbox_claim_batch.v1"] = (
        "cloud_image_outbox_claim_batch.v1"
    )
    dispatcher_id: str
    items: list[CloudImageOutboxItemV1]
    replayed: bool = False

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceDomain(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


class DecisionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


class AuthorizationClass(StrEnum):
    OPERATIONAL = "operational"
    SENSITIVE_RUNTIME = "sensitive_runtime"
    IMPLEMENTATION_ONLY = "implementation_only"
    SECOND_REVIEW_REQUIRED = "second_review_required"


class ExecutionClass(StrEnum):
    LOCAL_RUNTIME_ACTION = "local_runtime_action"


class HandoffStatus(StrEnum):
    HANDOFF_ELIGIBLE = "handoff_eligible"
    HANDOFF_BLOCKED = "handoff_blocked"
    HANDOFF_NOT_REQUIRED = "handoff_not_required"


class ExecutionRequestClass(StrEnum):
    APPROVED_RECOMMENDATION_HANDOFF = "approved_recommendation_handoff"


class TargetLane(StrEnum):
    LOCAL_RUNTIME_ACTION = "local_runtime_action"


class TargetSubsystem(StrEnum):
    FORGE_LOCAL_RUNTIME = "forge_local_runtime"


class RiskClass(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ExecutionRequestStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ROLLED_BACK = "rolled_back"
    DEAD_LETTERED = "dead_lettered"


class ExecutionState(StrEnum):
    QUEUED = "queued"
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ROLLED_BACK = "rolled_back"
    VERIFICATION_PENDING = "verification_pending"
    DEAD_LETTERED = "dead_lettered"


class FailureReasonClass(StrEnum):
    NONE = "none"
    POLICY_BLOCKED = "policy_blocked"
    INVALID_REQUEST = "invalid_request"
    SUBSYSTEM_UNAVAILABLE = "subsystem_unavailable"
    RUNTIME_FAILURE = "runtime_failure"
    TIMEOUT = "timeout"
    VERIFICATION_BLOCKED = "verification_blocked"
    UNKNOWN = "unknown"


class VerificationObservedOutcome(StrEnum):
    VERIFIED_SUCCESS = "verified_success"
    VERIFIED_PARTIAL = "verified_partial"
    VERIFIED_FAILURE = "verified_failure"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ProvenanceFields(BaseModel):
    trace_id: str
    root_decision_artifact_id: str
    parent_artifact_id: str | None = None
    lineage_step: int = Field(ge=0)
    emitting_subsystem: str


class LocalRecommendationApprovalDecisionV1(ProvenanceFields):
    decision_artifact_id: str
    candidate_id: str
    recommendation_id: str
    decision_type: DecisionType
    operator_note: str | None = None
    approved_at: datetime
    approved_by: str | None = None
    source_domain: SourceDomain
    authorization_class: AuthorizationClass
    execution_required: bool
    execution_class: ExecutionClass | None = None
    status: HandoffStatus


class LocalRecommendationExecutionRequestV1(ProvenanceFields):
    execution_request_id: str
    candidate_id: str
    decision_artifact_id: str
    request_class: ExecutionRequestClass = (
        ExecutionRequestClass.APPROVED_RECOMMENDATION_HANDOFF
    )
    target_subsystem: TargetSubsystem
    target_lane: TargetLane = TargetLane.LOCAL_RUNTIME_ACTION
    target_scope: str
    requested_action: str
    bounded_parameters: dict[str, Any] = Field(default_factory=dict)
    risk_class: RiskClass
    rollback_required: bool = False
    idempotency_key: str
    requested_at: datetime
    request_status: ExecutionRequestStatus = ExecutionRequestStatus.CREATED


class LocalRecommendationExecutionStatusV1(ProvenanceFields):
    execution_status_id: str
    execution_request_id: str
    execution_state: ExecutionState
    accepted_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    timed_out_at: datetime | None = None
    status_summary: str | None = None
    failure_reason_class: FailureReasonClass = FailureReasonClass.NONE
    operator_visible_notes: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    updated_at: datetime


class LocalRecommendationVerificationResultV1(ProvenanceFields):
    verification_artifact_id: str
    execution_request_id: str
    candidate_id: str
    verification_scope: str
    expected_gain: str
    observed_outcome: VerificationObservedOutcome
    regression_detected: bool = False
    rollback_recommended: bool = False
    verification_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    verified_at: datetime
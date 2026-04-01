from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.runtime_promotion.execution_handoff.contracts import (
    LocalRecommendationExecutionRequestV1,
    LocalRecommendationExecutionStatusV1,
    LocalRecommendationVerificationResultV1,
)


class RuntimePromotionCandidateDecisionEntry(BaseModel):
    candidate_id: str
    prior_status: str
    new_status: str
    operator_note: Optional[str] = None
    operator_identity: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuntimePromotionExecutionStatusSummary(BaseModel):
    execution_request_id: str
    latest_execution_state: str | None
    latest_status_summary: str | None
    latest_failure_reason_class: str | None
    last_status_recorded_at: datetime | None


class RuntimePromotionVerificationSummary(BaseModel):
    execution_request_id: str
    observed_outcome: str | None
    verification_summary: str | None
    regression_detected: bool
    rollback_recommended: bool
    verified_at: datetime | None


class RuntimePromotionExecutionHandoffDetail(BaseModel):
    handoff_exists: bool
    handoff_status: str
    decision_artifact_id: str
    trace_id: str
    root_decision_artifact_id: str
    parent_artifact_id: str | None = None
    lineage_step: int
    emitting_subsystem: str
    execution_request: LocalRecommendationExecutionRequestV1 | None = None
    latest_execution_status: LocalRecommendationExecutionStatusV1 | None = None
    latest_execution_summary: RuntimePromotionExecutionStatusSummary
    latest_verification: LocalRecommendationVerificationResultV1 | None = None
    latest_verification_summary: RuntimePromotionVerificationSummary


class RuntimePromotionCandidateSummary(BaseModel):
    candidate_id: str
    receipt_id: str
    candidate_type: str
    source_envelope_type: Literal["local_failure_pattern"]
    service: str
    fleet_member_id: str
    issue_class: str
    severity: str
    title: str
    summary: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuntimePromotionCandidateDetail(RuntimePromotionCandidateSummary):
    evidence: dict
    source_payload: dict
    decision_history: list[RuntimePromotionCandidateDecisionEntry] = []
    execution_handoff: RuntimePromotionExecutionHandoffDetail | None = None


class RuntimePromotionCandidateActionRequest(BaseModel):
    reason: Optional[str] = None
    operator_identity: Optional[str] = None


class RuntimePromotionCandidateActionResponse(BaseModel):
    ok: bool
    candidate_id: str
    status: str
    message: str

"""Pydantic schemas for ForgeAgents run persistence API.

These schemas define the request/response models for the /api/v1/forge-run
endpoints that handle execution persistence from ForgeAgents.
"""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Vocabulary Types (mirrored from ForgeAgents vocab.py)
# =============================================================================

FinalStatusType = Literal["pass", "fail", "aborted", "system_fault"]

FailReasonType = Literal[
    "quality_reject",
    "constraint_violation",
    "policy_violation",
    "max_retries_exceeded",
    "node_failure",
    "validation_error",
    "timeout",
    "dependency_failure",
]

AbortKindType = Literal["graceful", "hard"]

AbortReasonType = Literal[
    "operator_cancel",
    "safety_timeout",
    "max_steps",
    "policy_violation",
    "resource_limit",
    "external_signal",
]


# =============================================================================
# Request Schemas
# =============================================================================

class ExecutionIndexCreate(BaseModel):
    """Schema for execution_index record in persist request."""

    # Primary identifiers
    run_id: str = Field(..., max_length=64)
    trace_id: str = Field(..., max_length=64)
    workflow_id: str = Field(..., max_length=64)
    session_id: str = Field(..., max_length=64)

    # Repository context
    repo_id: str = Field(..., max_length=255)
    repo_sha: str = Field(..., max_length=64)
    branch: str = Field(..., max_length=255)

    # Execution mode
    mode: str = Field(..., max_length=20)
    invoker: str | None = Field(None, max_length=100)

    # Terminal status
    final_status: FinalStatusType

    # Conditional metadata
    fail_reason: FailReasonType | None = None
    abort_kind: AbortKindType | None = None
    abort_reason: AbortReasonType | None = None

    # Quality metrics
    promotion_ready: bool = False
    confidence_floor: float = Field(0.0, ge=0.0, le=1.0)

    # Evidence references
    evidence_hash: str | None = Field(None, max_length=71)
    artifact_bundle_pointer: str | None = Field(None, max_length=1024)

    # Timing
    total_duration_ms: int | None = None
    node_count: int | None = None
    attempt_count: int = 1

    # Timestamps
    created_at: str | None = None
    completed_at: str | None = None

    # Extensible metadata
    metadata: dict[str, Any] | None = None

    @field_validator("evidence_hash")
    @classmethod
    def validate_evidence_hash(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.startswith("sha256:"):
                raise ValueError("evidence_hash must start with 'sha256:'")
            if len(v) != 71:
                raise ValueError("evidence_hash must be 71 characters")
        return v


class RunEvidenceCreate(BaseModel):
    """Schema for run_evidence record in persist request."""

    run_id: str = Field(..., max_length=64)
    evidence_version: str = Field("RunEvidence.v1", max_length=20)
    evidence_hash: str = Field(..., max_length=71)
    evidence: dict[str, Any]

    @field_validator("evidence_hash")
    @classmethod
    def validate_evidence_hash(cls, v: str) -> str:
        if not v.startswith("sha256:"):
            raise ValueError("evidence_hash must start with 'sha256:'")
        if len(v) != 71:
            raise ValueError("evidence_hash must be 71 characters")
        return v


class PersistRunRequest(BaseModel):
    """Request to persist a run execution to DataForge.

    Called by ForgeAgents on run completion. Writes to both
    execution_index (for fast queries) and run_evidence (for full document).
    """

    execution_index: ExecutionIndexCreate
    run_evidence: RunEvidenceCreate | None = None  # Optional for system_fault


# =============================================================================
# Response Schemas
# =============================================================================

class PersistRunResponse(BaseModel):
    """Response from persist run endpoint."""

    status: Literal["created", "exists"]
    run_id: str
    message: str


class ExecutionIndexResponse(BaseModel):
    """Response schema for execution index record."""

    run_id: str
    trace_id: str
    workflow_id: str
    session_id: str
    repo_id: str
    repo_sha: str
    branch: str
    mode: str
    invoker: str | None
    final_status: str
    fail_reason: str | None
    abort_kind: str | None
    abort_reason: str | None
    promotion_ready: bool
    confidence_floor: float
    evidence_hash: str | None
    artifact_bundle_pointer: str | None
    total_duration_ms: int | None
    node_count: int | None
    attempt_count: int
    created_at: datetime | None
    completed_at: datetime | None
    # Map 'run_metadata' from DB model to 'metadata' in API response
    metadata: dict[str, Any] | None = Field(None, validation_alias="run_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class RunEvidenceResponse(BaseModel):
    """Response schema for run evidence record."""

    run_id: str
    evidence_version: str
    evidence_hash: str
    evidence: dict[str, Any]
    created_at: datetime | None

    class Config:
        from_attributes = True


class RunDetailResponse(BaseModel):
    """Full run details including index and evidence."""

    index: ExecutionIndexResponse
    evidence: RunEvidenceResponse | None


class ListRunsResponse(BaseModel):
    """Paginated list of runs."""

    runs: list[ExecutionIndexResponse]
    total: int
    page: int
    page_size: int
    has_more: bool

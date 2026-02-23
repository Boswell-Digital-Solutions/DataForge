"""Pydantic schemas for Agentic Reasoning API endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ExecutionOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class NominationStatus(str, Enum):
    CANDIDATE = "candidate"
    NOMINATED = "nominated"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REGISTERED = "registered"
    REJECTED = "rejected"


class KnowledgeType(str, Enum):
    CONTEXT_DISCOVERY = "context_discovery"
    ERROR_SIGNAL = "error_signal"
    DEPENDENCY_FINDING = "dependency_finding"
    SCOPE_OVERLAP = "scope_overlap"


# ============================================================================
# Experience Store Schemas
# ============================================================================


class ExperienceCreate(BaseModel):
    """Schema for creating an execution experience record."""

    run_id: UUID
    agent_id: UUID
    agent_archetype: str = Field(..., min_length=1, max_length=50)
    task_embedding: list[float] = Field(..., min_length=1)
    target_scope: dict[str, Any]
    execution_summary: str = Field(..., min_length=1)
    outcome: ExecutionOutcome
    gate_results_snapshot: dict[str, Any] | None = None
    tool_sequence: list[str] | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class ExperienceResponse(BaseModel):
    """Schema for experience record response."""

    experience_id: UUID
    run_id: UUID
    agent_id: UUID
    agent_archetype: str
    target_scope: dict[str, Any]
    execution_summary: str
    outcome: str
    gate_results_snapshot: dict[str, Any] | None
    tool_sequence: list[str] | None
    duration_ms: int | None
    cost_usd: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class ExperienceSearchRequest(BaseModel):
    """Schema for semantic experience search."""

    query_embedding: list[float] = Field(..., min_length=1)
    agent_archetype: str | None = None
    outcome: ExecutionOutcome | None = None
    min_similarity: float = Field(default=0.65, ge=0.0, le=1.0)
    limit: int = Field(default=5, ge=1, le=50)


class ExperienceSearchResult(BaseModel):
    """Schema for a single search result with similarity score."""

    experience_id: UUID
    run_id: UUID
    agent_id: UUID
    agent_archetype: str
    target_scope: dict[str, Any]
    execution_summary: str
    outcome: str
    gate_results_snapshot: dict[str, Any] | None
    tool_sequence: list[str] | None
    duration_ms: int | None
    cost_usd: float | None
    created_at: datetime
    similarity: float

    class Config:
        from_attributes = True


# ============================================================================
# Skill Nomination Schemas
# ============================================================================


class NominationCreate(BaseModel):
    """Schema for creating a skill nomination."""

    candidate_name: str = Field(..., min_length=1, max_length=200)
    tool_sequence: list[str] = Field(..., min_length=1)
    parameter_schemas: dict[str, Any] | None = None
    evidence_run_ids: list[UUID] = Field(..., min_length=1)
    proposed_capability_category: str | None = Field(default=None, pattern=r"^[A-G]$")
    proposed_capability_id: str | None = Field(default=None, max_length=200)


class NominationResponse(BaseModel):
    """Schema for nomination record response."""

    nomination_id: UUID
    candidate_name: str
    tool_sequence: list[str]
    parameter_schemas: dict[str, Any] | None
    evidence_run_ids: list[UUID]
    proposed_capability_category: str | None
    proposed_capability_id: str | None
    status: str
    rejection_reason: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NominationStatusUpdate(BaseModel):
    """Schema for updating nomination status."""

    status: NominationStatus
    reviewed_by: str | None = None
    rejection_reason: str | None = None


# ============================================================================
# Governed Broadcast Schemas
# ============================================================================


class BroadcastCreate(BaseModel):
    """Schema for creating a governed broadcast."""

    source_agent_id: UUID
    source_run_id: UUID
    target_scope: dict[str, Any]
    knowledge_type: KnowledgeType
    payload: dict[str, Any]
    provenance: dict[str, Any] | None = None
    trust_metadata: dict[str, Any] | None = None


class BroadcastResponse(BaseModel):
    """Schema for broadcast record response."""

    broadcast_id: UUID
    source_agent_id: UUID
    source_run_id: UUID
    target_scope: dict[str, Any]
    knowledge_type: str
    payload: dict[str, Any]
    provenance: dict[str, Any] | None
    trust_metadata: dict[str, Any] | None
    delivered_to: list[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

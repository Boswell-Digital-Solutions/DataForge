"""
Smithy Planning Session Schemas

Pydantic schemas for Planning session API requests and responses.
Matches the TypeScript types in forge-smithy/src/lib/types/agents.ts.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class SessionStatus(str, Enum):
    """Planning session lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PAORTStage(str, Enum):
    """PAORT cycle stages."""
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    TRANSITION = "transition"


# ═══════════════════════════════════════════════════════════════════════════════
# Request Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningSessionCreate(BaseModel):
    """Create a new planning session."""
    user_id: Optional[str] = None
    forgeagents_session_id: Optional[str] = None
    request_title: str = Field(..., max_length=200)
    request_description: str = Field(..., max_length=5000)
    request_repo_url: Optional[str] = Field(None, max_length=500)
    request_repo_commit: Optional[str] = Field(None, max_length=40)
    normalized_prompt: Optional[str] = None


class PlanningSessionUpdate(BaseModel):
    """Update planning session status and stage outputs."""
    status: Optional[SessionStatus] = None
    current_stage: Optional[PAORTStage] = None
    forgeagents_session_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stage_plan_output: Optional[dict] = None
    stage_act_output: Optional[dict] = None
    stage_observe_output: Optional[dict] = None
    stage_reflect_output: Optional[dict] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None


class PlanningStepCreate(BaseModel):
    """Create a planning step."""
    step_order: int = Field(..., ge=1)
    title: str = Field(..., max_length=300)
    description: str
    estimated_effort: Optional[str] = Field(None, max_length=100)
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class PlanningDeliverableCreate(BaseModel):
    """Create a planning deliverable with steps."""
    plan_title: str = Field(..., max_length=300)
    plan_overview: str
    plan_estimated_effort: Optional[str] = Field(None, max_length=100)
    plan_risks: list[str] = Field(default_factory=list)
    execution_prompt: str
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None
    tone_violations: Optional[int] = 0
    steps: list[PlanningStepCreate] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Response Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningStep(BaseModel):
    """Planning step response."""
    id: str
    step_order: int
    title: str
    description: str
    estimated_effort: Optional[str] = None
    dependencies: list[str] = []
    acceptance_criteria: list[str] = []

    model_config = ConfigDict(from_attributes=True)



class PlanningDeliverable(BaseModel):
    """Planning deliverable response."""
    id: str
    session_id: str
    plan_title: str
    plan_overview: str
    plan_estimated_effort: Optional[str] = None
    plan_risks: list[str] = []
    execution_prompt: str
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None
    tone_violations: Optional[int] = 0
    created_at: datetime
    steps: list[PlanningStep] = []

    model_config = ConfigDict(from_attributes=True)



class PlanningSession(BaseModel):
    """Full planning session response."""
    id: str
    user_id: Optional[str] = None
    forgeagents_session_id: Optional[str] = None
    status: SessionStatus
    current_stage: Optional[PAORTStage] = None
    request_title: str
    request_description: str
    request_repo_url: Optional[str] = None
    request_repo_commit: Optional[str] = None
    normalized_prompt: Optional[str] = None
    stage_plan_output: Optional[dict] = None
    stage_act_output: Optional[dict] = None
    stage_observe_output: Optional[dict] = None
    stage_reflect_output: Optional[dict] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deliverable: Optional[PlanningDeliverable] = None

    model_config = ConfigDict(from_attributes=True)



class PlanningSessionSummary(BaseModel):
    """Lightweight session summary for lists."""
    id: str
    user_id: Optional[str] = None
    status: SessionStatus
    request_title: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    has_deliverable: bool = False

    model_config = ConfigDict(from_attributes=True)



# ═══════════════════════════════════════════════════════════════════════════════
# Operational Memory Schema
# ═══════════════════════════════════════════════════════════════════════════════

class OperationalMemorySummary(BaseModel):
    """Summary of recent planning sessions for operational memory context.

    Used by forge-smithy to provide continuity across planning sessions.
    """
    recent_sessions: list[PlanningSessionSummary]
    total_completed: int
    total_failed: int
    common_themes: list[str] = []
    last_session_at: Optional[datetime] = None

"""
Sentinel Agent — Pydantic schemas for API request/response.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ── Enums ────────────────────────────────────────────────────

class SweepType(str, Enum):
    LIGHT = "light"
    DEEP = "deep"

class SweepStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class OverallStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class SweepTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    ANOMALY = "anomaly"

class HealingTier(str, Enum):
    A = "A"  # autonomous
    B = "B"  # supervised
    C = "C"  # escalation

class HealingOutcome(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATED = "escalated"
    SKIPPED = "skipped"


# ── Dimension result (shared) ────────────────────────────────

class DimensionResult(BaseModel):
    """Result from a single diagnostic dimension."""
    dimension: str = Field(..., description="D1-D6 identifier")
    dimension_name: str = Field(..., description="Human-readable dimension name")
    status: OverallStatus
    details: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


# ── Sweep schemas ────────────────────────────────────────────

class SweepCreate(BaseModel):
    sweep_type: SweepType
    trigger: SweepTrigger = SweepTrigger.SCHEDULED

class SweepUpdate(BaseModel):
    status: SweepStatus | None = None
    findings: list[DimensionResult] | None = None
    overall_status: OverallStatus | None = None
    duration_ms: int | None = None
    error: str | None = None
    completed_at: datetime | None = None

class SweepResponse(BaseModel):
    id: UUID
    sweep_type: str
    status: str
    dimensions_checked: list[str]
    findings: list[dict[str, Any]]
    overall_status: str
    trigger: str
    duration_ms: int | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SweepListResponse(BaseModel):
    items: list[SweepResponse]
    total: int


# ── Healing event schemas ────────────────────────────────────

class HealingEventCreate(BaseModel):
    sweep_id: UUID
    playbook: str
    tier: HealingTier
    action: str
    target_service: str | None = None
    governed: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

class HealingEventUpdate(BaseModel):
    outcome: HealingOutcome | None = None
    approval_id: str | None = None
    duration_ms: int | None = None
    completed_at: datetime | None = None
    details: dict[str, Any] | None = None

class HealingEventResponse(BaseModel):
    id: UUID
    sweep_id: UUID
    playbook: str
    tier: str
    action: str
    target_service: str | None
    outcome: str
    governed: bool
    approval_id: str | None
    details: dict[str, Any]
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class HealingEventListResponse(BaseModel):
    items: list[HealingEventResponse]
    total: int

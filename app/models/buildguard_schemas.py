"""
BuildGuard Telemetry Schemas

Pydantic models for BuildGuard event API validation.
Matches the JSON schemas from forge-smithy/schemas/buildguard_*.json
"""

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


class MetricsPayload(BaseModel):
    """Metrics payload within a BuildGuard event."""

    pass_: bool = Field(..., alias="pass", description="Whether the build passed")
    blocked_count: int = Field(..., ge=0, description="Number of blocked findings")
    total_findings: int = Field(..., ge=0, description="Total findings evaluated")
    triaged_count: int = Field(..., ge=0, description="Number triaged")
    avg_triage_lag_hours: Optional[float] = Field(None, ge=0, description="Average triage lag in hours")
    p50_triage_lag_hours: Optional[float] = Field(None, ge=0, description="P50 triage lag")
    p95_triage_lag_hours: Optional[float] = Field(None, ge=0, description="P95 triage lag")
    profile_hash: str = Field(..., min_length=64, max_length=64, description="Profile hash for correlation")
    evaluation_duration_ms: int = Field(..., ge=0, description="Evaluation duration in milliseconds")

    @field_validator('profile_hash')
    @classmethod
    def validate_profile_hash(cls, v: str) -> str:
        if not re.match(r'^[0-9a-f]{64}$', v):
            raise ValueError('profile_hash must be a 64-character hex string')
        return v

    class Config:
        populate_by_name = True


class BuildGuardMetricsEventCreate(BaseModel):
    """
    Schema for creating a BuildGuard metrics event.

    Matches buildguard_metrics_event.schema.json
    """

    schema_version: Literal["v1"] = Field(..., description="Schema version")
    event_type: Literal["buildguard.verdict"] = Field(..., description="Event type identifier")
    timestamp: str = Field(..., description="When the event was created (RFC3339)")
    verdict_id: str = Field(..., description="Links to the verdict")
    metrics: MetricsPayload

    @field_validator('verdict_id')
    @classmethod
    def validate_verdict_id(cls, v: str) -> str:
        # UUID format validation
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, v):
            raise ValueError('verdict_id must be a valid UUID format')
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        # Try to parse RFC3339 timestamp
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('timestamp must be a valid RFC3339 datetime')
        return v


class BuildGuardEventResponse(BaseModel):
    """Response schema for a stored BuildGuard event."""

    id: UUID
    schema_version: str
    event_type: str
    timestamp: datetime
    received_at: datetime
    verdict_id: str
    pass_status: bool
    blocked_count: int
    total_findings: int
    triaged_count: int
    avg_triage_lag_hours: Optional[float]
    p50_triage_lag_hours: Optional[float]
    p95_triage_lag_hours: Optional[float]
    profile_hash: str
    evaluation_duration_ms: int

    class Config:
        from_attributes = True


class BuildGuardProfileStatsResponse(BaseModel):
    """Response schema for profile statistics."""

    profile_hash: str
    total_verdicts: int
    pass_count: int
    fail_count: int
    pass_rate: float
    total_findings_evaluated: int
    total_blocked: int
    avg_triage_lag_hours_overall: Optional[float]
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class BuildGuardDashboardStats(BaseModel):
    """Aggregated stats for the BuildGuard dashboard."""

    # Overall metrics
    total_verdicts: int
    total_pass: int
    total_fail: int
    overall_pass_rate: float

    # Recent metrics (last 24h)
    verdicts_last_24h: int
    pass_rate_last_24h: float

    # Triage health
    avg_triage_lag_hours: Optional[float]
    p50_triage_lag_hours: Optional[float]
    p95_triage_lag_hours: Optional[float]

    # Top blocking profiles
    top_failing_profiles: List[BuildGuardProfileStatsResponse]


class EventsListResponse(BaseModel):
    """Paginated list of BuildGuard events."""

    events: List[BuildGuardEventResponse]
    total: int
    page: int
    page_size: int
    has_more: bool

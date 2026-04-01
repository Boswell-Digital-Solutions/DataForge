"""Pydantic schemas for BugCheck API.

These schemas define the request/response format for the BugCheck API endpoints.
They mirror the schemas in ForgeAgents but are tailored for DataForge's API.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================


class Severity(str, Enum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"


class Category(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    TEST = "test"
    CONTRACT = "contract"
    LINT = "lint"
    DEPENDENCY = "dependency"
    MIGRATION = "migration"
    RELIABILITY = "reliability"
    DOCUMENTATION = "documentation"


class LifecycleState(str, Enum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    FIX_PROPOSED = "FIX_PROPOSED"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    DISMISSED = "DISMISSED"


class RunMode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class RunScope(str, Enum):
    CHANGED_FILES = "changed_files"
    PACKAGE = "package"
    FULL_REPO = "full_repo"


class RunType(str, Enum):
    SERVICE_RUN = "service_run"
    ECOSYSTEM_RUN = "ecosystem_run"
    WORKFLOW_RUN = "workflow_run"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINALIZING = "finalizing"
    FINALIZED = "finalized"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GatingResult(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    PENDING = "pending"


class EnrichmentSource(str, Enum):
    MAID = "maid"
    XAI = "xai"


class EnrichmentType(str, Enum):
    FIX_PROPOSAL = "fix_proposal"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    DOCUMENTATION_LOOKUP = "documentation_lookup"
    CVE_LOOKUP = "cve_lookup"
    PATTERN_SEARCH = "pattern_search"
    IMPACT_ASSESSMENT = "impact_assessment"


class EnrichmentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    AUTOMATION = "automation"


class DismissalScope(str, Enum):
    THIS_FINDING = "this_finding"
    THIS_FILE = "this_file"
    THIS_RULE = "this_rule"
    THIS_SERVICE = "this_service"


# ============================================================================
# Run Schemas
# ============================================================================


class SeverityCountsSchema(BaseModel):
    s0: int = Field(default=0, ge=0)
    s1: int = Field(default=0, ge=0)
    s2: int = Field(default=0, ge=0)
    s3: int = Field(default=0, ge=0)
    s4: int = Field(default=0, ge=0)


class BugCheckRunCreate(BaseModel):
    """Schema for creating a BugCheck run."""
    run_id: UUID
    run_type: RunType
    targets: list[str] = Field(..., min_length=1)
    mode: RunMode
    scope: RunScope
    commit_sha: str = Field(..., pattern=r"^[a-f0-9]{40}$")
    base_commit_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    status: RunStatus = RunStatus.PENDING
    started_at: datetime
    completed_at: datetime | None = None
    severity_counts: SeverityCountsSchema = Field(default_factory=SeverityCountsSchema)
    gating_result: GatingResult | str = GatingResult.PENDING
    is_baseline: bool = False
    baseline_run_id: UUID | None = None
    triggered_by: str | None = None
    trigger_ref: str | None = None
    runtime_ms: int | None = Field(default=None, ge=0)
    checks_run: list[str] = Field(default_factory=list)
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BugCheckRunUpdate(BaseModel):
    """Schema for updating a BugCheck run."""
    status: RunStatus | None = None
    completed_at: datetime | str | None = None
    severity_counts: SeverityCountsSchema | dict[str, int] | None = None
    gating_result: GatingResult | str | None = None
    runtime_ms: int | None = None
    checks_run: list[str] | None = None
    error_message: str | None = None


class BugCheckRunResponse(BaseModel):
    """Schema for BugCheck run response."""
    run_id: UUID
    run_type: RunType | str
    targets: list[str]
    mode: RunMode | str
    scope: RunScope | str
    commit_sha: str
    base_commit_sha: str | None = None
    status: RunStatus | str
    started_at: datetime
    completed_at: datetime | None = None
    severity_counts: SeverityCountsSchema | dict[str, int]
    gating_result: GatingResult | str
    is_baseline: bool
    baseline_run_id: UUID | None = None
    triggered_by: str | None = None
    trigger_ref: str | None = None
    runtime_ms: int | None = None
    checks_run: list[str]
    error_message: str | None = None
    metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)



# ============================================================================
# Finding Schemas
# ============================================================================


class FindingLocationSchema(BaseModel):
    service: str
    file_path: str
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    column_start: int | None = Field(default=None, ge=1)
    column_end: int | None = Field(default=None, ge=1)
    function_name: str | None = None
    class_name: str | None = None


class FindingCreate(BaseModel):
    """Schema for creating a finding."""
    finding_id: UUID
    run_id: UUID
    fingerprint: str = Field(..., min_length=32, max_length=64)
    correlation_id: UUID | None = None
    severity: Severity
    category: Category
    confidence: float = Field(..., ge=0.0, le=1.0)
    title: str = Field(..., max_length=200)
    description: str
    location: FindingLocationSchema
    lifecycle_state: LifecycleState = LifecycleState.NEW
    autofix_available: bool = False
    provenance: str
    rule_id: str | None = None
    suggested_fix: str | None = None
    related_docs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    first_seen_run_id: UUID | None = None
    created_at: datetime


class FindingResponse(BaseModel):
    """Schema for finding response."""
    finding_id: UUID
    run_id: UUID
    fingerprint: str
    correlation_id: UUID | None = None
    severity: Severity | str
    category: Category | str
    confidence: float
    title: str
    description: str
    location: FindingLocationSchema | dict
    lifecycle_state: LifecycleState | str
    autofix_available: bool
    provenance: str
    rule_id: str | None = None
    suggested_fix: str | None = None
    related_docs: list[str]
    tags: list[str]
    first_seen_run_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)



class FindingsBatchResponse(BaseModel):
    """Schema for batch findings response."""
    count: int


# ============================================================================
# Enrichment Schemas
# ============================================================================


class EnrichmentContentSchema(BaseModel):
    analysis: str | None = None
    fix: dict | None = None
    references: list[dict] = Field(default_factory=list)
    cve_data: dict | None = None


class EnrichmentCreate(BaseModel):
    """Schema for creating an enrichment."""
    enrichment_id: UUID
    finding_id: UUID
    source: EnrichmentSource
    version: int = Field(..., ge=1)
    enrichment_type: EnrichmentType | None = None
    content: EnrichmentContentSchema
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    model_used: str | None = None
    tokens_used: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    created_at: datetime


class EnrichmentResponse(BaseModel):
    """Schema for enrichment response."""
    enrichment_id: UUID
    finding_id: UUID
    source: EnrichmentSource | str
    version: int
    enrichment_type: EnrichmentType | str | None = None
    content: EnrichmentContentSchema | dict
    confidence: float | None = None
    status: EnrichmentStatus | str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    model_used: str | None = None
    tokens_used: int | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ============================================================================
# Lifecycle Event Schemas
# ============================================================================


class ActorSchema(BaseModel):
    type: ActorType
    id: str
    name: str | None = None


class LifecycleEventCreate(BaseModel):
    """Schema for creating a lifecycle event."""
    event_id: UUID
    finding_id: UUID
    from_state: LifecycleState
    to_state: LifecycleState
    actor: ActorSchema
    reason: str | None = None
    scope: DismissalScope | None = None
    expires_at: datetime | None = None
    enrichment_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class LifecycleEventResponse(BaseModel):
    """Schema for lifecycle event response."""
    event_id: UUID
    finding_id: UUID
    from_state: LifecycleState | str
    to_state: LifecycleState | str
    actor_type: str
    actor_id: str
    actor_name: str | None = None
    reason: str | None = None
    scope: DismissalScope | str | None = None
    expires_at: datetime | None = None
    enrichment_id: UUID | None = None
    metadata: dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



# ============================================================================
# Progress Event Schemas
# ============================================================================


class ProgressEventCreate(BaseModel):
    """Schema for creating a progress event."""
    event_type: str
    message: str
    timestamp: datetime | str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProgressEventResponse(BaseModel):
    """Schema for progress event response."""
    id: UUID
    run_id: UUID
    event_type: str
    message: str
    metadata: dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


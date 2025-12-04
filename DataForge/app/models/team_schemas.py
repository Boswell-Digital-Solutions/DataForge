from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TeamRole(str, Enum):
    """Team member role enumeration."""
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class InviteStatus(str, Enum):
    """Team invitation status enumeration."""
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


# ============================================================================
# Team Schemas
# ============================================================================

class TeamBase(BaseModel):
    """Base schema for teams."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    organization_type: Optional[str] = Field(None, max_length=50)
    team_size: Optional[int] = Field(None, ge=1, le=10000)
    industry: Optional[str] = Field(None, max_length=100)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False


class TeamCreate(TeamBase):
    """Schema for creating a new team."""
    owner_id: int


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    organization_type: Optional[str] = Field(None, max_length=50)
    team_size: Optional[int] = Field(None, ge=1, le=10000)
    industry: Optional[str] = Field(None, max_length=100)
    settings: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class TeamResponse(TeamBase):
    """Schema for team responses."""
    id: int
    owner_id: int
    is_active: bool
    member_count: int
    project_count: int
    total_sessions: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TeamSummary(BaseModel):
    """Compact team summary for lists."""
    id: int
    name: str
    slug: str
    member_count: int
    project_count: int
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Team Member Schemas
# ============================================================================

class TeamMemberBase(BaseModel):
    """Base schema for team members."""
    team_id: int
    user_id: int
    role: TeamRole = TeamRole.member


class TeamMemberCreate(TeamMemberBase):
    """Schema for adding a team member."""
    invited_by: Optional[int] = None


class TeamMemberUpdate(BaseModel):
    """Schema for updating a team member."""
    role: Optional[TeamRole] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(TeamMemberBase):
    """Schema for team member responses."""
    id: int
    joined_at: datetime
    invited_by: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Team Invite Schemas
# ============================================================================

class TeamInviteBase(BaseModel):
    """Base schema for team invites."""
    team_id: int
    invited_email: str = Field(..., max_length=255)
    role: TeamRole = TeamRole.member


class TeamInviteCreate(TeamInviteBase):
    """Schema for creating a team invite."""
    invited_by: int
    expires_in_days: int = Field(default=7, ge=1, le=30)


class TeamInviteUpdate(BaseModel):
    """Schema for updating a team invite."""
    status: Optional[InviteStatus] = None


class TeamInviteResponse(TeamInviteBase):
    """Schema for team invite responses."""
    id: int
    invited_user_id: Optional[int] = None
    invited_by: int
    status: InviteStatus
    invite_token: str
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TeamInviteAccept(BaseModel):
    """Schema for accepting a team invite."""
    invite_token: str


# ============================================================================
# Team Project Schemas
# ============================================================================

class TeamProjectBase(BaseModel):
    """Base schema for team projects."""
    team_id: int
    project_id: int
    is_team_template: bool = False
    visibility: str = Field(default="team", max_length=20)


class TeamProjectCreate(TeamProjectBase):
    """Schema for creating a team project."""
    created_by: int


class TeamProjectUpdate(BaseModel):
    """Schema for updating a team project."""
    is_team_template: Optional[bool] = None
    visibility: Optional[str] = Field(None, max_length=20)


class TeamProjectResponse(TeamProjectBase):
    """Schema for team project responses."""
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Team Learning Aggregate Schemas
# ============================================================================

class TeamLearningAggregateBase(BaseModel):
    """Base schema for team learning aggregates."""
    team_id: int
    period_start: datetime
    period_end: datetime
    member_count_snapshot: int
    top_languages: List[Dict[str, Any]] = Field(default_factory=list)
    language_trends: Dict[str, Any] = Field(default_factory=dict)
    top_stacks: List[Dict[str, Any]] = Field(default_factory=list)
    stack_combinations: List[Dict[str, Any]] = Field(default_factory=list)
    common_project_types: List[Dict[str, Any]] = Field(default_factory=list)
    avg_project_complexity: Optional[float] = None
    avg_team_size_preference: Optional[float] = None
    overall_success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    projects_completed: int = 0
    projects_abandoned: int = 0
    avg_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    total_llm_queries: int = 0
    avg_tokens_per_session: Optional[float] = None
    most_used_provider: Optional[str] = None
    most_used_model: Optional[str] = None
    avg_session_duration_minutes: Optional[float] = None
    avg_steps_revisited: Optional[float] = None
    recommendation_override_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    recommended_languages: List[str] = Field(default_factory=list)
    recommended_stacks: List[str] = Field(default_factory=list)
    improvement_suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class TeamLearningAggregateCreate(TeamLearningAggregateBase):
    """Schema for creating a team learning aggregate."""
    pass


class TeamLearningAggregateResponse(TeamLearningAggregateBase):
    """Schema for team learning aggregate responses."""
    id: int
    computed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Team Insight Schemas
# ============================================================================

class TeamInsightBase(BaseModel):
    """Base schema for team insights."""
    team_id: int
    insight_type: str = Field(..., max_length=50)
    category: str = Field(..., max_length=50)
    priority: str = Field(default="medium", max_length=20)
    title: str = Field(..., max_length=500)
    description: str
    actionable_steps: Optional[List[Dict[str, Any]]] = None
    data_sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    impact_estimate: Optional[str] = Field(None, max_length=20)


class TeamInsightCreate(TeamInsightBase):
    """Schema for creating a team insight."""
    generated_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class TeamInsightUpdate(BaseModel):
    """Schema for updating a team insight."""
    is_active: Optional[bool] = None
    is_read: Optional[bool] = None
    is_acted_upon: Optional[bool] = None
    dismissed_at: Optional[datetime] = None


class TeamInsightResponse(TeamInsightBase):
    """Schema for team insight responses."""
    id: int
    is_active: bool
    is_read: bool
    is_acted_upon: bool
    dismissed_at: Optional[datetime] = None
    generated_by: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Analytics & Reports
# ============================================================================

class TeamAnalyticsRequest(BaseModel):
    """Request schema for team analytics."""
    team_id: int
    start_date: datetime
    end_date: datetime
    metrics: List[str] = Field(default_factory=list)


class TeamAnalyticsResponse(BaseModel):
    """Response schema for team analytics."""
    team_id: int
    period_start: datetime
    period_end: datetime
    member_count: int
    metrics: Dict[str, Any]
    insights: List[TeamInsightResponse]
    recommendations: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)

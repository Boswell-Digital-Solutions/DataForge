from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectType(str, Enum):
    """Project type enumeration."""
    web = "web"
    mobile = "mobile"
    desktop = "desktop"
    api = "api"
    ai_ml = "ai_ml"
    other = "other"


class OutcomeStatus(str, Enum):
    """Outcome status enumeration."""
    success = "success"
    partial = "partial"
    failure = "failure"
    unknown = "unknown"


# ============================================================================
# VibeForge Project Schemas
# ============================================================================

class VibeForgeProjectBase(BaseModel):
    """Base schema for VibeForge projects."""
    project_name: str = Field(..., min_length=1, max_length=255)
    project_type: ProjectType
    description: Optional[str] = None
    selected_languages: List[str] = Field(..., min_items=1)
    selected_stack: str = Field(..., min_length=1, max_length=100)
    intent_description: Optional[str] = None
    team_size: Optional[int] = Field(None, ge=1, le=1000)
    timeline_estimate: Optional[str] = None
    complexity_score: Optional[float] = Field(None, ge=0.0, le=10.0)


class VibeForgeProjectCreate(VibeForgeProjectBase):
    """Schema for creating a new VibeForge project."""
    user_id: Optional[int] = None


class VibeForgeProjectUpdate(BaseModel):
    """Schema for updating a VibeForge project."""
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    complexity_score: Optional[float] = Field(None, ge=0.0, le=10.0)


class VibeForgeProjectResponse(VibeForgeProjectBase):
    """Schema for VibeForge project responses."""
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Session Schemas
# ============================================================================

class ProjectSessionBase(BaseModel):
    """Base schema for project sessions."""
    project_id: int
    steps_completed: List[int] = Field(default_factory=list)
    steps_revisited: List[int] = Field(default_factory=list)
    languages_viewed: List[str] = Field(default_factory=list)
    languages_considered: List[str] = Field(default_factory=list)
    languages_final: List[str] = Field(default_factory=list)
    stacks_viewed: List[str] = Field(default_factory=list)
    stacks_compared: List[str] = Field(default_factory=list)
    stack_recommended: Optional[str] = None
    stack_final: Optional[str] = None
    stack_override: bool = False
    llm_queries: int = 0
    llm_provider_used: Optional[str] = None
    llm_tokens_consumed: int = 0
    abandoned: bool = False
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)


class ProjectSessionCreate(ProjectSessionBase):
    """Schema for creating a new project session."""
    pass


class ProjectSessionUpdate(BaseModel):
    """Schema for updating a project session."""
    session_completed_at: Optional[datetime] = None
    session_duration_seconds: Optional[int] = Field(None, ge=0)
    steps_completed: Optional[List[int]] = None
    steps_revisited: Optional[List[int]] = None
    languages_viewed: Optional[List[str]] = None
    languages_considered: Optional[List[str]] = None
    languages_final: Optional[List[str]] = None
    stacks_viewed: Optional[List[str]] = None
    stacks_compared: Optional[List[str]] = None
    stack_recommended: Optional[str] = None
    stack_final: Optional[str] = None
    stack_override: Optional[bool] = None
    llm_queries: Optional[int] = Field(None, ge=0)
    llm_provider_used: Optional[str] = None
    llm_tokens_consumed: Optional[int] = Field(None, ge=0)
    abandoned: Optional[bool] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)


class ProjectSessionResponse(ProjectSessionBase):
    """Schema for project session responses."""
    id: int
    session_started_at: datetime
    session_completed_at: Optional[datetime] = None
    session_duration_seconds: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Stack Outcome Schemas
# ============================================================================

class StackOutcomeBase(BaseModel):
    """Base schema for stack outcomes."""
    project_id: int
    stack_id: str = Field(..., min_length=1, max_length=100)
    project_type: ProjectType
    languages_used: List[str] = Field(..., min_items=1)
    outcome_status: OutcomeStatus
    build_successful: Optional[bool] = None
    tests_passed: Optional[bool] = None
    deployed_successfully: Optional[bool] = None
    build_time_seconds: Optional[int] = Field(None, ge=0)
    test_pass_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    deployment_time_seconds: Optional[int] = Field(None, ge=0)
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    would_recommend: Optional[bool] = None
    issues_count: int = 0
    issue_types: Optional[List[str]] = None
    fix_iterations: int = 0
    notes: Optional[str] = None


class StackOutcomeCreate(StackOutcomeBase):
    """Schema for creating a new stack outcome."""
    pass


class StackOutcomeUpdate(BaseModel):
    """Schema for updating a stack outcome."""
    outcome_status: Optional[OutcomeStatus] = None
    build_successful: Optional[bool] = None
    tests_passed: Optional[bool] = None
    deployed_successfully: Optional[bool] = None
    build_time_seconds: Optional[int] = Field(None, ge=0)
    test_pass_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    deployment_time_seconds: Optional[int] = Field(None, ge=0)
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    would_recommend: Optional[bool] = None
    issues_count: Optional[int] = Field(None, ge=0)
    issue_types: Optional[List[str]] = None
    fix_iterations: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class StackOutcomeResponse(StackOutcomeBase):
    """Schema for stack outcome responses."""
    id: int
    recorded_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Model Performance Schemas
# ============================================================================

class ModelPerformanceBase(BaseModel):
    """Base schema for model performance."""
    session_id: Optional[int] = None
    provider: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=100)
    prompt_type: str = Field(..., min_length=1, max_length=50)
    response_time_ms: Optional[int] = Field(None, ge=0)
    tokens_prompt: Optional[int] = Field(None, ge=0)
    tokens_completion: Optional[int] = Field(None, ge=0)
    tokens_total: Optional[int] = Field(None, ge=0)
    recommendation_accepted: Optional[bool] = None
    recommendation_helpful: Optional[bool] = None
    recommendation_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    experiment_id: Optional[str] = Field(None, max_length=100)
    variant: Optional[str] = Field(None, max_length=50)
    context_data: Optional[Dict[str, Any]] = None


class ModelPerformanceCreate(ModelPerformanceBase):
    """Schema for creating model performance records."""
    pass


class ModelPerformanceUpdate(BaseModel):
    """Schema for updating model performance."""
    recommendation_accepted: Optional[bool] = None
    recommendation_helpful: Optional[bool] = None


class ModelPerformanceResponse(ModelPerformanceBase):
    """Schema for model performance responses."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Language Preference Schemas
# ============================================================================

class LanguagePreferenceBase(BaseModel):
    """Base schema for language preferences."""
    user_id: int
    language_id: str = Field(..., min_length=1, max_length=50)
    language_name: str = Field(..., min_length=1, max_length=100)
    times_selected: int = 0
    times_viewed: int = 0
    times_considered: int = 0
    successful_projects: int = 0
    failed_projects: int = 0
    avg_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    project_types_used_in: List[str] = Field(default_factory=list)
    paired_with_languages: Dict[str, int] = Field(default_factory=dict)
    paired_with_stacks: Dict[str, int] = Field(default_factory=dict)
    last_used_at: Optional[datetime] = None


class LanguagePreferenceUpdate(BaseModel):
    """Schema for updating language preferences."""
    times_selected: Optional[int] = Field(None, ge=0)
    times_viewed: Optional[int] = Field(None, ge=0)
    times_considered: Optional[int] = Field(None, ge=0)
    successful_projects: Optional[int] = Field(None, ge=0)
    failed_projects: Optional[int] = Field(None, ge=0)
    avg_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    project_types_used_in: Optional[List[str]] = None
    paired_with_languages: Optional[Dict[str, int]] = None
    paired_with_stacks: Optional[Dict[str, int]] = None
    last_used_at: Optional[datetime] = None


class LanguagePreferenceResponse(LanguagePreferenceBase):
    """Schema for language preference responses."""
    id: int
    first_used_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Analytics Schemas
# ============================================================================

class StackSuccessRate(BaseModel):
    """Schema for stack success rate analytics."""
    stack_id: str
    project_type: ProjectType
    total_uses: int
    success_count: int
    partial_count: int
    failure_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    avg_build_time_seconds: Optional[int] = None
    avg_test_pass_rate: Optional[float] = Field(None, ge=0.0, le=1.0)


class LanguageTrend(BaseModel):
    """Schema for language usage trends."""
    language_id: str
    language_name: str
    total_selections: int
    total_projects: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    most_paired_with: List[str] = Field(default_factory=list)
    popular_stacks: List[str] = Field(default_factory=list)


class UserPreferenceSummary(BaseModel):
    """Schema for user preference summary."""
    user_id: int
    favorite_languages: List[str] = Field(default_factory=list)
    favorite_stacks: List[str] = Field(default_factory=list)
    preferred_project_types: List[ProjectType] = Field(default_factory=list)
    total_projects: int = 0
    success_rate: float = Field(0.0, ge=0.0, le=1.0)
    avg_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)

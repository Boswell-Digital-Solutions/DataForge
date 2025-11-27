"""
Multi-AI Planning System Pydantic Schemas

Request/response models for the planning system API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Stage Result Schema
# ============================================================================

class StageResult(BaseModel):
    """Result from a single planning stage."""
    stage: int = Field(..., ge=1)
    type: str = Field(..., max_length=50)  # 'initial', 'review', 'refinement', 'final'
    model: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=50)
    duration_ms: int = Field(..., ge=0)
    tokens_in: int = Field(..., ge=0)
    tokens_out: int = Field(..., ge=0)
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Planning Outcome Schemas
# ============================================================================

class PlanningOutcomeCreate(BaseModel):
    """Create a new planning outcome record."""
    session_id: str = Field(..., min_length=1)
    workflow_type: str = Field(..., max_length=50)
    task_type: Optional[str] = Field(None, max_length=50)
    request_complexity: Optional[str] = Field(None, max_length=20)
    codebase_context: Optional[Dict[str, Any]] = None
    stages: List[StageResult]
    total_duration_ms: int = Field(..., ge=0)
    total_tokens_used: int = Field(..., ge=0)
    total_cost_cents: int = Field(..., ge=0)
    iteration_count: int = Field(default=1, ge=1)

    @field_validator('request_complexity')
    @classmethod
    def validate_complexity(cls, v):
        if v and v not in ['simple', 'medium', 'complex']:
            raise ValueError('Complexity must be simple, medium, or complex')
        return v


class ExecutionResultUpdate(BaseModel):
    """Update planning outcome with execution results."""
    success: bool
    duration_seconds: int = Field(..., ge=0)
    tasks_completed: int = Field(default=0, ge=0)
    tasks_failed: int = Field(default=0, ge=0)


class UserFeedbackUpdate(BaseModel):
    """Update planning outcome with user feedback."""
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
    plan_was_modified: bool = Field(default=False)
    modification_extent: Optional[float] = Field(None, ge=0.0, le=1.0)


class PlanningOutcomeResponse(BaseModel):
    """Planning outcome response."""
    id: str
    created_at: datetime
    session_id: str
    user_id: Optional[str]
    workflow_type: str
    task_type: Optional[str]
    total_duration_ms: Optional[int]
    total_tokens_used: Optional[int]
    total_cost_cents: Optional[int]
    execution_success: Optional[bool]
    user_rating: Optional[int]

    class Config:
        from_attributes = True


# ============================================================================
# Model Performance Schemas
# ============================================================================

class ModelPerformanceResponse(BaseModel):
    """Model performance metrics response."""
    model: str
    provider: str
    stage_type: str
    task_type: str
    sample_count: int
    avg_duration_ms: Optional[float]
    avg_tokens: Optional[float]
    avg_quality_score: Optional[float]
    success_rate: Optional[float]
    ema_duration_ms: Optional[float]
    ema_quality: Optional[float]
    avg_cost_cents: Optional[float]

    class Config:
        from_attributes = True


# ============================================================================
# Recommendation Schemas
# ============================================================================

class ModelRecommendation(BaseModel):
    """Recommendation for a specific model."""
    model: str
    provider: str
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class StageModelRecommendations(BaseModel):
    """Model recommendations for all planning stages."""
    initial: ModelRecommendation
    review: ModelRecommendation
    refinement: ModelRecommendation
    final: ModelRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    based_on_samples: int = Field(..., ge=0)


class TimeEstimateRecommendation(BaseModel):
    """Time estimation recommendation."""
    estimated_minutes: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_interval: Optional[tuple[float, float]] = None
    based_on_samples: int = Field(..., ge=0)
    note: Optional[str] = None


class IterationRecommendation(BaseModel):
    """Iteration count recommendation."""
    recommended: int = Field(..., ge=1)
    min_viable: int = Field(..., ge=1)
    diminishing_returns: int = Field(..., ge=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    based_on_samples: int = Field(default=0, ge=0)
    note: Optional[str] = None


# ============================================================================
# AI Estimation Feedback Schemas
# ============================================================================

class AIEstimationFeedbackCreate(BaseModel):
    """Create AI estimation feedback record."""
    task_category: str = Field(..., max_length=50)
    task_complexity: Optional[str] = Field(None, max_length=20)
    estimated_minutes: float = Field(..., gt=0)
    actual_minutes: float = Field(..., gt=0)
    executor_type: str = Field(..., max_length=30)
    model_used: Optional[str] = Field(None, max_length=100)
    codebase_lines: Optional[int] = Field(None, ge=0)
    factors: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AIEstimationFeedbackResponse(BaseModel):
    """AI estimation feedback response."""
    id: str
    created_at: datetime
    task_category: str
    task_complexity: Optional[str]
    estimated_minutes: float
    actual_minutes: float
    accuracy_ratio: Optional[float]
    executor_type: str
    model_used: Optional[str]

    class Config:
        from_attributes = True

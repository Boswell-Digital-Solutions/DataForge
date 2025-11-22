"""
DataForge - Run History Schemas

Pydantic schemas for API request/response validation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Model Result Schemas
# ============================================================================

class ModelResultBase(BaseModel):
    """Base schema for model execution result."""
    model_id: str = Field(..., description="Model identifier (e.g., 'claude-3.5-sonnet')")
    provider: str = Field(..., description="Provider name (e.g., 'anthropic', 'openai', 'ollama')")
    output: str = Field(..., description="Model's generated output")
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(..., ge=0, description="Execution time in milliseconds")
    status: str = Field(default="success", description="Execution status")
    error_message: Optional[str] = Field(default=None, description="Error message if status is 'error'")


class ModelResultCreate(ModelResultBase):
    """Schema for creating a model result."""
    pass


class ModelResult(ModelResultBase):
    """Schema for model result with database fields."""
    id: int
    run_id: str
    cost_usd: float = Field(..., ge=0, description="Calculated cost in USD")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Run Schemas
# ============================================================================

class RunBase(BaseModel):
    """Base schema for run."""
    workspace_id: str = Field(..., description="Workspace identifier")
    prompt_snapshot: str = Field(..., description="Prompt text at execution time")
    context_block_ids: List[str] = Field(default_factory=list, description="Context blocks used")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    notes: Optional[str] = Field(default=None, description="User notes about this run")


class RunCreate(RunBase):
    """Schema for creating a run."""
    run_id: str = Field(..., description="Unique run identifier")
    results: List[ModelResultCreate] = Field(..., description="Model execution results")
    total_latency_ms: float = Field(..., ge=0)


class Run(RunBase):
    """Schema for run with all database fields."""
    run_id: str
    total_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    results: List[ModelResult] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RunSummary(BaseModel):
    """Compact run summary for list views."""
    run_id: str
    workspace_id: str
    prompt_snapshot: str = Field(..., description="First 100 chars of prompt")
    model_ids: List[str] = Field(..., description="Models used in this run")
    total_tokens: int
    total_cost_usd: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Query/Filter Schemas
# ============================================================================

class RunFilters(BaseModel):
    """Query filters for listing runs."""
    workspace_id: Optional[str] = None
    model_id: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ============================================================================
# Response Schemas
# ============================================================================

class ListRunsResponse(BaseModel):
    """Response for listing runs."""
    runs: List[RunSummary]
    total: int = Field(..., description="Total number of matching runs")
    page: int
    page_size: int
    has_more: bool = Field(..., description="Whether more pages are available")


class UsageMetrics(BaseModel):
    """Usage metrics for analytics."""
    workspace_id: str
    total_runs: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_cost_usd: float = Field(..., ge=0)
    runs_by_model: Dict[str, int] = Field(..., description="Number of runs per model")
    tokens_by_model: Dict[str, int] = Field(..., description="Total tokens per model")
    cost_by_model: Dict[str, float] = Field(..., description="Total cost per model")
    date_range: Dict[str, str] = Field(..., description="Start and end dates of metrics")


class RunDetailResponse(BaseModel):
    """Detailed run information."""
    run_id: str
    workspace_id: str
    prompt_snapshot: str
    context_block_ids: List[str]
    results: List[ModelResult]
    total_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    tags: List[str]
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DeleteRunResponse(BaseModel):
    """Response for run deletion."""
    status: str = Field(default="success")
    message: str
    run_id: str

"""Global Rate Limits — Pydantic v2 schemas.

Request/response models for the rate-limits API.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────


class RateLimitProvider(str, Enum):
    XAI = "xai"
    MAID = "maid"


# ── Request Schemas ──────────────────────────────────────────


class RateLimitCheckRequest(BaseModel):
    """Atomically check and increment the rate limit counter."""

    provider: RateLimitProvider
    estimated_cost_usd: float = Field(default=0.0, ge=0)


class RateLimitConfigUpsert(BaseModel):
    """Create or update rate limit configuration for a provider."""

    provider: RateLimitProvider
    window_duration_seconds: int = Field(default=2592000, description="Default 30 days")
    max_count: int = Field(ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0)


# ── Response Schemas ─────────────────────────────────────────


class RateLimitCheckResponse(BaseModel):
    """Result of a rate-limit check."""

    allowed: bool
    provider: str
    current_count: int
    max_count: int
    requests_remaining: int
    utilization: float = Field(ge=0, le=1)
    cost_usd: float
    max_cost_usd: float | None
    reason: str


class RateLimitStatusResponse(BaseModel):
    """Current status of a provider's rate limit."""

    id: UUID
    provider: str
    window_start: datetime
    window_duration_seconds: int
    current_count: int
    max_count: int
    requests_remaining: int
    utilization: float
    cost_usd: float
    max_cost_usd: float | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RateLimitSummaryResponse(BaseModel):
    """Summary of all rate limits."""

    providers: list[RateLimitStatusResponse]
    total_providers: int

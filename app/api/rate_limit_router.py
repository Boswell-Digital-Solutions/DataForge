"""
Rate Limiting Admin API Router - REST endpoints for managing rate limits.

Provides endpoints for:
- Checking current rate limit status
- Managing rate limit configurations
- Whitelisting/blacklisting identifiers
- Resetting counters
- Viewing metrics
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from app.utils.rate_limiter import (
    get_rate_limiter,
    SlidingWindowLimiter,
    RateLimitWindow,
    RateLimitScope,
    RateLimitConfig,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class RateLimitConfigRequest(BaseModel):
    """Request to create/update rate limit configuration."""
    name: str = Field(..., description="Unique limit name")
    scope: str = Field(..., description="Scope: user, ip, endpoint, combined")
    window: str = Field(..., description="Window: second, minute, hour, day")
    max_requests: int = Field(..., ge=1, description="Max requests in window")
    description: str = Field(default="", description="Human-readable description")
    enabled: bool = Field(default=True, description="Is limit active?")

    class Config:
        example = {
            "name": "custom_limit",
            "scope": "user",
            "window": "minute",
            "max_requests": 100,
            "description": "Custom per-user limit",
        }


class RateLimitConfigResponse(BaseModel):
    """Response with rate limit configuration."""
    name: str
    scope: str
    window: str
    max_requests: int
    description: str
    enabled: bool

    class Config:
        example = {
            "name": "public_api",
            "scope": "ip",
            "window": "minute",
            "max_requests": 60,
            "description": "Public API: 60 requests per minute per IP",
            "enabled": True,
        }


class RateLimitStatusRequest(BaseModel):
    """Request to check rate limit status."""
    limit_name: str = Field(..., description="Name of the rate limit")
    identifier: str = Field(..., description="User ID, IP, endpoint, etc.")

    class Config:
        example = {
            "limit_name": "authenticated_api",
            "identifier": "user-123",
        }


class RateLimitStatusResponse(BaseModel):
    """Response with rate limit status."""
    limit_name: str
    is_limited: bool
    allowed: int
    used: Optional[int] = None
    remaining: Optional[int] = None
    window: str
    reset_in_seconds: Optional[int] = None
    reset_at: Optional[int] = None
    message: Optional[str] = None


class WhitelistRequest(BaseModel):
    """Request to whitelist/unwhitelist identifier."""
    identifier: str = Field(..., description="User ID, IP, or other identifier")
    ttl_hours: int = Field(default=24, ge=0, description="TTL for whitelist entry (0=permanent)")

    class Config:
        example = {
            "identifier": "admin-user-1",
            "ttl_hours": 24,
        }


class RateLimitMetricsResponse(BaseModel):
    """Response with rate limiting metrics."""
    total_requests: int = Field(description="Total requests processed")
    rate_limited_requests: int = Field(description="Requests rejected")
    allowed_requests: int = Field(description="Requests allowed")
    exceeded_by_scope: Dict[str, int] = Field(description="Breakdown by scope")
    redis_errors: int = Field(description="Redis errors")
    active_limits: int = Field(description="Active limit configurations")
    redis_available: bool = Field(description="Is Redis available?")

    class Config:
        example = {
            "total_requests": 10000,
            "rate_limited_requests": 125,
            "allowed_requests": 9875,
            "exceeded_by_scope": {"user": 75, "ip": 50},
            "redis_errors": 0,
            "active_limits": 5,
            "redis_available": True,
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    redis_available: bool
    message: str


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/admin/rate-limits",
    tags=["rate-limiting"],
    responses={401: {"description": "Not authenticated"}, 403: {"description": "Not authorized"}},
)


def get_limiter() -> SlidingWindowLimiter:
    """Dependency injection for rate limiter."""
    import redis
    from app.config import config

    redis_client = redis.from_url(config.redis_url)
    return get_rate_limiter(redis_client)


# ============================================================================
# Health & Status
# ============================================================================


@router.get("/health", response_model=HealthResponse)
async def rate_limit_health(limiter: SlidingWindowLimiter = Depends(get_limiter)):
    """Check rate limiting system health."""
    status = "healthy" if limiter.is_redis_available() else "degraded"
    message = "Rate limiting active" if limiter.is_redis_available() else "Redis unavailable"

    return HealthResponse(
        status=status,
        redis_available=limiter.is_redis_available(),
        message=message,
    )


@router.get("/metrics", response_model=RateLimitMetricsResponse)
async def get_metrics(limiter: SlidingWindowLimiter = Depends(get_limiter)):
    """Get rate limiting metrics."""
    metrics = limiter.get_metrics()
    return RateLimitMetricsResponse(
        total_requests=metrics.total_requests,
        rate_limited_requests=metrics.rate_limited_requests,
        allowed_requests=metrics.allowed_requests,
        exceeded_by_scope=metrics.exceeded_by_scope,
        redis_errors=metrics.redis_errors,
        active_limits=metrics.active_limits,
        redis_available=limiter.is_redis_available(),
    )


# ============================================================================
# Limit Configuration
# ============================================================================


@router.get("/limits", response_model=List[RateLimitConfigResponse])
async def list_limits(limiter: SlidingWindowLimiter = Depends(get_limiter)):
    """List all rate limit configurations."""
    limits = limiter.get_all_limits()
    return [RateLimitConfigResponse(**limit.to_dict()) for limit in limits.values()]


@router.get("/limits/{name}", response_model=RateLimitConfigResponse)
async def get_limit_config(
    name: str = Path(..., description="Limit name"),
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Get specific limit configuration."""
    limit = limiter.get_limit(name)
    if not limit:
        raise HTTPException(
            status_code=404,
            detail=f"Rate limit '{name}' not found",
        )
    return RateLimitConfigResponse(**limit.to_dict())


@router.post("/limits", response_model=RateLimitConfigResponse)
async def create_limit(
    req: RateLimitConfigRequest,
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Create or update a rate limit configuration."""
    try:
        scope = RateLimitScope(req.scope)
        window = RateLimitWindow(req.window)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope or window: {e}",
        )

    config = RateLimitConfig(
        name=req.name,
        scope=scope,
        window=window,
        max_requests=req.max_requests,
        description=req.description,
        enabled=req.enabled,
    )

    limiter.register_limit(config)
    return RateLimitConfigResponse(**config.to_dict())


# ============================================================================
# Status & Usage
# ============================================================================


@router.post("/status", response_model=RateLimitStatusResponse)
async def check_status(
    req: RateLimitStatusRequest,
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Check rate limit status for an identifier (without consuming quota)."""
    if not limiter.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    usage = limiter.get_current_usage(req.limit_name, req.identifier)
    if "error" in usage:
        raise HTTPException(
            status_code=404,
            detail=usage.get("error", "Limit not found"),
        )

    is_limited = usage.get("used", 0) >= usage.get("allowed", 1)
    return RateLimitStatusResponse(
        limit_name=req.limit_name,
        is_limited=is_limited,
        allowed=usage.get("allowed", 0),
        used=usage.get("used", 0),
        remaining=usage.get("remaining", 0),
        window=usage.get("window", ""),
        reset_in_seconds=usage.get("reset_in_seconds"),
        message=usage.get("message"),
    )


# ============================================================================
# Whitelist Management
# ============================================================================


@router.post("/whitelist", response_model=Dict)
async def whitelist_identifier(
    req: WhitelistRequest,
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Add identifier to whitelist (unlimited requests)."""
    if not limiter.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    success = limiter.whitelist_identifier(req.identifier, req.ttl_hours)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to whitelist identifier",
        )

    return {
        "success": True,
        "identifier": req.identifier,
        "message": f"Whitelisted for {req.ttl_hours} hours" if req.ttl_hours > 0 else "Whitelisted permanently",
    }


@router.delete("/whitelist/{identifier}", response_model=Dict)
async def remove_whitelist(
    identifier: str = Path(..., description="Identifier to remove from whitelist"),
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Remove identifier from whitelist."""
    if not limiter.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    success = limiter.remove_from_whitelist(identifier)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to remove from whitelist",
        )

    return {
        "success": True,
        "identifier": identifier,
        "message": "Removed from whitelist",
    }


# ============================================================================
# Reset & Cleanup
# ============================================================================


@router.post("/reset/{limit_name}/{identifier}", response_model=Dict)
async def reset_limit(
    limit_name: str = Path(..., description="Limit name"),
    identifier: str = Path(..., description="Identifier to reset"),
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Manually reset rate limit counter for an identifier."""
    if not limiter.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    success = limiter.reset_identifier_limit(limit_name, identifier)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Limit '{limit_name}' not found",
        )

    return {
        "success": True,
        "limit_name": limit_name,
        "identifier": identifier,
        "message": "Limit counter reset",
    }


@router.post("/clear-all", response_model=Dict)
async def clear_all_limits(
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """
    Clear all rate limit data.

    WARNING: This resets all rate limit counters!
    Use only in exceptional circumstances.
    """
    if not limiter.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    count = limiter.clear_all_limits()
    logger.warning(f"Cleared {count} rate limit keys via admin API")

    return {
        "success": True,
        "cleared_keys": count,
        "message": "All rate limit data cleared",
    }


# ============================================================================
# Metrics Management
# ============================================================================


@router.delete("/metrics/reset", response_model=Dict)
async def reset_metrics(
    limiter: SlidingWindowLimiter = Depends(get_limiter),
):
    """Reset rate limiting metrics to zero."""
    limiter.reset_metrics()
    return {
        "success": True,
        "message": "Metrics reset to zero",
    }

"""
Token Revocation Admin API Router - REST endpoints for managing token revocation.

Provides endpoints for:
- Revoking individual tokens
- Bulk revocation by user or pattern
- Checking revocation status
- Viewing revocation history
- Unrevoke operations (restoration)
- Metrics and monitoring
"""

from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict
import logging

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field, ConfigDict

from app.utils.token_revocation import (
    get_token_revocation_manager,
    TokenRevocationManager,
    RevocationReason,
    RevocationRecord,
    RevocationMetrics,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class RevokeTokenRequest(BaseModel):
    """Request to revoke a single token."""
    jti: str = Field(..., description="JWT ID claim")
    user_id: str = Field(..., description="User ID")
    reason: str = Field(
        default="user_logout",
        description="Revocation reason (logout, compromised, etc.)",
    )
    metadata: Optional[Dict] = Field(default=None, description="Extra context")

    model_config = ConfigDict(example={'jti': 'abc123', 'user_id': 'user-456', 'reason': 'user_logout', 'metadata': {'device_id': 'iphone-x'}})



class RevokeUserTokensRequest(BaseModel):
    """Request to revoke all tokens for a user."""
    user_id: str = Field(..., description="User ID to revoke tokens for")
    reason: str = Field(
        default="security_event",
        description="Revocation reason",
    )
    except_jti: Optional[str] = Field(
        default=None,
        description="JTI to keep active - logout everywhere except this token",
    )
    metadata: Optional[Dict] = Field(default=None, description="Extra context")

    model_config = ConfigDict(example={'user_id': 'user-456', 'reason': 'password_changed', 'except_jti': 'current-token-jti'})



class UnrevokeTokenRequest(BaseModel):
    """Request to restore a revoked token."""
    jti: str = Field(..., description="JWT ID claim to restore")

    model_config = ConfigDict(example={'jti': 'abc123'})



class RevocationRecordResponse(BaseModel):
    """Response with revocation record details."""
    jti: str
    user_id: str
    revoked_at: str
    reason: str
    expires_at: Optional[str]
    metadata: Dict

    model_config = ConfigDict(example={'jti': 'abc123', 'user_id': 'user-456', 'revoked_at': '2025-11-21T15:30:00', 'reason': 'user_logout', 'expires_at': '2025-11-21T16:30:00', 'metadata': {}})



class RevocationStatusResponse(BaseModel):
    """Response indicating revocation status."""
    is_revoked: bool
    record: Optional[RevocationRecordResponse] = None

    model_config = ConfigDict(example={'is_revoked': True, 'record': {'jti': 'abc123', 'user_id': 'user-456', 'revoked_at': '2025-11-21T15:30:00', 'reason': 'user_logout', 'expires_at': '2025-11-21T16:30:00', 'metadata': {}}})



class BulkActionResponse(BaseModel):
    """Response for bulk operations."""
    success: bool
    count: int
    details: str

    model_config = ConfigDict(example={'success': True, 'count': 5, 'details': 'Revoked 5 tokens for user-456'})



class RevocationMetricsResponse(BaseModel):
    """Response with revocation metrics."""
    total_revoked: int = Field(description="Total tokens revoked (cumulative)")
    active_revocations: int = Field(description="Currently blacklisted tokens")
    revoked_by_reason: Dict[str, int] = Field(description="Breakdown by revocation reason")
    bulk_revocations: int = Field(description="Number of bulk operations")
    failed_revocations: int = Field(description="Failed revocation attempts")
    redis_available: bool = Field(description="Is Redis available for revocation?")

    model_config = ConfigDict(example={'total_revoked': 42, 'active_revocations': 12, 'revoked_by_reason': {'user_logout': 25, 'password_changed': 10, 'security_event': 7}, 'bulk_revocations': 3, 'failed_revocations': 0, 'redis_available': True})



class UserRevocationsResponse(BaseModel):
    """Response with all revocations for a user."""
    user_id: str
    total: int
    revocations: List[RevocationRecordResponse]

    model_config = ConfigDict(example={'user_id': 'user-456', 'total': 2, 'revocations': [{'jti': 'abc123', 'user_id': 'user-456', 'revoked_at': '2025-11-21T15:30:00', 'reason': 'user_logout', 'expires_at': '2025-11-21T16:30:00', 'metadata': {}}]})



class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    redis_available: bool
    message: str


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/admin/tokens",
    tags=["token-revocation"],
    responses={401: {"description": "Not authenticated"}, 403: {"description": "Not authorized"}},
)


# Dependency: Get revocation manager
def get_revocation_manager() -> TokenRevocationManager:
    """Dependency injection for revocation manager."""
    # In production, create Redis client from config
    import redis
    from app.config import config

    redis_client = redis.from_url(config.redis_url)
    return get_token_revocation_manager(redis_client)


# ============================================================================
# Health & Status Endpoints
# ============================================================================


@router.get("/health", response_model=HealthResponse)
async def token_revocation_health(manager: TokenRevocationManager = Depends(get_revocation_manager)):
    """Check token revocation system health."""
    status = "healthy" if manager.is_redis_available() else "degraded"
    message = "Token revocation system operational" if manager.is_redis_available() else "Redis unavailable, revocation disabled"

    return HealthResponse(
        status=status,
        redis_available=manager.is_redis_available(),
        message=message,
    )


@router.get("/metrics", response_model=RevocationMetricsResponse)
async def get_revocation_metrics(manager: TokenRevocationManager = Depends(get_revocation_manager)):
    """Get revocation metrics and statistics."""
    metrics = manager.get_metrics()
    return RevocationMetricsResponse(
        total_revoked=metrics.total_revoked,
        active_revocations=metrics.active_revocations,
        revoked_by_reason=metrics.revoked_by_reason,
        bulk_revocations=metrics.bulk_revocations,
        failed_revocations=metrics.failed_revocations,
        redis_available=manager.is_redis_available(),
    )


# ============================================================================
# Single Token Operations
# ============================================================================


@router.post("/revoke", response_model=BulkActionResponse)
async def revoke_token(
    req: RevokeTokenRequest,
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """
    Revoke a single token by JTI.

    This immediately adds the token to the blacklist, preventing its use.
    """
    if not manager.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Token revocation service unavailable (Redis offline)",
        )

    try:
        reason = RevocationReason(req.reason)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid revocation reason. Valid reasons: {[r.value for r in RevocationReason]}",
        )

    # Calculate expires_at based on default token TTL (1 hour)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    success = manager.revoke_token(
        jti=req.jti,
        user_id=req.user_id,
        reason=reason,
        expires_at=expires_at,
        metadata=req.metadata or {},
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke token",
        )

    return BulkActionResponse(
        success=True,
        count=1,
        details=f"Token {req.jti} revoked ({reason.value})",
    )


@router.get("/status/{jti}", response_model=RevocationStatusResponse)
async def check_token_status(
    jti: str = Path(..., description="JWT ID to check"),
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """Check if a token is revoked."""
    is_revoked = manager.is_revoked(jti)

    if is_revoked:
        record = manager.get_revocation(jti)
        return RevocationStatusResponse(
            is_revoked=True,
            record=RevocationRecordResponse(**record.to_dict()) if record else None,
        )
    else:
        return RevocationStatusResponse(is_revoked=False, record=None)


@router.get("/{jti}", response_model=RevocationRecordResponse)
async def get_revocation_record(
    jti: str = Path(..., description="JWT ID"),
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """Get detailed revocation record for a token."""
    record = manager.get_revocation(jti)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Token {jti} is not revoked",
        )

    return RevocationRecordResponse(**record.to_dict())


@router.post("/restore", response_model=BulkActionResponse)
async def restore_token(
    req: UnrevokeTokenRequest,
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """
    Restore a revoked token (remove from blacklist).

    Use carefully - this allows a previously revoked token to be used again.
    """
    if not manager.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Token revocation service unavailable",
        )

    success = manager.unrevoke_token(req.jti)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Token {req.jti} is not revoked or could not be restored",
        )

    return BulkActionResponse(
        success=True,
        count=1,
        details=f"Token {req.jti} restored",
    )


# ============================================================================
# Bulk Operations
# ============================================================================


@router.post("/revoke/user", response_model=BulkActionResponse)
async def revoke_user_tokens(
    req: RevokeUserTokensRequest,
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """
    Revoke all tokens for a user.

    Optionally keep one token active (useful for 'logout everywhere except this device').
    """
    if not manager.is_redis_available():
        raise HTTPException(
            status_code=503,
            detail="Token revocation service unavailable",
        )

    try:
        reason = RevocationReason(req.reason)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid revocation reason",
        )

    if req.except_jti:
        count = manager.revoke_tokens_except(
            user_id=req.user_id,
            keep_jti=req.except_jti,
            reason=reason,
        )
    else:
        count = manager.revoke_user_tokens(
            user_id=req.user_id,
            reason=reason,
            metadata=req.metadata or {},
        )

    return BulkActionResponse(
        success=True,
        count=count,
        details=f"Revoked {count} tokens for user {req.user_id}",
    )


@router.get("/user/{user_id}", response_model=UserRevocationsResponse)
async def get_user_revocations(
    user_id: str = Path(..., description="User ID"),
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """Get all revoked tokens for a user."""
    revocations = manager.get_revocations_for_user(user_id)
    records = [RevocationRecordResponse(**r.to_dict()) for r in revocations]

    return UserRevocationsResponse(
        user_id=user_id,
        total=len(records),
        revocations=records,
    )


# ============================================================================
# Bulk Cleanup
# ============================================================================


@router.post("/cleanup/expired", response_model=BulkActionResponse)
async def cleanup_expired_revocations(
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """
    Clean up expired revocation records.

    Redis automatically handles TTL expiration, but this endpoint can be called
    to manually trigger cleanup (mainly for metrics).
    """
    count = manager.cleanup_expired()

    return BulkActionResponse(
        success=True,
        count=count,
        details="Cleanup complete (Redis handles expiration automatically)",
    )


# ============================================================================
# Admin Operations
# ============================================================================


@router.delete("/metrics/reset", response_model=Dict)
async def reset_metrics(
    manager: TokenRevocationManager = Depends(get_revocation_manager),
):
    """Reset revocation metrics to zero."""
    manager.reset_metrics()
    return {"success": True, "message": "Metrics reset"}

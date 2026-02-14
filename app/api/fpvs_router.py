"""
FPVS (Forge Production Verification System) Endpoints for DataForge

Standardized health, readiness, and version endpoints per FPVS spec.
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["fpvs"])

# Service version (should match main.py)
SERVICE_VERSION = "1.0.0"

# FPVS Schema Version - tracks the schema contract version
FPVS_SCHEMA_VERSION = "1.0.0"


# =============================================================================
# Response Models
# =============================================================================

class HealthResponse(BaseModel):
    """Liveness check response - minimal, always fast"""
    status: str = Field(default="ok", description="Service status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class DependencyStatus(BaseModel):
    """Individual dependency health status"""
    status: str = Field(..., description="ok, degraded, or error")
    latency_ms: Optional[int] = Field(None, description="Check latency in ms")
    error: Optional[str] = Field(None, description="Error message if status is error")


class ReadyResponse(BaseModel):
    """Readiness check response with dependency status"""
    status: str = Field(..., description="ready, degraded, or unavailable")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    version: str = Field(..., description="Service version")
    correlation_id: str = Field(..., description="Request correlation ID")
    dependencies: dict[str, DependencyStatus] = Field(
        ..., description="Dependency check results"
    )


class VersionResponse(BaseModel):
    """Service version and build metadata"""
    service_name: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Semantic version")
    build_sha: str = Field(..., description="Git commit SHA")
    deployed_at: str = Field(..., description="Deployment timestamp")
    schema_version: str = Field(..., description="FPVS schema contract version")
    python_version: str = Field(..., description="Python runtime version")
    alembic_revision: Optional[str] = Field(None, description="Current Alembic migration revision")


# =============================================================================
# Dependency Check Helpers
# =============================================================================

async def check_database() -> DependencyStatus:
    """Check PostgreSQL database connectivity"""
    try:
        from sqlalchemy import text
        from app.database import SessionLocal

        start = asyncio.get_event_loop().time()
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        latency_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        return DependencyStatus(status="ok", latency_ms=latency_ms)
    except Exception as e:
        return DependencyStatus(status="error", error=str(e))


async def check_pgvector() -> DependencyStatus:
    """Check pgvector extension availability"""
    try:
        from sqlalchemy import text
        from app.database import SessionLocal

        start = asyncio.get_event_loop().time()
        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            row = result.fetchone()
            if not row:
                return DependencyStatus(
                    status="error", error="pgvector extension not installed"
                )
        finally:
            db.close()
        latency_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        return DependencyStatus(status="ok", latency_ms=latency_ms)
    except Exception as e:
        return DependencyStatus(status="error", error=str(e))


async def check_redis() -> DependencyStatus:
    """Check Redis connectivity"""
    try:
        from app.utils.redis_utils import get_redis_client

        start = asyncio.get_event_loop().time()
        redis = await get_redis_client()
        if not redis:
            return DependencyStatus(status="degraded", error="Redis not configured")

        await redis.ping()
        latency_ms = int((asyncio.get_event_loop().time() - start) * 1000)
        return DependencyStatus(status="ok", latency_ms=latency_ms)
    except Exception as e:
        return DependencyStatus(status="degraded", error=str(e))


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Lightweight liveness probe. Returns 200 if process is alive.",
)
async def health_check() -> HealthResponse:
    """
    Level 0: Liveness check (lightweight, always safe)

    - Always returns 200 if the process is running
    - No dependency checks
    - Response time < 500ms
    - Safe to call frequently (every 10s)
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness check",
    description="Validates service can fulfill its contract by checking dependencies.",
)
async def readiness_check(
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
) -> ReadyResponse:
    """
    Level 1: Readiness check (validates dependencies)

    Checks:
    - Database connectivity (PostgreSQL)
    - pgvector extension availability
    - Redis connectivity (optional)

    Returns:
    - ready: All critical dependencies healthy
    - degraded: Optional dependencies unhealthy or high latency
    - unavailable: Critical dependencies unavailable
    """
    import uuid

    # Get correlation ID from header or request state or generate new
    correlation_id = x_correlation_id
    if not correlation_id and hasattr(request.state, "correlation_id"):
        correlation_id = request.state.correlation_id
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Run all checks concurrently
    db_check, pgvector_check, redis_check = await asyncio.gather(
        check_database(),
        check_pgvector(),
        check_redis(),
        return_exceptions=True
    )

    # Handle exceptions from gather
    if isinstance(db_check, Exception):
        db_check = DependencyStatus(status="error", error=str(db_check))
    if isinstance(pgvector_check, Exception):
        pgvector_check = DependencyStatus(status="error", error=str(pgvector_check))
    if isinstance(redis_check, Exception):
        redis_check = DependencyStatus(status="degraded", error=str(redis_check))

    dependencies = {
        "database": db_check,
        "pgvector": pgvector_check,
        "redis": redis_check,
    }

    # Determine overall status
    # Critical: database, pgvector
    # Optional: redis
    critical_checks = ["database", "pgvector"]

    has_critical_errors = any(
        dependencies[name].status == "error"
        for name in critical_checks
    )
    has_any_errors = any(
        dep.status == "error" for dep in dependencies.values()
    )
    has_degraded = any(
        dep.status == "degraded" for dep in dependencies.values()
    )

    if has_critical_errors:
        status = "unavailable"
    elif has_any_errors or has_degraded:
        status = "degraded"
    else:
        status = "ready"

    return ReadyResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=SERVICE_VERSION,
        correlation_id=correlation_id,
        dependencies=dependencies,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Service version",
    description="Service metadata and build information.",
)
async def version_info() -> VersionResponse:
    """
    Service version and build metadata.

    Build SHA and deployment time are populated from Render environment variables:
    - RENDER_GIT_COMMIT: Git SHA of deployed commit
    - RENDER_DEPLOY_TIME: ISO 8601 timestamp of deployment
    """
    alembic_rev = None
    try:
        from sqlalchemy import text
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            if row:
                alembic_rev = row[0]
        finally:
            db.close()
    except Exception:
        pass

    return VersionResponse(
        service_name="dataforge",
        version=SERVICE_VERSION,
        build_sha=os.getenv("RENDER_GIT_COMMIT", "unknown"),
        deployed_at=os.getenv("RENDER_DEPLOY_TIME", "unknown"),
        schema_version=FPVS_SCHEMA_VERSION,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        alembic_revision=alembic_rev,
    )

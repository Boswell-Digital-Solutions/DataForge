"""Global Rate Limits — FastAPI router.

Provides atomic check-and-increment for cross-run XAI/MAID rate limiting.
ForgeAgents calls POST /check before each provider call.

Prefix: /api/v1/rate-limits
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rate_limits_models import GlobalRateLimit
from app.models.rate_limits_schemas import (
    RateLimitCheckRequest,
    RateLimitCheckResponse,
    RateLimitConfigUpsert,
    RateLimitStatusResponse,
    RateLimitSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rate-limits", tags=["rate-limits"])

# Default window: 30 days (monthly)
DEFAULT_WINDOW_SECONDS = 30 * 24 * 3600
DEFAULT_MAX_COUNT = {"xai": 5000, "maid": 2000}
DEFAULT_MAX_COST = {"xai": 300.0, "maid": 100.0}


def _get_or_create_window(
    db: Session, provider: str, window_seconds: int = DEFAULT_WINDOW_SECONDS
) -> GlobalRateLimit:
    """Get the current rate-limit window, creating one if needed.

    Uses SELECT FOR UPDATE to prevent concurrent window creation.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)

    # Try to find an active window (SELECT FOR UPDATE for atomicity)
    row = (
        db.query(GlobalRateLimit)
        .filter(
            GlobalRateLimit.provider == provider,
            GlobalRateLimit.window_start >= cutoff,
        )
        .with_for_update()
        .order_by(GlobalRateLimit.window_start.desc())
        .first()
    )

    if row is not None:
        return row

    # Create a new window
    defaults = DEFAULT_MAX_COUNT.get(provider, 5000)
    cost_default = DEFAULT_MAX_COST.get(provider, 300.0)

    row = GlobalRateLimit(
        provider=provider,
        window_start=now,
        window_duration_seconds=window_seconds,
        current_count=0,
        max_count=defaults,
        cost_usd=Decimal("0"),
        max_cost_usd=Decimal(str(cost_default)),
        metadata_={},
    )
    db.add(row)
    db.flush()
    return row


def _build_response(row: GlobalRateLimit, allowed: bool, reason: str) -> RateLimitCheckResponse:
    """Build a RateLimitCheckResponse from a rate-limit row."""
    remaining = max(0, row.max_count - row.current_count)
    utilization = row.current_count / row.max_count if row.max_count > 0 else 1.0
    return RateLimitCheckResponse(
        allowed=allowed,
        provider=row.provider,
        current_count=row.current_count,
        max_count=row.max_count,
        requests_remaining=remaining,
        utilization=round(min(utilization, 1.0), 4),
        cost_usd=float(row.cost_usd),
        max_cost_usd=float(row.max_cost_usd) if row.max_cost_usd else None,
        reason=reason,
    )


# ── Endpoints ────────────────────────────────────────────────


@router.post("/check", response_model=RateLimitCheckResponse)
def check_and_increment(body: RateLimitCheckRequest, db: Session = Depends(get_db)):
    """Atomically check and increment the rate limit counter.

    Uses SELECT FOR UPDATE for row-level locking to prevent races.
    Returns allow/deny with current usage stats.
    """
    provider = body.provider.value
    row = _get_or_create_window(db, provider)

    # Check request count
    if row.current_count >= row.max_count:
        db.commit()
        logger.warning(
            "rate_limit_denied",
            extra={"provider": provider, "count": row.current_count, "max": row.max_count},
        )
        return _build_response(row, allowed=False, reason=f"Monthly {provider.upper()} budget exhausted ({row.current_count}/{row.max_count})")

    # Check cost cap
    if row.max_cost_usd and row.cost_usd + Decimal(str(body.estimated_cost_usd)) > row.max_cost_usd:
        db.commit()
        logger.warning(
            "rate_limit_cost_denied",
            extra={"provider": provider, "cost": float(row.cost_usd), "max": float(row.max_cost_usd)},
        )
        return _build_response(row, allowed=False, reason=f"Cost cap exceeded (${float(row.cost_usd):.2f}/${float(row.max_cost_usd):.2f})")

    # Increment
    row.current_count += 1
    row.cost_usd += Decimal(str(body.estimated_cost_usd))
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    return _build_response(row, allowed=True, reason="OK")


@router.get("/status", response_model=RateLimitSummaryResponse)
def get_status(db: Session = Depends(get_db)):
    """Get current rate-limit status for all providers."""
    providers = []
    for provider_name in ("xai", "maid"):
        row = _get_or_create_window(db, provider_name)
        remaining = max(0, row.max_count - row.current_count)
        utilization = row.current_count / row.max_count if row.max_count > 0 else 0.0
        providers.append(RateLimitStatusResponse(
            id=row.id,
            provider=row.provider,
            window_start=row.window_start,
            window_duration_seconds=row.window_duration_seconds,
            current_count=row.current_count,
            max_count=row.max_count,
            requests_remaining=remaining,
            utilization=round(min(utilization, 1.0), 4),
            cost_usd=float(row.cost_usd),
            max_cost_usd=float(row.max_cost_usd) if row.max_cost_usd else None,
            metadata=row.metadata_ or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        ))
    db.commit()
    return RateLimitSummaryResponse(providers=providers, total_providers=len(providers))


@router.get("/status/{provider}", response_model=RateLimitStatusResponse)
def get_provider_status(provider: str, db: Session = Depends(get_db)):
    """Get rate-limit status for a specific provider."""
    if provider not in ("xai", "maid"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    row = _get_or_create_window(db, provider)
    remaining = max(0, row.max_count - row.current_count)
    utilization = row.current_count / row.max_count if row.max_count > 0 else 0.0
    db.commit()

    return RateLimitStatusResponse(
        id=row.id,
        provider=row.provider,
        window_start=row.window_start,
        window_duration_seconds=row.window_duration_seconds,
        current_count=row.current_count,
        max_count=row.max_count,
        requests_remaining=remaining,
        utilization=round(min(utilization, 1.0), 4),
        cost_usd=float(row.cost_usd),
        max_cost_usd=float(row.max_cost_usd) if row.max_cost_usd else None,
        metadata=row.metadata_ or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.put("/config", response_model=RateLimitCheckResponse)
def upsert_config(body: RateLimitConfigUpsert, db: Session = Depends(get_db)):
    """Create or update rate limit configuration for a provider.

    Updates max_count and max_cost_usd for the current window.
    """
    provider = body.provider.value
    row = _get_or_create_window(db, provider, body.window_duration_seconds)

    row.max_count = body.max_count
    row.window_duration_seconds = body.window_duration_seconds
    if body.max_cost_usd is not None:
        row.max_cost_usd = Decimal(str(body.max_cost_usd))
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    return _build_response(row, allowed=row.current_count < row.max_count, reason="Config updated")

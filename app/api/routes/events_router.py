"""
BuildGuard Events API Router

POST /api/v1/events - Accept BuildGuard metrics events
GET /api/v1/events - List events with pagination
GET /api/v1/events/stats - Dashboard statistics
GET /api/v1/events/profiles - Profile statistics
"""

from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth.api_keys import validate_api_key
from app.database import get_db
from app.logging_config import get_logger
from app.models.authorforge_analytics_schemas import (
    AuthorForgeAnalyticsEnvelopeV1,
    AuthorForgeAnalyticsIngestResponse,
)
from app.models.authorforge_analytics_models import AuthorForgeAnalyticsRecord
from app.models.buildguard_models import BuildGuardEvent, BuildGuardProfileStats
from app.models.buildguard_schemas import (
    BuildGuardMetricsEventCreate,
    BuildGuardEventResponse,
    BuildGuardProfileStatsResponse,
    BuildGuardDashboardStats,
    EventsListResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify API key from Authorization header.

    For now, accepts any Bearer token. In production, validate against
    a list of authorized API keys.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization[7:]  # Strip "Bearer "
    if not token:
        raise HTTPException(status_code=401, detail="API key required")

    # TODO: Validate token against authorized keys
    return token


def verify_authorforge_analytics_key(
    authorization: Optional[str] = Header(None),
) -> str:
    """Require a database-backed key scoped only to AuthorForge analytics."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Analytics API key required")
    token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Analytics API key required")
    try:
        key_info = validate_api_key(token)
    except Exception:
        logger.error("authorforge_analytics_auth_failed category=database")
        raise HTTPException(status_code=503, detail="Analytics authorization unavailable")
    if key_info is None:
        raise HTTPException(status_code=401, detail="Invalid analytics API key")

    metadata = key_info.metadata if isinstance(key_info.metadata, dict) else {}
    scopes = metadata.get("scopes")
    if (
        metadata.get("service") != "authorforge"
        or not isinstance(scopes, list)
        or "analytics:write" not in scopes
    ):
        raise HTTPException(status_code=403, detail="AuthorForge analytics scope required")
    return key_info.id


@router.post("", status_code=201)
async def create_event(
    event: BuildGuardMetricsEventCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Create a new BuildGuard metrics event.

    This endpoint receives verdict events from the GRR BuildGuard quality gate.
    Events are validated against the schema and stored for BI and audit purposes.
    """
    logger.info(
        "Received BuildGuard event",
        extra={
            "verdict_id": event.verdict_id,
            "event_type": event.event_type,
            "pass": event.metrics.pass_,
        }
    )

    # Parse timestamp
    try:
        event_timestamp = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    # Create event record
    db_event = BuildGuardEvent(
        schema_version=event.schema_version,
        event_type=event.event_type,
        timestamp=event_timestamp,
        verdict_id=event.verdict_id,
        pass_status=event.metrics.pass_,
        blocked_count=event.metrics.blocked_count,
        total_findings=event.metrics.total_findings,
        triaged_count=event.metrics.triaged_count,
        avg_triage_lag_hours=event.metrics.avg_triage_lag_hours,
        p50_triage_lag_hours=event.metrics.p50_triage_lag_hours,
        p95_triage_lag_hours=event.metrics.p95_triage_lag_hours,
        profile_hash=event.metrics.profile_hash,
        evaluation_duration_ms=event.metrics.evaluation_duration_ms,
        raw_payload=event.model_dump(),
    )

    try:
        db.add(db_event)
        db.flush()

        # Update profile stats
        _update_profile_stats(db, event)

        db.commit()
        db.refresh(db_event)

        logger.info(
            "BuildGuard event stored",
            extra={
                "event_id": str(db_event.id),
                "verdict_id": event.verdict_id,
            }
        )

        return {
            "id": str(db_event.id),
            "verdict_id": event.verdict_id,
            "status": "created",
        }

    except IntegrityError as e:
        db.rollback()
        if "verdict_id" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"Event with verdict_id {event.verdict_id} already exists"
            )
        raise HTTPException(status_code=500, detail="Database error")


@router.post(
    "/authorforge-analytics",
    response_model=AuthorForgeAnalyticsIngestResponse,
    status_code=202,
)
def ingest_authorforge_analytics(
    envelope: AuthorForgeAnalyticsEnvelopeV1,
    db: Session = Depends(get_db),
    _api_key_id: str = Depends(verify_authorforge_analytics_key),
) -> AuthorForgeAnalyticsIngestResponse:
    """Persist one minimized analytics event; content-bearing fields never validate."""
    digest = envelope.event_digest()
    existing = db.get(AuthorForgeAnalyticsRecord, envelope.event_id)
    if existing is not None:
        if existing.event_digest != digest:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "authorforge_analytics_identity_conflict",
                    "event_id": str(envelope.event_id),
                },
            )
        return AuthorForgeAnalyticsIngestResponse(
            event_id=envelope.event_id,
            status="duplicate",
        )

    record = AuthorForgeAnalyticsRecord(
        event_id=envelope.event_id,
        event_digest=digest,
        canonical_bytes=len(envelope.canonical_bytes()),
        schema_version=envelope.schema_version,
        policy_version=envelope.policy_version,
        occurred_at=envelope.occurred_at,
        event_type=envelope.event_type,
        dimensions=envelope.bounded_dimensions(),
        metrics=envelope.bounded_metrics(),
    )
    try:
        db.add(record)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(AuthorForgeAnalyticsRecord, envelope.event_id)
        if existing is None:
            logger.error("authorforge_analytics_ingest_failed category=database")
            raise HTTPException(
                status_code=503,
                detail="Analytics persistence unavailable",
            )
        if existing.event_digest != digest:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "authorforge_analytics_identity_conflict",
                    "event_id": str(envelope.event_id),
                },
            )
        return AuthorForgeAnalyticsIngestResponse(
            event_id=envelope.event_id,
            status="duplicate",
        )
    except SQLAlchemyError:
        db.rollback()
        logger.error("authorforge_analytics_ingest_failed category=database")
        raise HTTPException(status_code=503, detail="Analytics persistence unavailable")

    logger.info(
        "authorforge_analytics_ingested",
        extra={"event_id": str(envelope.event_id), "event_type": envelope.event_type},
    )
    return AuthorForgeAnalyticsIngestResponse(
        event_id=envelope.event_id,
        status="accepted",
    )


def _update_profile_stats(db: Session, event: BuildGuardMetricsEventCreate):
    """Update aggregated profile statistics."""
    profile_hash = event.metrics.profile_hash

    stats = db.query(BuildGuardProfileStats).filter(
        BuildGuardProfileStats.profile_hash == profile_hash
    ).first()

    if stats is None:
        # Create new profile stats
        stats = BuildGuardProfileStats(
            profile_hash=profile_hash,
            total_verdicts=1,
            pass_count=1 if event.metrics.pass_ else 0,
            fail_count=0 if event.metrics.pass_ else 1,
            total_findings_evaluated=event.metrics.total_findings,
            total_blocked=event.metrics.blocked_count,
            avg_triage_lag_hours_overall=event.metrics.avg_triage_lag_hours,
            first_seen=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        db.add(stats)
    else:
        # Update existing stats
        stats.total_verdicts += 1
        if event.metrics.pass_:
            stats.pass_count += 1
        else:
            stats.fail_count += 1
        stats.total_findings_evaluated += event.metrics.total_findings
        stats.total_blocked += event.metrics.blocked_count

        # Rolling average for triage lag
        if event.metrics.avg_triage_lag_hours is not None:
            if stats.avg_triage_lag_hours_overall is None:
                stats.avg_triage_lag_hours_overall = event.metrics.avg_triage_lag_hours
            else:
                # Simple running average
                n = stats.total_verdicts
                stats.avg_triage_lag_hours_overall = (
                    (stats.avg_triage_lag_hours_overall * (n - 1) + event.metrics.avg_triage_lag_hours) / n
                )

        stats.last_seen = datetime.now(UTC)


@router.get("", response_model=EventsListResponse)
async def list_events(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    profile_hash: Optional[str] = Query(None, description="Filter by profile hash"),
    pass_status: Optional[bool] = Query(None, description="Filter by pass/fail"),
    since: Optional[datetime] = Query(None, description="Events after this timestamp"),
):
    """
    List BuildGuard events with pagination and filters.
    """
    query = db.query(BuildGuardEvent)

    # Apply filters
    if profile_hash:
        query = query.filter(BuildGuardEvent.profile_hash == profile_hash)
    if pass_status is not None:
        query = query.filter(BuildGuardEvent.pass_status == pass_status)
    if since:
        query = query.filter(BuildGuardEvent.timestamp >= since)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    events = query.order_by(desc(BuildGuardEvent.timestamp)).offset(offset).limit(page_size).all()

    return EventsListResponse(
        events=[BuildGuardEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(events)) < total,
    )


@router.get("/stats", response_model=BuildGuardDashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get aggregated dashboard statistics for BuildGuard.
    """
    # Overall counts
    total = db.query(func.count(BuildGuardEvent.id)).scalar() or 0
    pass_count = db.query(func.count(BuildGuardEvent.id)).filter(
        BuildGuardEvent.pass_status == True
    ).scalar() or 0
    fail_count = total - pass_count

    # Last 24 hours
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    recent_total = db.query(func.count(BuildGuardEvent.id)).filter(
        BuildGuardEvent.timestamp >= cutoff
    ).scalar() or 0
    recent_pass = db.query(func.count(BuildGuardEvent.id)).filter(
        BuildGuardEvent.timestamp >= cutoff,
        BuildGuardEvent.pass_status == True
    ).scalar() or 0

    # Triage lag averages
    avg_lag = db.query(func.avg(BuildGuardEvent.avg_triage_lag_hours)).scalar()
    p50_lag = db.query(func.avg(BuildGuardEvent.p50_triage_lag_hours)).scalar()
    p95_lag = db.query(func.avg(BuildGuardEvent.p95_triage_lag_hours)).scalar()

    # Top failing profiles (by fail count, last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    top_failing = db.query(BuildGuardProfileStats).filter(
        BuildGuardProfileStats.last_seen >= week_ago,
        BuildGuardProfileStats.fail_count > 0
    ).order_by(desc(BuildGuardProfileStats.fail_count)).limit(5).all()

    return BuildGuardDashboardStats(
        total_verdicts=total,
        total_pass=pass_count,
        total_fail=fail_count,
        overall_pass_rate=pass_count / total if total > 0 else 0.0,
        verdicts_last_24h=recent_total,
        pass_rate_last_24h=recent_pass / recent_total if recent_total > 0 else 0.0,
        avg_triage_lag_hours=avg_lag,
        p50_triage_lag_hours=p50_lag,
        p95_triage_lag_hours=p95_lag,
        top_failing_profiles=[
            BuildGuardProfileStatsResponse(
                profile_hash=p.profile_hash,
                total_verdicts=p.total_verdicts,
                pass_count=p.pass_count,
                fail_count=p.fail_count,
                pass_rate=p.pass_rate,
                total_findings_evaluated=p.total_findings_evaluated,
                total_blocked=p.total_blocked,
                avg_triage_lag_hours_overall=p.avg_triage_lag_hours_overall,
                first_seen=p.first_seen,
                last_seen=p.last_seen,
            )
            for p in top_failing
        ],
    )


@router.get("/profiles", response_model=list[BuildGuardProfileStatsResponse])
async def list_profiles(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Max profiles to return"),
):
    """
    List profile statistics ordered by most recent activity.
    """
    profiles = db.query(BuildGuardProfileStats).order_by(
        desc(BuildGuardProfileStats.last_seen)
    ).limit(limit).all()

    return [
        BuildGuardProfileStatsResponse(
            profile_hash=p.profile_hash,
            total_verdicts=p.total_verdicts,
            pass_count=p.pass_count,
            fail_count=p.fail_count,
            pass_rate=p.pass_rate,
            total_findings_evaluated=p.total_findings_evaluated,
            total_blocked=p.total_blocked,
            avg_triage_lag_hours_overall=p.avg_triage_lag_hours_overall,
            first_seen=p.first_seen,
            last_seen=p.last_seen,
        )
        for p in profiles
    ]


@router.get("/{verdict_id}", response_model=BuildGuardEventResponse)
async def get_event(verdict_id: str, db: Session = Depends(get_db)):
    """
    Get a specific BuildGuard event by verdict ID.
    """
    event = db.query(BuildGuardEvent).filter(
        BuildGuardEvent.verdict_id == verdict_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return BuildGuardEventResponse.model_validate(event)

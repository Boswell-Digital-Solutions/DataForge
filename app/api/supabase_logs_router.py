"""
Supabase log events — read-only FastAPI router.

Serves the redacted Supabase log mirror to ForgeAgents' Sentinel for anomaly
sweeps (brute-force, after-hours, bulk-mutation). Read-only by design: rows are
written exclusively by the scheduled poller (scripts/poll_supabase_logs.py), and
DataForge owns the durable copy.

Prefix: /api/v1/supabase-logs
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.supabase_log_models import SupabaseLogEvent
from app.models.supabase_log_schemas import (
    SupabaseLogEventListResponse,
    SupabaseLogEventResponse,
)

router = APIRouter(prefix="/api/v1/supabase-logs", tags=["supabase-logs"])

MAX_LIMIT = 5000


@router.get("/events", response_model=SupabaseLogEventListResponse)
def list_events(
    since: datetime | None = Query(None, description="Only events at/after this time (ISO-8601)."),
    until: datetime | None = Query(None, description="Only events before this time (ISO-8601)."),
    category: str | None = Query(None, description="Filter by classification (auth, http_error, ...)."),
    log_type: str | None = Query(None, description="Filter by Supabase log source (auth, postgres, ...)."),
    limit: int = Query(500, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> SupabaseLogEventListResponse:
    """List redacted Supabase log events, most recent first.

    Sentinel calls this with a ``since`` window each sweep; the rows are already
    safe to read (no tokens, hashed identities, scrubbed messages).
    """
    q = db.query(SupabaseLogEvent)
    if since is not None:
        q = q.filter(SupabaseLogEvent.event_time >= since)
    if until is not None:
        q = q.filter(SupabaseLogEvent.event_time < until)
    if category:
        q = q.filter(SupabaseLogEvent.category == category)
    if log_type:
        q = q.filter(SupabaseLogEvent.log_type == log_type)

    total = q.count()
    items = (
        q.order_by(SupabaseLogEvent.event_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return SupabaseLogEventListResponse(
        items=[SupabaseLogEventResponse.model_validate(row) for row in items],
        total=total,
    )

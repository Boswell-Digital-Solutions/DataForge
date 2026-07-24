"""
Supabase log events — DataForge durable persistence.

A redacted, allow-listed mirror of security/operational Supabase log entries,
pulled on a schedule by ``scripts/poll_supabase_logs.py``. DataForge owns this
durable copy (CRITICAL RULE: all durable state lives here); ForgeAgents'
Sentinel reads it for anomaly sweeps but never writes it.

Sensitive fields are stripped at ingest (see ``app/utils/supabase_log_ingest``),
so every row here is already safe to read and forward.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class SupabaseLogEvent(Base):
    """One redacted Supabase log entry kept as durable Forge evidence."""

    __tablename__ = "supabase_log_events"

    # The Supabase log id (UUID string) — primary key so re-pulling an
    # overlapping window is idempotent via INSERT ... ON CONFLICT DO NOTHING.
    id = Column(String(64), primary_key=True)

    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    log_type = Column(String(40), nullable=True, index=True, comment="auth, postgrest, postgres, edge, ...")
    level = Column(String(20), nullable=True, comment="error, warning, fatal, success, ...")
    status = Column(String(20), nullable=True, comment="HTTP/postgres status code")
    method = Column(String(10), nullable=True)
    pathname = Column(String(500), nullable=True)
    latency_ms = Column(Float, nullable=True)

    category = Column(
        String(30), nullable=True,
        comment="auth, http_error, error, warning, postgres_op, other",
    )
    # event_message after PII/credential scrubbing.
    message = Column(Text, nullable=True)
    # Allow-listed structural fields only (safe headers, regions, auth_user_hash).
    event_metadata = Column(JSONB, nullable=False, default=dict)

    source = Column(String(20), nullable=False, default="supabase")
    redacted = Column(Boolean, nullable=False, default=True)
    source_cursor = Column(String(64), nullable=True, comment="poll window this row arrived in")
    ingested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Sentinel queries the recent window by category (e.g. auth failures).
        Index("ix_supabase_log_events_category_time", "category", "event_time"),
    )

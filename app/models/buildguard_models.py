"""
BuildGuard Telemetry Models

SQLAlchemy models for storing BuildGuard verdict events and metrics.
Supports the GRR BuildGuard Phase D quality gate system.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, JSON, Text,
    Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class BuildGuardEvent(Base):
    """
    BuildGuard metrics event storage.

    Stores verdict events from the GRR BuildGuard quality gate system
    for business intelligence and audit trail purposes.
    """
    __tablename__ = "buildguard_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Event metadata
    schema_version = Column(String(10), nullable=False, default="v1")
    event_type = Column(String(50), nullable=False)  # e.g., "buildguard.verdict"
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Verdict reference
    verdict_id = Column(String(36), nullable=False, unique=True, index=True)

    # Core metrics
    pass_status = Column(Boolean, nullable=False)
    blocked_count = Column(Integer, nullable=False, default=0)
    total_findings = Column(Integer, nullable=False, default=0)
    triaged_count = Column(Integer, nullable=False, default=0)

    # Triage lag metrics (nullable for verdicts with no triaged findings)
    avg_triage_lag_hours = Column(Float, nullable=True)
    p50_triage_lag_hours = Column(Float, nullable=True)
    p95_triage_lag_hours = Column(Float, nullable=True)

    # Profile tracking
    profile_hash = Column(String(64), nullable=False, index=True)

    # Performance
    evaluation_duration_ms = Column(Integer, nullable=False, default=0)

    # Raw event payload for audit
    raw_payload = Column(JSON, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint('blocked_count >= 0', name='check_blocked_count_positive'),
        CheckConstraint('total_findings >= 0', name='check_total_findings_positive'),
        CheckConstraint('triaged_count >= 0', name='check_triaged_count_positive'),
        CheckConstraint('evaluation_duration_ms >= 0', name='check_duration_positive'),
        Index('ix_buildguard_events_timestamp', 'timestamp'),
        Index('ix_buildguard_events_pass_status', 'pass_status'),
        Index('ix_buildguard_events_profile_timestamp', 'profile_hash', 'timestamp'),
    )

    def __repr__(self):
        return f"<BuildGuardEvent(verdict_id={self.verdict_id}, pass={self.pass_status})>"


class BuildGuardProfileStats(Base):
    """
    Aggregated statistics per CI profile.

    Materialized view pattern for dashboard queries.
    Updated on each new verdict event.
    """
    __tablename__ = "buildguard_profile_stats"

    # Primary key is the profile hash
    profile_hash = Column(String(64), primary_key=True)

    # Aggregate counts
    total_verdicts = Column(Integer, nullable=False, default=0)
    pass_count = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)

    # Aggregate metrics
    total_findings_evaluated = Column(Integer, nullable=False, default=0)
    total_blocked = Column(Integer, nullable=False, default=0)

    # Average triage lag across all verdicts
    avg_triage_lag_hours_overall = Column(Float, nullable=True)

    # Timestamps
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Pass rate (computed)
    @property
    def pass_rate(self) -> float:
        if self.total_verdicts == 0:
            return 0.0
        return self.pass_count / self.total_verdicts

    def __repr__(self):
        return f"<BuildGuardProfileStats(hash={self.profile_hash[:8]}..., pass_rate={self.pass_rate:.1%})>"

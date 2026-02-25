"""
Sentinel Agent — DataForge models.

Tables:
  - sentinel_sweeps: Health sweep records (light/deep)
  - sentinel_healing_events: Healing actions and outcomes
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class SentinelSweep(Base):
    """A health sweep (diagnostic run) across ecosystem services."""
    __tablename__ = "sentinel_sweeps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sweep_type = Column(
        String(20), nullable=False,
        comment="light or deep",
    )
    status = Column(
        String(20), nullable=False, default="running",
        comment="running, completed, failed",
    )
    dimensions_checked = Column(JSONB, nullable=False, default=list, comment="List of dimension IDs checked")
    findings = Column(JSONB, nullable=False, default=list, comment="Array of DimensionResult objects")
    overall_status = Column(
        String(20), nullable=False, default="unknown",
        comment="healthy, degraded, critical, unknown",
    )
    trigger = Column(String(30), nullable=False, default="scheduled", comment="scheduled, manual, anomaly")
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    healing_events = relationship("SentinelHealingEvent", back_populates="sweep", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "sweep_type IN ('light', 'deep')",
            name="ck_sentinel_sweep_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_sentinel_sweep_status",
        ),
        CheckConstraint(
            "overall_status IN ('healthy', 'degraded', 'critical', 'unknown')",
            name="ck_sentinel_sweep_overall",
        ),
    )


class SentinelHealingEvent(Base):
    """A healing action taken (or escalated) by Sentinel."""
    __tablename__ = "sentinel_healing_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sweep_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sentinel_sweeps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    playbook = Column(String(60), nullable=False, comment="e.g. restart_service, rollback_config, escalate_critical")
    tier = Column(
        String(1), nullable=False,
        comment="A = autonomous, B = supervised, C = escalation",
    )
    action = Column(String(200), nullable=False, comment="Human-readable description of the action")
    target_service = Column(String(60), nullable=True, comment="Service affected")
    outcome = Column(
        String(20), nullable=False, default="pending",
        comment="pending, success, failure, escalated, skipped",
    )
    governed = Column(Boolean, nullable=False, default=False, comment="Whether governance approval was required")
    approval_id = Column(String(100), nullable=True, comment="Governance event ID if governed")
    details = Column(JSONB, nullable=False, default=dict)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    sweep = relationship("SentinelSweep", back_populates="healing_events")

    __table_args__ = (
        CheckConstraint(
            "tier IN ('A', 'B', 'C')",
            name="ck_sentinel_healing_tier",
        ),
        CheckConstraint(
            "outcome IN ('pending', 'success', 'failure', 'escalated', 'skipped')",
            name="ck_sentinel_healing_outcome",
        ),
    )

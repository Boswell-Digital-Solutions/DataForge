"""SQLAlchemy models for BugCheck persistence.

This module provides database models for storing BugCheck runs, findings,
enrichments, and lifecycle events. DataForge is the single source of truth
for all BugCheck state.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ============================================================================
# BugCheck Run
# ============================================================================


class BugCheckRunModel(Base):
    """Database model for BugCheck runs."""

    __tablename__ = "bugcheck_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type = Column(String(50), nullable=False)  # service_run, ecosystem_run, workflow_run
    targets = Column(JSON, nullable=False)  # list of service names
    mode = Column(String(20), nullable=False)  # quick, standard, deep
    scope = Column(String(30), nullable=False)  # changed_files, package, full_repo
    commit_sha = Column(String(40), nullable=False)
    base_commit_sha = Column(String(40), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    severity_counts = Column(JSON, nullable=False, default=dict)
    gating_result = Column(String(20), nullable=False, default="pending")
    is_baseline = Column(Boolean, default=False)
    baseline_run_id = Column(UUID(as_uuid=True), nullable=True)
    triggered_by = Column(String(20), nullable=True)
    trigger_ref = Column(String(255), nullable=True)
    runtime_ms = Column(Integer, nullable=True)
    checks_run = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    findings = relationship("BugCheckFindingModel", back_populates="run", cascade="all, delete-orphan")
    progress_events = relationship("BugCheckProgressModel", back_populates="run", cascade="all, delete-orphan")


# ============================================================================
# Finding
# ============================================================================


class BugCheckFindingModel(Base):
    """Database model for BugCheck findings."""

    __tablename__ = "bugcheck_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("bugcheck_runs.id", ondelete="CASCADE"), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    severity = Column(String(5), nullable=False)  # S0, S1, S2, S3, S4
    category = Column(String(30), nullable=False)
    confidence = Column(Float, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(JSON, nullable=False)  # service, file_path, line_start, etc.
    lifecycle_state = Column(String(20), nullable=False, default="NEW")
    autofix_available = Column(Boolean, default=False)
    provenance = Column(String(100), nullable=False)  # Check ID
    rule_id = Column(String(100), nullable=True)
    suggested_fix = Column(Text, nullable=True)
    related_docs = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    first_seen_run_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    run = relationship("BugCheckRunModel", back_populates="findings")
    enrichments = relationship("BugCheckEnrichmentModel", back_populates="finding", cascade="all, delete-orphan")
    lifecycle_events = relationship("BugCheckLifecycleEventModel", back_populates="finding", cascade="all, delete-orphan")


# ============================================================================
# Enrichment
# ============================================================================


class BugCheckEnrichmentModel(Base):
    """Database model for AI enrichments on findings."""

    __tablename__ = "bugcheck_enrichments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("bugcheck_findings.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(20), nullable=False)  # maid, xai
    version = Column(Integer, nullable=False, default=1)
    enrichment_type = Column(String(50), nullable=True)
    content = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    finding = relationship("BugCheckFindingModel", back_populates="enrichments")


# ============================================================================
# Lifecycle Event
# ============================================================================


class BugCheckLifecycleEventModel(Base):
    """Database model for finding lifecycle transitions."""

    __tablename__ = "bugcheck_lifecycle_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("bugcheck_findings.id", ondelete="CASCADE"), nullable=False)
    from_state = Column(String(20), nullable=False)
    to_state = Column(String(20), nullable=False)
    actor_type = Column(String(20), nullable=False)  # user, system, agent, automation
    actor_id = Column(String(255), nullable=False)
    actor_name = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    scope = Column(String(30), nullable=True)  # For dismissals
    expires_at = Column(DateTime, nullable=True)  # For dismissals
    enrichment_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    finding = relationship("BugCheckFindingModel", back_populates="lifecycle_events")


# ============================================================================
# Progress Events
# ============================================================================


class BugCheckProgressModel(Base):
    """Database model for run progress events (for WebSocket streaming)."""

    __tablename__ = "bugcheck_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("bugcheck_runs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("BugCheckRunModel", back_populates="progress_events")

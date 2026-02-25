"""
PressForge — DataForge models.

Tables:
  - pf_journalists: Media contacts with coverage embeddings
  - pf_campaigns: Outreach campaigns linked to AuthorForge projects
  - pf_pitches: Per-journalist pitches with AI transparency metadata
  - pf_outreach_events: Send/reply/bounce event log
  - pf_coverage: Media mention tracking
  - pf_domain_reputation: Sender domain health (DMARC/SPF/DKIM)
  - pf_ai_audit_log: Immutable AI transparency audit trail
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Text,
    ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class PfJournalist(Base):
    """Media contact with coverage embedding for semantic search."""
    __tablename__ = "pf_journalists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False)
    email = Column(Text, nullable=True, comment="Encrypted at app layer in later phases")
    beat = Column(String(100), nullable=True)
    publication = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    social_links = Column(JSONB, nullable=False, default=dict)
    coverage_embedding = Column(Vector(1536), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    consent_status = Column(String(20), nullable=False, default="unknown")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pitches = relationship("PfPitch", back_populates="journalist", cascade="all, delete-orphan")
    coverage = relationship("PfCoverage", back_populates="journalist")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'do_not_contact')", name="ck_pf_journalist_status"),
        CheckConstraint("consent_status IN ('unknown', 'legitimate_interest', 'opted_in', 'opted_out')", name="ck_pf_journalist_consent"),
    )


class PfCampaign(Base):
    """Outreach campaign linked to an AuthorForge project."""
    __tablename__ = "pf_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, comment="FK concept to AuthorForge project")
    title = Column(String(300), nullable=False)
    news_angle = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="DISCOVER")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pitches = relationship("PfPitch", back_populates="campaign", cascade="all, delete-orphan")
    coverage = relationship("PfCoverage", back_populates="campaign")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DISCOVER', 'MATCH', 'GENERATE', 'LABEL', 'REVIEW', 'EXECUTE', 'MONITOR', 'COMPLETE')",
            name="ck_pf_campaign_status",
        ),
    )


class PfPitch(Base):
    """Per-journalist pitch with AI transparency metadata."""
    __tablename__ = "pf_pitches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    ai_generated = Column(Boolean, nullable=False, default=False)
    ai_rationale = Column(Text, nullable=True)
    humanity_score = Column(Float, nullable=True, comment="0.0=pure AI, 1.0=fully human-edited")
    human_verification_checksum = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="pitches")
    journalist = relationship("PfJournalist", back_populates="pitches")
    outreach_events = relationship("PfOutreachEvent", back_populates="pitch", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'reviewed', 'approved', 'sent', 'rejected')", name="ck_pf_pitch_status"),
    )


class PfOutreachEvent(Base):
    """Send/reply/bounce/open event log."""
    __tablename__ = "pf_outreach_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pitch_id = Column(UUID(as_uuid=True), ForeignKey("pf_pitches.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)
    metadata = Column(JSONB, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    pitch = relationship("PfPitch", back_populates="outreach_events")

    __table_args__ = (
        CheckConstraint("event_type IN ('send', 'reply', 'bounce', 'open')", name="ck_pf_outreach_event_type"),
    )


class PfCoverage(Base):
    """Media mention / coverage tracking."""
    __tablename__ = "pf_coverage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    article_url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    ai_sentiment_score = Column(Float, nullable=True)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    journalist = relationship("PfJournalist", back_populates="coverage")
    campaign = relationship("PfCampaign", back_populates="coverage")


class PfDomainReputation(Base):
    """Sender domain health — DMARC/SPF/DKIM status and warm-up state."""
    __tablename__ = "pf_domain_reputation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain = Column(String(255), nullable=False, unique=True)
    dmarc_status = Column(String(10), nullable=False, default="unknown")
    spf_status = Column(String(10), nullable=False, default="unknown")
    dkim_status = Column(String(10), nullable=False, default="unknown")
    warmup_state = Column(String(10), nullable=False, default="cold")
    bounce_rate = Column(Float, nullable=False, default=0.0)
    last_checked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("dmarc_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_dmarc"),
        CheckConstraint("spf_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_spf"),
        CheckConstraint("dkim_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_dkim"),
        CheckConstraint("warmup_state IN ('cold', 'warming', 'warm')", name="ck_pf_domain_warmup"),
    )


class PfAiAuditLog(Base):
    """Immutable append-only AI transparency audit trail."""
    __tablename__ = "pf_ai_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type = Column(String(50), nullable=False, comment="e.g. match, pitch_generation, subject_variants")
    model_version = Column(String(100), nullable=False)
    input_hash = Column(String(128), nullable=True)
    rationale = Column(Text, nullable=True)
    personalization_notes = Column(Text, nullable=True)
    campaign_id = Column(UUID(as_uuid=True), nullable=True)
    journalist_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

"""Dedicated durable storage for strict, content-free AuthorForge analytics."""

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuthorForgeAnalyticsRecord(Base):
    """One validated ``AuthorForgeAnalyticsEnvelope.v1`` event.

    This table is intentionally separate from both canonical ForgeEvent.v1
    telemetry and the physically retained pre-v1 events table.
    """

    __tablename__ = "authorforge_analytics_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    event_digest = Column(String(64), nullable=False)
    canonical_bytes = Column(Integer, nullable=False)
    schema_version = Column(String(64), nullable=False)
    policy_version = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    event_type = Column(String(64), nullable=False)
    dimensions = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)

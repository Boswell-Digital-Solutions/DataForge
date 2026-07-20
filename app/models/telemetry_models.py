"""ORM mapping for the canonical Forge ``events`` telemetry table."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, JSON, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class TelemetryEventRecord(Base):
    """Existing canonical telemetry record; schema created by migration 4bae83731016."""

    __tablename__ = "events"

    event_id = Column(Uuid(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    service = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    correlation_id = Column(Uuid(as_uuid=True), nullable=True)
    event_metadata = Column("metadata", JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    metrics = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_events_service", "service"),
        Index("idx_events_event_type", "event_type"),
        Index("idx_events_correlation_id", "correlation_id"),
        Index("idx_events_timestamp", "timestamp"),
        Index("idx_events_service_timestamp", "service", "timestamp"),
    )

"""ORM mapping for the shared Forge telemetry ``events`` table."""

from sqlalchemy import Column, DateTime, Index, JSON, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class TelemetryEventRecord(Base):
    """Durable generic telemetry event owned by DataForge.

    The table itself predates this ORM mapping and is created by Alembic.  The
    mapping gives the authenticated HTTP ingest boundary and tests one exact
    representation of that existing schema without changing its storage shape.
    """

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
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_events_service", "service"),
        Index("idx_events_event_type", "event_type"),
        Index("idx_events_correlation_id", "correlation_id"),
        Index("idx_events_timestamp", "timestamp"),
        Index("idx_events_service_timestamp", "service", "timestamp"),
    )

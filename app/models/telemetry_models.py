"""ORM mapping for the shared Forge telemetry ``events`` table."""

from sqlalchemy import Column, DateTime, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TelemetryEventRecord(Base):
    """Durable generic telemetry event owned by DataForge.

    The table itself predates this ORM mapping and is created by Alembic.  The
    mapping gives the authenticated HTTP ingest boundary and tests one exact
    representation of that existing schema without changing its storage shape.
    """

    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    service = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

"""
Tarcie event persistence model.

Stores friction notes and markers from Tarcie capture tool.
Append-only by design. No enrichment or analysis at ingest time.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.database import Base


class TarcieEvent(Base):
    """
    Append-only storage for Tarcie capture events.

    Events are written once and never modified.
    Analysis and enrichment happen downstream (SMITH).
    """

    __tablename__ = "tarcie_events"

    # Primary key from Tarcie (client-generated UUID)
    id = Column(PGUUID(as_uuid=True), primary_key=True)

    # Device identification
    device_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)

    # Timestamps
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    timestamp_mono_ms = Column(BigInteger, nullable=False)

    # Event data
    event_type = Column(String(32), nullable=False)  # "Note" or "Marker"
    content = Column(Text, nullable=False, default="")
    app_context = Column(String(64), nullable=False, default="General")

    # Metadata
    source_version = Column(String(32), nullable=False)

    # Server-side timestamp for when we received it
    ingested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    __table_args__ = (
        # Composite index for device + time range queries
        Index("ix_tarcie_events_device_time", "device_id", "timestamp_utc"),
        # Index for recent events across all devices
        Index("ix_tarcie_events_ingested", "ingested_at"),
    )

    def __repr__(self) -> str:
        return f"<TarcieEvent {self.id} type={self.event_type} context={self.app_context}>"

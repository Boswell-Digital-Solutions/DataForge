"""ORM mapping for canonical ForgeEvent.v1 durable storage."""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ForgeEventV1Record(Base):
    """Durable canonical Forge telemetry event owned by DataForge.

    Alembic owns the PostgreSQL checks, expression indexes, and atomic identity
    function. This mapping intentionally has no alias or
    relationship to the physically retained pre-v1 ``events`` table.
    """

    __tablename__ = "forge_events_v1"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    event_digest = Column(String(64), nullable=False)
    schema_version = Column(String(32), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    service_name = Column(Text, nullable=False)
    service_instance_id = Column(Text, nullable=True)
    environment = Column(Text, nullable=False)
    tenant_ref = Column(Text, nullable=True)
    event_type = Column(Text, nullable=False)
    severity = Column(String(16), nullable=False)
    outcome = Column(String(32), nullable=False)
    evidence_class = Column(String(16), nullable=False)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    trace_id = Column(String(32), nullable=True)
    span_id = Column(String(16), nullable=True)
    parent_span_id = Column(String(16), nullable=True)
    attributes = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    privacy_class = Column(String(16), nullable=False)
    retention_class = Column(String(16), nullable=False)
    sampled = Column(Boolean, nullable=False)
    sample_rate = Column(Float, nullable=True)
    sampling_reason = Column(String(32), nullable=False)

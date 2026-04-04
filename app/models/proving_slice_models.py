"""SQLAlchemy ORM models for the proving-slice intake surface.

Two tables:
  PSCloudIntakeRecord  — durable log of every artifact received from DataForge Local
  PSCloudReceipt       — receipt artifact emitted back after each intake decision
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class PSCloudIntakeRecord(Base):
    """One row per artifact received from DataForge Local.

    Idempotency key has a UNIQUE constraint: a second submission with the
    same key is detected here and reconciled as duplicate_reconciled
    without re-running validation.
    """

    __tablename__ = "ps_cloud_intake_records"

    intake_id = Column(String(36), primary_key=True)
    artifact_id = Column(String(36), nullable=False, index=True)
    artifact_family = Column(String(128), nullable=False, index=True)
    artifact_version = Column(Integer(), nullable=False)
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    produced_by_system = Column(String(255), nullable=False)
    lineage_root_id = Column(String(36), nullable=False, index=True)
    trace_id = Column(String(128), nullable=False)

    # Outcome written after validation
    intake_outcome = Column(String(64), nullable=False, index=True)
    rejection_class = Column(Text(), nullable=True)
    rejection_detail = Column(Text(), nullable=True)

    # Canonical reference assigned on acceptance
    shared_record_ref = Column(Text(), nullable=True)

    # Full artifact snapshot
    payload_json = Column(JSONB(), nullable=False)
    envelope_json = Column(JSONB(), nullable=False)

    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=False)


class PSCloudReceipt(Base):
    """One row per receipt artifact emitted back to DataForge Local.

    Each intake_record produces exactly one receipt row.
    receipt_artifact_id is the UUID the receipt artifact carries as its
    own artifact_id (used by Local to validate the returned artifact).
    """

    __tablename__ = "ps_cloud_receipts"

    receipt_id = Column(String(36), primary_key=True)
    intake_id = Column(
        String(36),
        ForeignKey("ps_cloud_intake_records.intake_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_id = Column(String(36), nullable=False, index=True)
    receipt_artifact_id = Column(String(36), nullable=False, unique=True)

    intake_outcome = Column(String(64), nullable=False, index=True)
    rejection_class = Column(Text(), nullable=True)
    retry_allowed = Column(Boolean(), nullable=False, default=False)
    outcome_summary = Column(Text(), nullable=True)
    shared_record_ref = Column(Text(), nullable=True)

    emitted_at = Column(DateTime(timezone=True), nullable=False)

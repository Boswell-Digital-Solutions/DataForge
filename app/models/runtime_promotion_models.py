from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class RuntimePromotionReceipt(Base):
    __tablename__ = "runtime_promotion_receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(String(64), nullable=False, unique=True, index=True)

    envelope_type = Column(String(100), nullable=False, index=True)
    envelope_version = Column(String(20), nullable=False)

    fleet_member_id = Column(String(255), nullable=False, index=True)
    runtime_bundle_id = Column(String(255), nullable=True)
    runtime_bundle_version = Column(String(100), nullable=True)

    service = Column(String(100), nullable=False, index=True)
    dedupe_key = Column(String(255), nullable=True, index=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)

    payload = Column(JSONB, nullable=False)
    raw_envelope = Column(JSONB, nullable=False)

    ingest_status = Column(String(20), nullable=False, default="accepted", index=True)
    source = Column(String(50), nullable=False, default="forge_local_runtime")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
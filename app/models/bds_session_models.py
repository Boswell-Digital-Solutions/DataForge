"""Finalized BDS sessions owned by DataForge."""

from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class BdsSession(Base):
    __tablename__ = "bds_sessions"

    session_kind = Column(String(16), primary_key=True)
    session_id = Column(String(100), primary_key=True)
    final_status = Column(String(16), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    session_data = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    persisted_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

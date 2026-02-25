"""Global Rate Limits — SQLAlchemy models.

Provides cross-run rate limit tracking backed by DataForge.
ForgeAgents checks these limits before XAI/MAID calls.
Uses SELECT FOR UPDATE for atomic increment under concurrency.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, Integer, String, DateTime, Numeric, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class GlobalRateLimit(Base):
    """A rate-limit tracking row for a provider within a time window."""

    __tablename__ = "global_rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider = Column(
        String(30), nullable=False,
        comment="xai or maid",
    )
    window_start = Column(
        DateTime(timezone=True), nullable=False,
        comment="Start of the current rate-limit window",
    )
    window_duration_seconds = Column(
        Integer, nullable=False,
        comment="Duration of the window in seconds",
    )
    current_count = Column(
        Integer, nullable=False, default=0,
        comment="Number of requests in the current window",
    )
    max_count = Column(
        Integer, nullable=False,
        comment="Maximum requests allowed in the window",
    )
    cost_usd = Column(
        Numeric(10, 4), nullable=False, default=0,
        comment="Accumulated cost in USD for the window",
    )
    max_cost_usd = Column(
        Numeric(10, 4), nullable=True,
        comment="Maximum cost allowed for the window",
    )
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default=dict,
        comment="Additional tracking metadata",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('xai', 'maid')",
            name="ck_rate_limits_provider",
        ),
        UniqueConstraint("provider", "window_start", name="uq_rate_limits_provider_window"),
    )

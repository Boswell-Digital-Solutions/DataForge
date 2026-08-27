"""RateCardSnapshot.v1 persistence (Cost Provenance Tranche 3, RFC-CP-03).

DataForge is the durable owner of promoted rate-card snapshots — the data
NeuroForge's ``promote_rate_card_candidate.py`` CLI produces and every
consumer (NeuroForge, Forge-Agents, Forge_Command) prices RunCostEvent.v1
amounts against. The schema mirrors
``forge_contract_core/contracts/families/rate_card_snapshot/rate_card_snapshot.v1.schema.json``
field-for-field; server-side digest and overlap enforcement live in
``app/api/rate_card_router.py``, not here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

RATE_CARD_STATUSES = ("CANDIDATE", "ACTIVE", "EXPIRED", "SUPERSEDED", "REVOKED")


class RateCardSnapshot(Base):
    """One immutable, effective-dated provider/model rate card."""

    __tablename__ = "rate_card_snapshots"
    __table_args__ = (
        CheckConstraint(f"status IN {RATE_CARD_STATUSES}", name="ck_rate_card_status"),
        CheckConstraint(
            "uncached_input_rate_micros_per_million_tokens IS NULL OR uncached_input_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_uncached_input_nonneg",
        ),
        CheckConstraint(
            "cached_input_rate_micros_per_million_tokens IS NULL OR cached_input_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_cached_input_nonneg",
        ),
        CheckConstraint(
            "cache_write_rate_micros_per_million_tokens IS NULL OR cache_write_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_cache_write_nonneg",
        ),
        CheckConstraint(
            "reasoning_rate_micros_per_million_tokens IS NULL OR reasoning_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_reasoning_nonneg",
        ),
        CheckConstraint(
            "output_rate_micros_per_million_tokens IS NULL OR output_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_output_nonneg",
        ),
        Index(
            "ix_rate_card_lookup",
            "provider",
            "model",
            "model_version",
            "status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(64), nullable=False)
    model = Column(String(256), nullable=False)
    model_version = Column(String(64), nullable=True)
    currency = Column(String(3), nullable=False, server_default="USD")

    uncached_input_rate_micros_per_million_tokens = Column(Integer, nullable=True)
    cached_input_rate_micros_per_million_tokens = Column(Integer, nullable=True)
    cache_write_rate_micros_per_million_tokens = Column(Integer, nullable=True)
    reasoning_rate_micros_per_million_tokens = Column(Integer, nullable=True)
    output_rate_micros_per_million_tokens = Column(Integer, nullable=True)

    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)

    source_url = Column(String(2048), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    approved_by = Column(String(256), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)
    superseded_by = Column(UUID(as_uuid=True), nullable=True)
    rounding_rule = Column(String(64), nullable=False)
    digest = Column(String(80), nullable=False)

    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RateCardSnapshot {self.id} {self.provider}/{self.model} status={self.status}>"

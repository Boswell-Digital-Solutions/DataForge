"""CSSA security ledger — DataForge models (authority plan §22, §30).

Append-only immutable records written by the ForgeAgents CSSA recorder.
Cardinality is database law:
  - cssa_decisions / cssa_authorizations: unique attempt_id
  - cssa_outcomes: at most one TERMINAL outcome per attempt (partial unique)
There is no update path by design; the router exposes no mutation endpoints.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class CssaDecision(Base):
    __tablename__ = "cssa_decisions"

    decision_id = Column(String(128), primary_key=True)
    attempt_id = Column(String(128), nullable=False)
    correlation_id = Column(String(128), nullable=False)
    record_hash = Column(String(80), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cssa_decisions_attempt_unique", "attempt_id", unique=True),
    )


class CssaAuthorization(Base):
    __tablename__ = "cssa_authorizations"

    authorization_id = Column(String(128), primary_key=True)
    attempt_id = Column(String(128), nullable=False)
    correlation_id = Column(String(128), nullable=False)
    record_hash = Column(String(80), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cssa_authorizations_attempt_unique", "attempt_id", unique=True),
    )


class CssaOutcome(Base):
    __tablename__ = "cssa_outcomes"

    outcome_id = Column(String(128), primary_key=True)
    attempt_id = Column(String(128), nullable=False)
    correlation_id = Column(String(128), nullable=False)
    record_hash = Column(String(80), nullable=False)
    payload = Column(JSONB, nullable=False)
    terminal = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index(
            "ix_cssa_outcomes_attempt_terminal_unique",
            "attempt_id",
            unique=True,
            postgresql_where=text("terminal"),
            sqlite_where=text("terminal"),
        ),
    )


class CssaCounter(Base):
    """Monotonic anti-rollback high-water marks (bundle/snapshot versions)."""

    __tablename__ = "cssa_counters"

    counter = Column(String(128), primary_key=True)
    high_water = Column(BigInteger, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CssaQuotaReservation(Base):
    """Atomic quota reservation (authority plan §13; OPEN-3).

    Lifecycle: reserved -> committed | released | expired. The reserve path
    sums unexpired reserved + committed units per bucket inside one
    transaction so concurrent reserves cannot overspend.
    """

    __tablename__ = "cssa_quota_reservations"

    quota_reservation_id = Column(String(128), primary_key=True)
    tenant_id = Column(String(128), nullable=True)
    principal_id = Column(String(128), nullable=False)
    service = Column(String(128), nullable=False)
    quota_bucket = Column(String(256), nullable=False)
    reserved_units = Column(BigInteger, nullable=False)
    committed_units = Column(BigInteger, nullable=True)
    unit_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_cssa_quota_reservations_bucket_status", "quota_bucket", "status"),
    )


class CssaAuthorizationConsumption(Base):
    """Durable single-use consumption ledger (plan §15.4, §31 Phase 6).

    One row per consumed authorization; the primary key makes a replay a
    constraint violation across process restarts, not just within one process.
    """

    __tablename__ = "cssa_authorization_consumptions"

    authorization_id = Column(String(128), primary_key=True)
    consumed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

"""SQLAlchemy models for deterministic LLM policy envelope enforcement."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class LLMPolicyEnvelopeModel(Base):
    """Stored policy envelopes used by governed LLM execution."""

    __tablename__ = "llm_policy_envelopes"

    policy_key = Column(String(128), primary_key=True)
    policy_version = Column(String(32), nullable=False, index=True)
    envelope = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LLMPolicyLedgerEntryModel(Base):
    """Append-only per-call ledger entries for governed runs."""

    __tablename__ = "llm_policy_run_ledger"

    ledger_id = Column(String(36), primary_key=True)
    run_id = Column(String(64), nullable=False, index=True)
    sequence_no = Column(Integer, nullable=False)
    policy_key = Column(String(128), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False, index=True)
    provider = Column(String(64), nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_estimated_usd = Column(Numeric(10, 6), nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    termination_reason = Column(String(64), nullable=True, index=True)
    entry_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "sequence_no", name="uq_llm_policy_run_ledger_sequence"),
        Index("ix_llm_policy_run_ledger_run_sequence", "run_id", "sequence_no"),
    )


class LLMPolicyRunFinalizationModel(Base):
    """Single-write finalization records for governed runs."""

    __tablename__ = "llm_policy_run_finalizations"

    run_id = Column(String(64), primary_key=True)
    policy_key = Column(String(128), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, index=True)
    termination_reason = Column(String(64), nullable=True, index=True)
    total_calls = Column(Integer, nullable=False, default=0)
    total_prompt_tokens = Column(Integer, nullable=False, default=0)
    total_completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Numeric(10, 6), nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finalized_at = Column(DateTime(timezone=True), nullable=False)
    finalization_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LLMPolicyBanditStateModel(Base):
    """Tenant-scoped Slice 2 bandit state for governed LLM routing."""

    __tablename__ = "llm_policy_bandit_states"

    tenant_id = Column(String(128), primary_key=True)
    policy_key = Column(String(128), primary_key=True)
    partition_key = Column(String(256), primary_key=True)
    policy_version = Column(String(32), nullable=False)
    bandit_policy_id = Column(String(32), nullable=False, index=True)
    state_version = Column(Integer, nullable=False, default=0)
    state_payload = Column(JSONB, nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "ix_llm_policy_bandit_states_tenant_policy",
            "tenant_id",
            "policy_key",
        ),
    )


class LLMPolicyRewardRecordModel(Base):
    """Immutable reward records for Slice 2 bandit updates."""

    __tablename__ = "llm_policy_reward_records"

    call_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    policy_key = Column(String(128), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False)
    partition_key = Column(String(256), nullable=False, index=True)
    action_id = Column(String(256), nullable=False, index=True)
    bandit_policy_id = Column(String(32), nullable=False, index=True)
    reward_version = Column(String(32), nullable=False)
    reward_value = Column(Numeric(8, 6), nullable=False)
    router_degraded = Column(Boolean, nullable=False, default=False)
    reward_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_llm_policy_reward_records_tenant_policy_created",
            "tenant_id",
            "policy_key",
            "created_at",
        ),
    )

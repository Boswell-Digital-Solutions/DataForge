"""Forge Memory (FMEM-02) typed memory spine.

Durable, scoped, bitemporal storage for the memory contract families produced by
the ``forge-memory`` engine (plan set BDS-FMEM-PLAN-SET-001). DataForge Cloud is
the store of record.

Design: each row keeps the full artifact envelope+payload as JSONB, plus typed,
indexed columns for scope isolation and temporal retrieval. Distinct from the
legacy scopeless ``agent_memories`` bucket — these tables add authenticated
scope, temporal validity, supersession, and a real delete path.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MemoryEpisode(Base):
    """Immutable agent/system event (memory_episode). References producer
    evidence; grants no authority."""

    __tablename__ = "memory_episodes"

    artifact_id = Column(String(64), primary_key=True)
    episode_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True, index=True)
    repo_id = Column(String(128), nullable=True, index=True)
    run_id = Column(String(128), nullable=True, index=True)
    agent_id = Column(String(128), nullable=True, index=True)
    episode_type = Column(String(32), nullable=False)
    origin_class = Column(String(32), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    residency = Column(String(32), nullable=False)
    sensitivity_class = Column(String(32), nullable=False)
    instruction_capability = Column(String(16), nullable=False)
    quarantined = Column(Boolean, nullable=False, default=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemoryClaim(Base):
    """Candidate assertion derived from episodes (memory_claim)."""

    __tablename__ = "memory_claims"

    artifact_id = Column(String(64), primary_key=True)
    claim_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True, index=True)
    repo_id = Column(String(128), nullable=True, index=True)
    subject_entity_id = Column(String(256), nullable=False, index=True)
    predicate = Column(String(256), nullable=False, index=True)
    object = Column(Text, nullable=False)
    authority_class = Column(String(32), nullable=False)
    trust_state = Column(String(32), nullable=False)
    verification_state = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemoryFact(Base):
    """Promoted, bitemporal, canonical fact (memory_fact). ``artifact_id`` equals
    the payload ``memory_id``."""

    __tablename__ = "memory_facts"

    artifact_id = Column(String(64), primary_key=True)
    memory_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True, index=True)
    repo_id = Column(String(128), nullable=True, index=True)
    subject_entity_id = Column(String(256), nullable=False, index=True)
    predicate = Column(String(256), nullable=False, index=True)
    object = Column(Text, nullable=False)
    authority_class = Column(String(32), nullable=False)
    trust_state = Column(String(32), nullable=False)
    verification_state = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, index=True)
    valid_from = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_to = Column(DateTime(timezone=True), nullable=True, index=True)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    supersedes_memory_id = Column(String(64), nullable=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_memory_facts_current", "tenant_id", "subject_entity_id", "predicate", "status"),
        Index("ix_memory_facts_temporal", "valid_from", "valid_to"),
    )


class MemoryReceipt(Base):
    """Retrieval or use receipt (memory_retrieval_receipt / memory_use_receipt)."""

    __tablename__ = "memory_receipts"

    artifact_id = Column(String(64), primary_key=True)
    receipt_kind = Column(String(32), nullable=False, index=True)  # retrieval | use
    tenant_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True)
    repo_id = Column(String(128), nullable=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemoryDeletion(Base):
    """Non-sensitive deletion receipt. Records that a memory row was really
    removed (removing eligibility), unlike the legacy phantom clear()."""

    __tablename__ = "memory_deletions"

    id = Column(String(64), primary_key=True, default=_uuid)
    target_family = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    reason = Column(String(256), nullable=True)
    requested_by = Column(String(128), nullable=False)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())

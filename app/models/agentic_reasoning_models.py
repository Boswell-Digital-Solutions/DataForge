"""SQLAlchemy models for Agentic Reasoning extensions.

This module provides database models for the Experience Store,
Skill Nominations, and Governed Broadcasts. These support the
agentic reasoning capabilities from Wei et al. (2026).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.database import Base


# ============================================================================
# Execution Experience (Experience Store)
# ============================================================================


class ExecutionExperienceModel(Base):
    """Database model for execution experience records.

    Stores past execution outcomes with vector embeddings for semantic
    retrieval during the Plan phase. Written during the Reflect phase.
    """

    __tablename__ = "execution_experiences"

    experience_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("forge_runs.run_id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), nullable=False)
    agent_archetype = Column(String(50), nullable=False)
    task_embedding = Column(Vector(768), nullable=False)
    target_scope = Column(JSON, nullable=False)
    execution_summary = Column(Text, nullable=False)
    outcome = Column(String(20), nullable=False)  # success, partial, failure
    gate_results_snapshot = Column(JSON, nullable=True)
    tool_sequence = Column(JSON, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ============================================================================
# Skill Nomination
# ============================================================================


class SkillNominationModel(Base):
    """Database model for skill promotion nominations.

    Tracks the lifecycle of skill candidates from detection through
    registration in the capability registry.
    """

    __tablename__ = "skill_nominations"

    nomination_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_name = Column(String(200), nullable=False)
    tool_sequence = Column(JSON, nullable=False)
    parameter_schemas = Column(JSON, nullable=True)
    evidence_run_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    proposed_capability_category = Column(String(1), nullable=True)  # A-G
    proposed_capability_id = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="candidate")
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ============================================================================
# Governed Broadcast
# ============================================================================


class GovernedBroadcastModel(Base):
    """Database model for governed broadcast messages.

    Records all agent-to-agent knowledge sharing packets routed
    through ForgeCommand for governance and audit.
    """

    __tablename__ = "governed_broadcasts"

    broadcast_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_agent_id = Column(UUID(as_uuid=True), nullable=False)
    source_run_id = Column(UUID(as_uuid=True), ForeignKey("forge_runs.run_id", ondelete="CASCADE"), nullable=False)
    target_scope = Column(JSON, nullable=False)
    knowledge_type = Column(String(30), nullable=False)  # context_discovery, error_signal, dependency_finding, scope_overlap
    payload = Column(JSON, nullable=False)
    provenance = Column(JSON, nullable=True)
    trust_metadata = Column(JSON, nullable=True)
    delivered_to = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

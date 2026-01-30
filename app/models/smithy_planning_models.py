"""
Smithy Planning Session Models

SQLAlchemy models for persisting Planning sprint sessions from forge-smithy.
These models store the full PAORT cycle output and deliverables.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum
import uuid

from app.database import Base


def generate_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


class SessionStatus(str, enum.Enum):
    """Planning session lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PAORTStage(str, enum.Enum):
    """PAORT cycle stages."""
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    TRANSITION = "transition"


class SmithyPlanningSession(Base):
    """Planning session record.

    Stores the full lifecycle of a planning sprint including request,
    stage outputs, and final deliverable.
    """
    __tablename__ = "smithy_planning_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Session metadata
    user_id = Column(String(36), nullable=True, index=True)
    forgeagents_session_id = Column(String(100), nullable=True, index=True)

    # Status tracking
    status = Column(
        SQLEnum(SessionStatus, name="planning_session_status"),
        nullable=False,
        default=SessionStatus.PENDING
    )
    current_stage = Column(
        SQLEnum(PAORTStage, name="paort_stage"),
        nullable=True
    )

    # Request data
    request_title = Column(String(200), nullable=False)
    request_description = Column(Text, nullable=False)
    request_repo_url = Column(String(500), nullable=True)
    request_repo_commit = Column(String(40), nullable=True)
    normalized_prompt = Column(Text, nullable=True)

    # Stage outputs (JSONB for flexibility)
    stage_plan_output = Column(JSONB, nullable=True)
    stage_act_output = Column(JSONB, nullable=True)
    stage_observe_output = Column(JSONB, nullable=True)
    stage_reflect_output = Column(JSONB, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_stage = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    deliverable = relationship(
        "SmithyPlanningDeliverable",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SmithyPlanningSession(id={self.id}, status={self.status}, title={self.request_title[:30]}...)>"


class SmithyPlanningDeliverable(Base):
    """Final deliverable from a completed planning session.

    Contains the structured plan, execution prompt, and metadata.
    """
    __tablename__ = "smithy_planning_deliverables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36),
        ForeignKey("smithy_planning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Plan structure
    plan_title = Column(String(300), nullable=False)
    plan_overview = Column(Text, nullable=False)
    plan_estimated_effort = Column(String(100), nullable=True)
    plan_risks = Column(ARRAY(String), nullable=True)

    # Execution prompt for coding agent
    execution_prompt = Column(Text, nullable=False)

    # Metadata
    total_tokens = Column(Integer, nullable=True)
    total_cost = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    tone_violations = Column(Integer, nullable=True, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("SmithyPlanningSession", back_populates="deliverable")
    steps = relationship(
        "SmithyPlanningStep",
        back_populates="deliverable",
        cascade="all, delete-orphan",
        order_by="SmithyPlanningStep.step_order"
    )

    def __repr__(self):
        return f"<SmithyPlanningDeliverable(id={self.id}, title={self.plan_title[:30]}...)>"


class SmithyPlanningStep(Base):
    """Individual step in a planning deliverable.

    Represents one implementation step with dependencies and acceptance criteria.
    """
    __tablename__ = "smithy_planning_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    deliverable_id = Column(
        String(36),
        ForeignKey("smithy_planning_deliverables.id", ondelete="CASCADE"),
        nullable=False
    )

    # Step order (1-based)
    step_order = Column(Integer, nullable=False)

    # Step content
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    estimated_effort = Column(String(100), nullable=True)

    # Dependencies (array of step IDs)
    dependencies = Column(ARRAY(String), nullable=True, default=[])

    # Acceptance criteria (array of strings)
    acceptance_criteria = Column(ARRAY(String), nullable=True, default=[])

    # Relationships
    deliverable = relationship("SmithyPlanningDeliverable", back_populates="steps")

    def __repr__(self):
        return f"<SmithyPlanningStep(id={self.id}, order={self.step_order}, title={self.title[:30]}...)>"

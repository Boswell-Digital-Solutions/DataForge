"""
Multi-AI Planning System Models

SQLAlchemy ORM models for tracking planning sessions, model performance,
and AI time estimation feedback.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, BigInteger, Index
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class PlanningOutcome(Base):
    """
    Records complete planning session execution with stage-by-stage results.

    Tracks multi-AI workflows (ChatGPT ←→ Claude iterations) including:
    - Model selection per stage
    - Token usage and latency
    - Execution outcomes
    - User feedback and satisfaction
    """
    __tablename__ = "planning_outcomes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Session context
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(100), nullable=True)

    # Request metadata
    workflow_type = Column(String(50), nullable=False)  # 'multi_ai_planning'
    task_type = Column(String(50), nullable=True)  # 'feature', 'refactor', 'bugfix'
    request_complexity = Column(String(20), nullable=True)  # 'simple', 'medium', 'complex'
    codebase_context = Column(JSON, nullable=True)

    # Stage-by-stage results (JSON array)
    # Format: [{"stage": 1, "type": "initial", "model": "gpt-4", ...}, ...]
    stages = Column(JSON, nullable=False)

    # Aggregates
    total_duration_ms = Column(Integer, nullable=True)
    total_tokens_used = Column(Integer, nullable=True)
    total_cost_cents = Column(Integer, nullable=True)
    iteration_count = Column(Integer, default=1)

    # Execution outcome (filled after Claude Code runs the plan)
    execution_started = Column(Boolean, default=False)
    execution_success = Column(Boolean, nullable=True)
    execution_duration_seconds = Column(Integer, nullable=True)
    tasks_completed = Column(Integer, nullable=True)
    tasks_failed = Column(Integer, nullable=True)

    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)
    plan_was_modified = Column(Boolean, default=False)
    modification_extent = Column(Float, nullable=True)  # 0.0 to 1.0

    __table_args__ = (
        Index('idx_planning_outcomes_created', 'created_at'),
        Index('idx_planning_outcomes_task', 'task_type', 'workflow_type'),
    )

    def __repr__(self):
        return f"<PlanningOutcome(id={self.id}, workflow={self.workflow_type}, stages={len(self.stages) if self.stages else 0})>"


class PlanningModelPerformance(Base):
    """
    Tracks model performance using EMA for continuous learning.

    Maintains aggregates per (model, provider, stage_type, task_type) dimension.
    Uses Exponential Moving Average for quality metrics that adapt over time.
    """
    __tablename__ = "planning_model_performance"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Dimensions (composite key)
    model = Column(String(100), nullable=False, index=True)  # 'gpt-4', 'claude-3-opus'
    provider = Column(String(50), nullable=False, index=True)  # 'openai', 'anthropic'
    stage_type = Column(String(50), nullable=False, index=True)  # 'initial', 'review', 'refinement', 'final'
    task_type = Column(String(50), default='general', index=True)  # 'feature', 'refactor', 'bugfix'

    # Raw aggregates
    sample_count = Column(Integer, default=0)
    total_duration_ms = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    success_count = Column(Integer, default=0)

    # Calculated averages
    avg_duration_ms = Column(Float, nullable=True)
    avg_tokens = Column(Float, nullable=True)
    avg_quality_score = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)

    # EMA values (exponential moving average)
    ema_duration_ms = Column(Float, nullable=True)
    ema_quality = Column(Float, nullable=True)
    ema_alpha = Column(Float, default=0.1)  # Learning rate

    # Cost tracking
    avg_cost_cents = Column(Float, nullable=True)

    __table_args__ = (
        Index('idx_planning_model_perf_lookup', 'model', 'provider', 'stage_type'),
        Index('idx_planning_model_perf_task', 'task_type', 'stage_type'),
    )

    def __repr__(self):
        return f"<PlanningModelPerformance(model={self.model}, stage={self.stage_type}, samples={self.sample_count})>"


class AIEstimationFeedback(Base):
    """
    Records AI time estimation accuracy for continuous improvement.

    Tracks estimated vs actual execution time to improve future estimates.
    Supports different executors (claude_code, human) and task categories.
    """
    __tablename__ = "ai_estimation_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Task context
    task_category = Column(String(50), nullable=False, index=True)  # 'testing', 'refactoring', 'feature'
    task_complexity = Column(String(20), nullable=True)  # 'simple', 'medium', 'complex'

    # Estimation vs actual
    estimated_minutes = Column(Float, nullable=False)
    actual_minutes = Column(Float, nullable=False)
    accuracy_ratio = Column(Float, nullable=True)  # actual / estimated

    # Execution context
    executor_type = Column(String(30), nullable=False, index=True)  # 'claude_code', 'human', 'copilot'
    model_used = Column(String(100), nullable=True)  # Which AI model was used
    codebase_lines = Column(Integer, nullable=True)  # Size of codebase

    # Factors (JSON for flexible metadata)
    factors = Column(JSON, nullable=True)

    # User context
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index('idx_estimation_task', 'task_category', 'executor_type'),
        Index('idx_estimation_created', 'created_at'),
    )

    def __repr__(self):
        return f"<AIEstimationFeedback(category={self.task_category}, est={self.estimated_minutes}m, actual={self.actual_minutes}m)>"

"""
Tests for Multi-AI Planning SQLAlchemy Models

Tests:
- PlanningOutcome model creation and relationships
- PlanningModelPerformance model with EMA tracking
- AIEstimationFeedback model for time estimation
- Database constraints and validations
"""

import pytest
import uuid
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.planning_models import Base, PlanningOutcome, PlanningModelPerformance, AIEstimationFeedback


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ============================================================================
# PlanningOutcome Model Tests
# ============================================================================

class TestPlanningOutcome:
    """Test PlanningOutcome model."""

    def test_create_planning_outcome(self, db_session):
        """Test creating a basic planning outcome record."""
        session_id = str(uuid.uuid4())
        outcome = PlanningOutcome(
            id=str(uuid.uuid4()),
            session_id=session_id,
            workflow_type="multi_ai_planning",
            task_type="feature",
            request_complexity="medium",
            stages=[
                {
                    "stage": 1,
                    "type": "initial",
                    "model": "gpt-4",
                    "provider": "openai",
                    "duration_ms": 5000,
                    "tokens_in": 1500,
                    "tokens_out": 2000
                }
            ],
            total_duration_ms=20000,
            total_tokens_used=10000,
            total_cost_cents=50,
            iteration_count=1
        )

        db_session.add(outcome)
        db_session.commit()

        # Verify record was created
        retrieved = db_session.query(PlanningOutcome).filter_by(session_id=session_id).first()
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.workflow_type == "multi_ai_planning"
        assert retrieved.task_type == "feature"
        assert retrieved.request_complexity == "medium"
        assert len(retrieved.stages) == 1
        assert retrieved.total_duration_ms == 20000

    def test_planning_outcome_with_execution_data(self, db_session):
        """Test planning outcome with execution results."""
        outcome = PlanningOutcome(
            id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            task_type="refactor",
            request_complexity="complex",
            stages=[],
            total_duration_ms=30000,
            total_tokens_used=15000,
            total_cost_cents=75,
            iteration_count=1,
            # Execution data
            execution_started=True,
            execution_success=True,
            execution_duration_seconds=180,
            tasks_completed=5,
            tasks_failed=0
        )

        db_session.add(outcome)
        db_session.commit()

        retrieved = db_session.query(PlanningOutcome).filter_by(id=outcome.id).first()
        assert retrieved.execution_started is True
        assert retrieved.execution_success is True
        assert retrieved.execution_duration_seconds == 180
        assert retrieved.tasks_completed == 5
        assert retrieved.tasks_failed == 0

    def test_planning_outcome_with_user_feedback(self, db_session):
        """Test planning outcome with user feedback."""
        outcome = PlanningOutcome(
            id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            task_type="bugfix",
            stages=[],
            total_duration_ms=15000,
            total_tokens_used=8000,
            total_cost_cents=40,
            iteration_count=1,
            # User feedback
            user_rating=5,
            user_feedback="Excellent plan, very detailed!",
            plan_was_modified=False,
            modification_extent=0.0
        )

        db_session.add(outcome)
        db_session.commit()

        retrieved = db_session.query(PlanningOutcome).filter_by(id=outcome.id).first()
        assert retrieved.user_rating == 5
        assert "Excellent" in retrieved.user_feedback
        assert retrieved.plan_was_modified is False
        assert retrieved.modification_extent == 0.0

    def test_planning_outcome_json_stages(self, db_session):
        """Test that stages are properly stored as JSON."""
        stages = [
            {"stage": 1, "type": "initial", "model": "gpt-4", "tokens": 1000},
            {"stage": 2, "type": "review", "model": "claude-3-opus", "tokens": 1200},
            {"stage": 3, "type": "refinement", "model": "gpt-4", "tokens": 1100},
            {"stage": 4, "type": "final", "model": "claude-3-opus", "tokens": 1300}
        ]

        outcome = PlanningOutcome(
            id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            stages=stages,
            total_duration_ms=25000,
            total_tokens_used=4600,
            total_cost_cents=80
        )

        db_session.add(outcome)
        db_session.commit()

        retrieved = db_session.query(PlanningOutcome).filter_by(id=outcome.id).first()
        assert len(retrieved.stages) == 4
        assert retrieved.stages[0]["type"] == "initial"
        assert retrieved.stages[3]["model"] == "claude-3-opus"

    def test_planning_outcome_session_id_index(self, db_session):
        """Test that session_id index works for queries."""
        session_id = str(uuid.uuid4())

        # Create multiple outcomes with same session_id
        for i in range(3):
            outcome = PlanningOutcome(
                id=str(uuid.uuid4()),
                session_id=session_id,
                workflow_type="multi_ai_planning",
                stages=[],
                total_duration_ms=10000 * (i + 1),
                total_tokens_used=5000,
                total_cost_cents=25
            )
            db_session.add(outcome)

        db_session.commit()

        # Query by session_id (should use index)
        outcomes = db_session.query(PlanningOutcome).filter_by(session_id=session_id).all()
        assert len(outcomes) == 3


# ============================================================================
# PlanningModelPerformance Model Tests
# ============================================================================

class TestPlanningModelPerformance:
    """Test PlanningModelPerformance model."""

    def test_create_model_performance(self, db_session):
        """Test creating a model performance record."""
        perf = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="initial",
            task_type="feature",
            ema_duration_ms=5000.0,
            avg_tokens=3500.0,
            avg_cost_cents=45.0,
            ema_quality=0.85,
            success_rate=0.92,
            sample_count=10
        )

        db_session.add(perf)
        db_session.commit()

        retrieved = db_session.query(PlanningModelPerformance).filter_by(model="gpt-4", stage_type="initial").first()
        assert retrieved is not None
        assert retrieved.provider == "openai"
        assert retrieved.ema_quality == 0.85
        assert retrieved.success_rate == 0.92
        assert retrieved.sample_count == 10

    def test_model_performance_ema_fields(self, db_session):
        """Test EMA (Exponential Moving Average) fields."""
        perf = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="claude-3-opus-20240229",
            provider="anthropic",
            stage_type="review",
            ema_duration_ms=3500.5,
            avg_tokens=2800.75,
            avg_cost_cents=55.25,
            ema_quality=0.91,
            success_rate=0.95,
            sample_count=25
        )

        db_session.add(perf)
        db_session.commit()

        retrieved = db_session.query(PlanningModelPerformance).filter_by(id=perf.id).first()
        assert abs(retrieved.ema_duration_ms - 3500.5) < 0.01
        assert abs(retrieved.avg_tokens - 2800.75) < 0.01
        assert abs(retrieved.avg_cost_cents - 55.25) < 0.01
        assert abs(retrieved.ema_quality - 0.91) < 0.01

    def test_model_performance_multiple_records(self, db_session):
        """Test creating multiple performance records for different combinations."""
        # Create records for different model/stage combinations
        perf1 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="initial",
            task_type="feature",
            ema_quality=0.85,
            sample_count=5
        )

        perf2 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="refinement",  # Different stage
            task_type="feature",
            ema_quality=0.90,
            sample_count=10
        )

        db_session.add_all([perf1, perf2])
        db_session.commit()

        # Both should exist
        results = db_session.query(PlanningModelPerformance).filter_by(
            model="gpt-4",
            provider="openai"
        ).all()
        assert len(results) == 2


# ============================================================================
# AIEstimationFeedback Model Tests
# ============================================================================

class TestAIEstimationFeedback:
    """Test AIEstimationFeedback model."""

    def test_create_estimation_feedback(self, db_session):
        """Test creating an estimation feedback record."""
        feedback = AIEstimationFeedback(
            id=str(uuid.uuid4()),
            task_category="feature",
            task_complexity="medium",
            executor_type="claude_code",
            estimated_minutes=60,
            actual_minutes=55,
            accuracy_ratio=0.92
        )

        db_session.add(feedback)
        db_session.commit()

        retrieved = db_session.query(AIEstimationFeedback).filter_by(id=feedback.id).first()
        assert retrieved is not None
        assert retrieved.task_category == "feature"
        assert retrieved.estimated_minutes == 60
        assert retrieved.actual_minutes == 55
        assert abs(retrieved.accuracy_ratio - 0.92) < 0.01

    def test_estimation_feedback_accuracy_calculation(self, db_session):
        """Test accuracy ratio calculation."""
        # Perfect estimate
        feedback1 = AIEstimationFeedback(
            id=str(uuid.uuid4()),
            task_category="bugfix",
            task_complexity="simple",
            executor_type="claude_code",
            estimated_minutes=30,
            actual_minutes=30,
            accuracy_ratio=1.0
        )

        # Underestimate
        feedback2 = AIEstimationFeedback(
            id=str(uuid.uuid4()),
            task_category="refactor",
            task_complexity="complex",
            executor_type="claude_code",
            estimated_minutes=120,
            actual_minutes=180,
            accuracy_ratio=0.67  # 120/180
        )

        # Overestimate
        feedback3 = AIEstimationFeedback(
            id=str(uuid.uuid4()),
            task_category="feature",
            task_complexity="medium",
            executor_type="claude_code",
            estimated_minutes=90,
            actual_minutes=60,
            accuracy_ratio=0.67  # 60/90
        )

        db_session.add_all([feedback1, feedback2, feedback3])
        db_session.commit()

        all_feedback = db_session.query(AIEstimationFeedback).all()
        assert len(all_feedback) == 3
        assert any(f.accuracy_ratio == 1.0 for f in all_feedback)

    def test_estimation_feedback_index(self, db_session):
        """Test that executor_type and task_category are indexed."""
        # Create multiple feedback records
        for i in range(5):
            feedback = AIEstimationFeedback(
                id=str(uuid.uuid4()),
                task_category="feature",
                executor_type="claude_code",
                estimated_minutes=60,
                actual_minutes=55 + i,
                accuracy_ratio=0.9
            )
            db_session.add(feedback)

        db_session.commit()

        # Query should use index
        results = db_session.query(AIEstimationFeedback).filter_by(
            executor_type="claude_code",
            task_category="feature"
        ).all()

        assert len(results) == 5


# ============================================================================
# Integration Tests
# ============================================================================

class TestModelIntegration:
    """Test interactions between models."""

    def test_full_workflow_data_storage(self, db_session):
        """Test storing complete workflow with all related data."""
        session_id = str(uuid.uuid4())

        # 1. Create planning outcome
        outcome = PlanningOutcome(
            id=str(uuid.uuid4()),
            session_id=session_id,
            workflow_type="multi_ai_planning",
            task_type="feature",
            request_complexity="medium",
            stages=[
                {"stage": 1, "model": "gpt-4", "tokens": 3000},
                {"stage": 2, "model": "claude-3-opus", "tokens": 3200}
            ],
            total_duration_ms=25000,
            total_tokens_used=6200,
            total_cost_cents=85,
            iteration_count=1
        )

        # 2. Create model performance records
        perf1 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="initial",
            task_type="feature",
            ema_quality=0.88,
            sample_count=15
        )

        perf2 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="claude-3-opus-20240229",
            provider="anthropic",
            stage_type="review",
            task_type="feature",
            ema_quality=0.92,
            sample_count=18
        )

        # 3. Create estimation feedback
        feedback = AIEstimationFeedback(
            id=str(uuid.uuid4()),
            task_category="feature",
            task_complexity="medium",
            executor_type="claude_code",
            estimated_minutes=60,
            actual_minutes=58,
            accuracy_ratio=0.97
        )

        db_session.add_all([outcome, perf1, perf2, feedback])
        db_session.commit()

        # Verify all records exist
        assert db_session.query(PlanningOutcome).count() == 1
        assert db_session.query(PlanningModelPerformance).count() == 2
        assert db_session.query(AIEstimationFeedback).count() == 1

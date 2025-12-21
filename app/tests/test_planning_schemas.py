"""
Tests for Multi-AI Planning Pydantic Schemas

Tests:
- Schema validation and field constraints
- Complexity and rating validators
- Nested schema structures (StageResult)
- Request/response serialization
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from app.models.planning_schemas import (
    StageResult,
    PlanningOutcomeCreate,
    ExecutionResultUpdate,
    UserFeedbackUpdate,
    PlanningOutcomeResponse,
    ModelRecommendation,
    StageModelRecommendations,
    TimeEstimateRecommendation,
    IterationRecommendation,
    AIEstimationFeedbackCreate,
    AIEstimationFeedbackResponse,
    ModelPerformanceResponse
)


# ============================================================================
# StageResult Schema Tests
# ============================================================================

class TestStageResult:
    """Test StageResult schema."""

    def test_valid_stage_result(self):
        """Test creating a valid stage result."""
        stage = StageResult(
            stage=1,
            type="initial",
            model="gpt-4",
            provider="openai",
            duration_ms=5000,
            tokens_in=1500,
            tokens_out=2000,
            metadata={"temperature": 0.7}
        )

        assert stage.stage == 1
        assert stage.type == "initial"
        assert stage.model == "gpt-4"
        assert stage.duration_ms == 5000
        assert stage.metadata["temperature"] == 0.7

    def test_stage_result_missing_optional_fields(self):
        """Test stage result with optional fields omitted."""
        stage = StageResult(
            stage=2,
            type="review",
            model="claude-3-opus-20240229",
            provider="anthropic",
            duration_ms=3500,
            tokens_in=1200,
            tokens_out=1800
        )

        assert stage.metadata is None or stage.metadata == {}

    def test_stage_result_negative_duration_fails(self):
        """Test that negative duration is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StageResult(
                stage=1,
                type="initial",
                model="gpt-4",
                provider="openai",
                duration_ms=-1000,  # Invalid
                tokens_in=1500,
                tokens_out=2000
            )

        errors = exc_info.value.errors()
        assert any("duration_ms" in str(e) for e in errors)


# ============================================================================
# PlanningOutcomeCreate Schema Tests
# ============================================================================

class TestPlanningOutcomeCreate:
    """Test PlanningOutcomeCreate schema."""

    def test_valid_planning_outcome_create(self):
        """Test creating a valid planning outcome."""
        outcome = PlanningOutcomeCreate(
            session_id="test-session-123",
            workflow_type="multi_ai_planning",
            task_type="feature",
            request_complexity="medium",
            stages=[
                StageResult(
                    stage=1,
                    type="initial",
                    model="gpt-4",
                    provider="openai",
                    duration_ms=5000,
                    tokens_in=1500,
                    tokens_out=2000
                )
            ],
            total_duration_ms=25000,
            total_tokens_used=10000,
            total_cost_cents=85,
            iteration_count=1
        )

        assert outcome.session_id == "test-session-123"
        assert outcome.workflow_type == "multi_ai_planning"
        assert outcome.task_type == "feature"
        assert outcome.request_complexity == "medium"
        assert len(outcome.stages) == 1

    def test_complexity_validator(self):
        """Test complexity field validation."""
        # Valid complexities
        for complexity in ["simple", "medium", "complex"]:
            outcome = PlanningOutcomeCreate(
                session_id="test",
                workflow_type="multi_ai_planning",
                request_complexity=complexity,
                stages=[],
                total_duration_ms=1000,
                total_tokens_used=500,
                total_cost_cents=10
            )
            assert outcome.request_complexity == complexity

        # Invalid complexity
        with pytest.raises(ValidationError) as exc_info:
            PlanningOutcomeCreate(
                session_id="test",
                workflow_type="multi_ai_planning",
                request_complexity="ultra-hard",  # Invalid
                stages=[],
                total_duration_ms=1000,
                total_tokens_used=500,
                total_cost_cents=10
            )

        errors = exc_info.value.errors()
        assert any("request_complexity" in str(e) for e in errors)

    def test_negative_values_rejected(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            PlanningOutcomeCreate(
                session_id="test",
                workflow_type="multi_ai_planning",
                stages=[],
                total_duration_ms=-1000,  # Invalid
                total_tokens_used=500,
                total_cost_cents=10
            )

        with pytest.raises(ValidationError):
            PlanningOutcomeCreate(
                session_id="test",
                workflow_type="multi_ai_planning",
                stages=[],
                total_duration_ms=1000,
                total_tokens_used=-500,  # Invalid
                total_cost_cents=10
            )

    def test_codebase_context_optional(self):
        """Test that codebase_context is optional."""
        outcome1 = PlanningOutcomeCreate(
            session_id="test",
            workflow_type="multi_ai_planning",
            stages=[],
            total_duration_ms=1000,
            total_tokens_used=500,
            total_cost_cents=10
        )
        assert outcome1.codebase_context is None

        outcome2 = PlanningOutcomeCreate(
            session_id="test",
            workflow_type="multi_ai_planning",
            codebase_context={"files": 50, "lines": 10000},
            stages=[],
            total_duration_ms=1000,
            total_tokens_used=500,
            total_cost_cents=10
        )
        assert outcome2.codebase_context["files"] == 50


# ============================================================================
# ExecutionResultUpdate Schema Tests
# ============================================================================

class TestExecutionResultUpdate:
    """Test ExecutionResultUpdate schema."""

    def test_valid_execution_result(self):
        """Test valid execution result update."""
        result = ExecutionResultUpdate(
            success=True,
            duration_seconds=180,
            tasks_completed=5,
            tasks_failed=0
        )

        assert result.success is True
        assert result.duration_seconds == 180
        assert result.tasks_completed == 5
        assert result.tasks_failed == 0

    def test_execution_result_defaults(self):
        """Test default values for optional fields."""
        result = ExecutionResultUpdate(
            success=False,
            duration_seconds=120
        )

        assert result.tasks_completed == 0
        assert result.tasks_failed == 0

    def test_negative_duration_rejected(self):
        """Test that negative duration is rejected."""
        with pytest.raises(ValidationError):
            ExecutionResultUpdate(
                success=True,
                duration_seconds=-60  # Invalid
            )


# ============================================================================
# UserFeedbackUpdate Schema Tests
# ============================================================================

class TestUserFeedbackUpdate:
    """Test UserFeedbackUpdate schema."""

    def test_valid_user_feedback(self):
        """Test valid user feedback."""
        feedback = UserFeedbackUpdate(
            rating=5,
            feedback="Excellent plan!",
            plan_was_modified=False,
            modification_extent=0.0
        )

        assert feedback.rating == 5
        assert feedback.feedback == "Excellent plan!"
        assert feedback.plan_was_modified is False
        assert feedback.modification_extent == 0.0

    def test_rating_validator(self):
        """Test rating validation (1-5)."""
        # Valid ratings
        for rating in range(1, 6):
            feedback = UserFeedbackUpdate(rating=rating)
            assert feedback.rating == rating

        # Invalid ratings
        with pytest.raises(ValidationError):
            UserFeedbackUpdate(rating=0)  # Too low

        with pytest.raises(ValidationError):
            UserFeedbackUpdate(rating=6)  # Too high

    def test_modification_extent_validator(self):
        """Test modification_extent validation (0.0-1.0)."""
        # Valid extents
        for extent in [0.0, 0.25, 0.5, 0.75, 1.0]:
            feedback = UserFeedbackUpdate(
                rating=4,
                plan_was_modified=True,
                modification_extent=extent
            )
            assert feedback.modification_extent == extent

        # Invalid extents
        with pytest.raises(ValidationError):
            UserFeedbackUpdate(
                rating=4,
                modification_extent=-0.1  # Too low
            )

        with pytest.raises(ValidationError):
            UserFeedbackUpdate(
                rating=4,
                modification_extent=1.5  # Too high
            )


# ============================================================================
# ModelRecommendation Schema Tests
# ============================================================================

class TestModelRecommendation:
    """Test ModelRecommendation schema."""

    def test_valid_model_recommendation(self):
        """Test valid model recommendation."""
        rec = ModelRecommendation(
            model="gpt-4",
            provider="openai",
            confidence=0.85
        )

        assert rec.model == "gpt-4"
        assert rec.provider == "openai"
        assert abs(rec.confidence - 0.85) < 0.01

    def test_confidence_bounds(self):
        """Test confidence validation (0.0-1.0)."""
        # Valid confidences
        for conf in [0.0, 0.5, 1.0]:
            rec = ModelRecommendation(
                model="gpt-4",
                provider="openai",
                confidence=conf
            )
            assert abs(rec.confidence - conf) < 0.01

        # Invalid confidences
        with pytest.raises(ValidationError):
            ModelRecommendation(
                model="gpt-4",
                provider="openai",
                confidence=-0.1
            )

        with pytest.raises(ValidationError):
            ModelRecommendation(
                model="gpt-4",
                provider="openai",
                confidence=1.5
            )


# ============================================================================
# StageModelRecommendations Schema Tests
# ============================================================================

class TestStageModelRecommendations:
    """Test StageModelRecommendations schema."""

    def test_valid_stage_recommendations(self):
        """Test valid recommendations for all stages."""
        recs = StageModelRecommendations(
            initial=ModelRecommendation(model="gpt-4", provider="openai", confidence=0.8),
            review=ModelRecommendation(model="claude-3-opus-20240229", provider="anthropic", confidence=0.85),
            refinement=ModelRecommendation(model="gpt-4", provider="openai", confidence=0.8),
            final=ModelRecommendation(model="claude-3-opus-20240229", provider="anthropic", confidence=0.9),
            confidence=0.85,
            based_on_samples=25
        )

        assert recs.initial.model == "gpt-4"
        assert recs.review.provider == "anthropic"
        assert recs.confidence == 0.85
        assert recs.based_on_samples == 25

    def test_all_stages_required(self):
        """Test that all four stages are required."""
        with pytest.raises(ValidationError):
            StageModelRecommendations(
                initial=ModelRecommendation(model="gpt-4", provider="openai", confidence=0.8),
                review=ModelRecommendation(model="claude-3-opus-20240229", provider="anthropic", confidence=0.85),
                # Missing refinement and final
                confidence=0.5,
                based_on_samples=10
            )


# ============================================================================
# TimeEstimateRecommendation Schema Tests
# ============================================================================

class TestTimeEstimateRecommendation:
    """Test TimeEstimateRecommendation schema."""

    def test_valid_time_estimate(self):
        """Test valid time estimate."""
        estimate = TimeEstimateRecommendation(
            estimated_minutes=60,
            confidence=0.75,
            based_on_samples=15
        )

        assert estimate.estimated_minutes == 60
        assert estimate.confidence == 0.75
        assert estimate.based_on_samples == 15

    def test_negative_minutes_rejected(self):
        """Test that negative minutes are rejected."""
        with pytest.raises(ValidationError):
            TimeEstimateRecommendation(
                estimated_minutes=-30,
                confidence=0.5,
                based_on_samples=10
            )


# ============================================================================
# AIEstimationFeedback Schema Tests
# ============================================================================

class TestAIEstimationFeedback:
    """Test AIEstimationFeedback schemas."""

    def test_valid_feedback_create(self):
        """Test creating valid estimation feedback."""
        feedback = AIEstimationFeedbackCreate(
            task_category="feature",
            task_complexity="medium",
            executor_type="claude_code",
            estimated_minutes=60,
            actual_minutes=55,
            accuracy_ratio=0.92
        )

        assert feedback.task_category == "feature"
        assert feedback.estimated_minutes == 60
        assert feedback.actual_minutes == 55
        assert abs(feedback.accuracy_ratio - 0.92) < 0.01

    def test_negative_minutes_rejected(self):
        """Test that negative minutes are rejected."""
        with pytest.raises(ValidationError):
            AIEstimationFeedbackCreate(
                task_category="feature",
                estimated_minutes=-60,
                actual_minutes=55,
                accuracy_ratio=0.92
            )

    def test_accuracy_ratio_bounds(self):
        """Test accuracy ratio validation (0.0-2.0)."""
        # Valid ratios
        for ratio in [0.0, 0.5, 1.0, 1.5, 2.0]:
            feedback = AIEstimationFeedbackCreate(
                task_category="feature",
                estimated_minutes=60,
                actual_minutes=60,
                accuracy_ratio=ratio
            )
            assert abs(feedback.accuracy_ratio - ratio) < 0.01

        # Invalid ratios
        with pytest.raises(ValidationError):
            AIEstimationFeedbackCreate(
                task_category="feature",
                estimated_minutes=60,
                actual_minutes=60,
                accuracy_ratio=-0.1
            )

        with pytest.raises(ValidationError):
            AIEstimationFeedbackCreate(
                task_category="feature",
                estimated_minutes=60,
                actual_minutes=60,
                accuracy_ratio=2.5
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestSchemaIntegration:
    """Test schema integration and serialization."""

    def test_full_planning_workflow_serialization(self):
        """Test serializing a complete planning workflow."""
        # Create complete planning outcome
        outcome = PlanningOutcomeCreate(
            session_id="integration-test-123",
            workflow_type="multi_ai_planning",
            task_type="feature",
            request_complexity="medium",
            codebase_context={"files": 100, "lines": 25000},
            stages=[
                StageResult(
                    stage=1,
                    type="initial",
                    model="gpt-4",
                    provider="openai",
                    duration_ms=5000,
                    tokens_in=1500,
                    tokens_out=2000
                ),
                StageResult(
                    stage=2,
                    type="review",
                    model="claude-3-opus-20240229",
                    provider="anthropic",
                    duration_ms=4500,
                    tokens_in=1800,
                    tokens_out=2200
                )
            ],
            total_duration_ms=25000,
            total_tokens_used=7500,
            total_cost_cents=95,
            iteration_count=1
        )

        # Serialize to dict
        data = outcome.model_dump()

        assert data["session_id"] == "integration-test-123"
        assert len(data["stages"]) == 2
        assert data["stages"][0]["model"] == "gpt-4"
        assert data["codebase_context"]["files"] == 100

        # Serialize to JSON
        json_str = outcome.model_dump_json()
        assert "integration-test-123" in json_str
        assert "gpt-4" in json_str

    def test_nested_model_validation(self):
        """Test validation cascades through nested models."""
        # Invalid nested stage should fail
        with pytest.raises(ValidationError):
            PlanningOutcomeCreate(
                session_id="test",
                workflow_type="multi_ai_planning",
                stages=[
                    StageResult(
                        stage=1,
                        type="initial",
                        model="gpt-4",
                        provider="openai",
                        duration_ms=-1000,  # Invalid nested value
                        tokens_in=1500,
                        tokens_out=2000
                    )
                ],
                total_duration_ms=1000,
                total_tokens_used=500,
                total_cost_cents=10
            )

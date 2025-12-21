"""
Tests for Multi-AI Planning Learning Router API Endpoints

Tests:
- Planning outcome recording endpoints
- Model performance query endpoints
- Recommendation endpoints
- Feedback and execution recording
- Error handling and edge cases
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.planning_models import Base, PlanningOutcome, PlanningModelPerformance


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


@pytest.fixture
def client(test_db):
    """Create test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# Recording Endpoint Tests
# ============================================================================

class TestRecordPlanningOutcome:
    """Test POST /api/v1/learning/planning-outcomes"""

    def test_record_planning_outcome_success(self, client, test_db):
        """Test successfully recording a planning outcome."""
        session_id = str(uuid.uuid4())
        payload = {
            "session_id": session_id,
            "workflow_type": "multi_ai_planning",
            "task_type": "feature",
            "request_complexity": "medium",
            "stages": [
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
            "total_duration_ms": 25000,
            "total_tokens_used": 7500,
            "total_cost_cents": 85,
            "iteration_count": 1
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "recorded"

        # Verify record was created in database
        outcome = test_db.query(PlanningOutcome).filter_by(session_id=session_id).first()
        assert outcome is not None
        assert outcome.task_type == "feature"

    def test_record_planning_outcome_with_codebase_context(self, client, test_db):
        """Test recording with codebase context."""
        payload = {
            "session_id": str(uuid.uuid4()),
            "workflow_type": "multi_ai_planning",
            "codebase_context": {"files": 150, "lines": 30000, "language": "python"},
            "stages": [],
            "total_duration_ms": 20000,
            "total_tokens_used": 8000,
            "total_cost_cents": 70
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=payload)

        assert response.status_code == 200

    def test_record_planning_outcome_invalid_complexity(self, client):
        """Test that invalid complexity is rejected."""
        payload = {
            "session_id": str(uuid.uuid4()),
            "workflow_type": "multi_ai_planning",
            "request_complexity": "ultra-difficult",  # Invalid
            "stages": [],
            "total_duration_ms": 20000,
            "total_tokens_used": 8000,
            "total_cost_cents": 70
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=payload)

        assert response.status_code == 422  # Validation error

    def test_record_planning_outcome_negative_values(self, client):
        """Test that negative values are rejected."""
        payload = {
            "session_id": str(uuid.uuid4()),
            "workflow_type": "multi_ai_planning",
            "stages": [],
            "total_duration_ms": -1000,  # Invalid
            "total_tokens_used": 8000,
            "total_cost_cents": 70
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=payload)

        assert response.status_code == 422


class TestUpdateExecutionResult:
    """Test PATCH /api/v1/learning/planning-outcomes/{id}/execution"""

    def test_update_execution_result_success(self, client, test_db):
        """Test updating execution result."""
        # Create planning outcome first
        outcome_id = str(uuid.uuid4())
        outcome = PlanningOutcome(
            id=outcome_id,
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            stages=[],
            total_duration_ms=20000,
            total_tokens_used=8000,
            total_cost_cents=70
        )
        test_db.add(outcome)
        test_db.commit()

        # Update with execution result
        payload = {
            "success": True,
            "duration_seconds": 180,
            "tasks_completed": 5,
            "tasks_failed": 0
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/{outcome_id}/execution",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"

        # Verify database was updated
        updated = test_db.query(PlanningOutcome).filter_by(id=outcome_id).first()
        assert updated.execution_success is True
        assert updated.execution_duration_seconds == 180
        assert updated.tasks_completed == 5

    def test_update_execution_result_not_found(self, client):
        """Test updating non-existent outcome."""
        payload = {
            "success": True,
            "duration_seconds": 180
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/nonexistent-id/execution",
            json=payload
        )

        assert response.status_code == 404


class TestRecordUserFeedback:
    """Test PATCH /api/v1/learning/planning-outcomes/{id}/feedback"""

    def test_record_user_feedback_success(self, client, test_db):
        """Test recording user feedback."""
        # Create planning outcome first
        outcome_id = str(uuid.uuid4())
        outcome = PlanningOutcome(
            id=outcome_id,
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            stages=[],
            total_duration_ms=20000,
            total_tokens_used=8000,
            total_cost_cents=70
        )
        test_db.add(outcome)
        test_db.commit()

        # Record feedback
        payload = {
            "rating": 5,
            "feedback": "Excellent plan!",
            "plan_was_modified": False,
            "modification_extent": 0.0
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/{outcome_id}/feedback",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"

        # Verify database was updated
        updated = test_db.query(PlanningOutcome).filter_by(id=outcome_id).first()
        assert updated.user_rating == 5
        assert "Excellent" in updated.user_feedback

    def test_record_feedback_invalid_rating(self, client, test_db):
        """Test that invalid rating is rejected."""
        outcome_id = str(uuid.uuid4())
        outcome = PlanningOutcome(
            id=outcome_id,
            session_id=str(uuid.uuid4()),
            workflow_type="multi_ai_planning",
            stages=[],
            total_duration_ms=20000,
            total_tokens_used=8000,
            total_cost_cents=70
        )
        test_db.add(outcome)
        test_db.commit()

        payload = {
            "rating": 6,  # Invalid (must be 1-5)
            "feedback": "Too high!"
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/{outcome_id}/feedback",
            json=payload
        )

        assert response.status_code == 422


# ============================================================================
# Recommendation Endpoint Tests
# ============================================================================

class TestGetModelPerformance:
    """Test GET /api/v1/learning/model-performance"""

    def test_get_model_performance_no_filters(self, client, test_db):
        """Test getting all model performance records."""
        # Create test records
        perf1 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="initial",
            ema_quality=0.85,
            sample_count=10
        )
        perf2 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="claude-3-opus-20240229",
            provider="anthropic",
            stage_type="review",
            ema_quality=0.90,
            sample_count=15
        )
        test_db.add_all([perf1, perf2])
        test_db.commit()

        response = client.get("/api/v1/learning/model-performance")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_model_performance_with_filters(self, client, test_db):
        """Test filtering by model and stage."""
        # Create test records
        perf1 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="initial",
            task_type="feature",
            ema_quality=0.85,
            sample_count=10
        )
        perf2 = PlanningModelPerformance(
            id=str(uuid.uuid4()),
            model="gpt-4",
            provider="openai",
            stage_type="refinement",
            task_type="feature",
            ema_quality=0.88,
            sample_count=12
        )
        test_db.add_all([perf1, perf2])
        test_db.commit()

        response = client.get(
            "/api/v1/learning/model-performance",
            params={"model": "gpt-4", "stage_type": "initial"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["stage_type"] == "initial"


class TestGetStageModelRecommendations:
    """Test GET /api/v1/learning/recommendations/stage-models"""

    def test_get_recommendations_with_data(self, client, test_db):
        """Test getting recommendations when historical data exists."""
        # Create performance records for each stage
        stages = ["initial", "review", "refinement", "final"]
        models = {
            "initial": ("gpt-4", "openai"),
            "review": ("claude-3-opus-20240229", "anthropic"),
            "refinement": ("gpt-4", "openai"),
            "final": ("claude-3-opus-20240229", "anthropic")
        }

        for stage in stages:
            model, provider = models[stage]
            perf = PlanningModelPerformance(
                id=str(uuid.uuid4()),
                model=model,
                provider=provider,
                stage_type=stage,
                task_type="feature",
                ema_quality=0.85,
                sample_count=15
            )
            test_db.add(perf)

        test_db.commit()

        response = client.get("/api/v1/learning/recommendations/stage-models")

        assert response.status_code == 200
        data = response.json()
        assert "initial" in data
        assert "review" in data
        assert "refinement" in data
        assert "final" in data
        assert data["initial"]["model"] == "gpt-4"
        assert data["confidence"] > 0

    def test_get_recommendations_no_data_returns_defaults(self, client, test_db):
        """Test that defaults are returned when no historical data."""
        response = client.get("/api/v1/learning/recommendations/stage-models")

        assert response.status_code == 200
        data = response.json()
        # Should return default models
        assert "initial" in data
        assert "review" in data
        assert data["confidence"] < 0.5  # Low confidence for defaults


class TestGetTimeEstimate:
    """Test GET /api/v1/learning/recommendations/time-estimate"""

    def test_get_time_estimate_with_data(self, client, test_db):
        """Test getting time estimate with historical data."""
        from app.models.planning_models import AIEstimationFeedback

        # Create feedback records
        for i in range(10):
            feedback = AIEstimationFeedback(
                id=str(uuid.uuid4()),
                task_category="feature",
                task_complexity="medium",
                executor_type="claude_code",
                estimated_minutes=60,
                actual_minutes=55 + i,
                accuracy_ratio=0.9
            )
            test_db.add(feedback)

        test_db.commit()

        response = client.get(
            "/api/v1/learning/recommendations/time-estimate",
            params={
                "task_category": "feature",
                "task_complexity": "medium",
                "executor_type": "claude_code"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "estimated_minutes" in data
        assert "confidence" in data
        assert data["estimated_minutes"] > 0

    def test_get_time_estimate_no_data_returns_default(self, client):
        """Test that default estimate is returned when no data."""
        response = client.get(
            "/api/v1/learning/recommendations/time-estimate",
            params={
                "task_category": "feature",
                "task_complexity": "simple"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["estimated_minutes"] > 0
        assert data["confidence"] < 0.5  # Low confidence for defaults


class TestGetIterationRecommendation:
    """Test GET /api/v1/learning/recommendations/iteration-count"""

    def test_get_iteration_recommendation(self, client, test_db):
        """Test getting iteration count recommendation."""
        # Create outcomes with different iteration counts
        for i in range(5):
            outcome = PlanningOutcome(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                workflow_type="multi_ai_planning",
                task_type="feature",
                request_complexity="complex",
                stages=[],
                total_duration_ms=20000,
                total_tokens_used=8000,
                total_cost_cents=70,
                iteration_count=2,
                execution_success=True
            )
            test_db.add(outcome)

        test_db.commit()

        response = client.get(
            "/api/v1/learning/recommendations/iteration-count",
            params={"task_type": "feature", "complexity": "complex"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommended" in data
        assert "confidence" in data


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_outcome_id(self, client):
        """Test handling of invalid outcome ID."""
        response = client.patch(
            "/api/v1/learning/planning-outcomes/invalid-uuid/feedback",
            json={"rating": 5}
        )

        assert response.status_code == 404

    def test_missing_required_fields(self, client):
        """Test that missing required fields are caught."""
        payload = {
            "session_id": str(uuid.uuid4()),
            # Missing workflow_type, stages, etc.
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=payload)

        assert response.status_code == 422

    def test_invalid_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/learning/planning-outcomes",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_planning_workflow(self, client, test_db):
        """Test recording and querying a complete workflow."""
        session_id = str(uuid.uuid4())

        # 1. Record planning outcome
        outcome_payload = {
            "session_id": session_id,
            "workflow_type": "multi_ai_planning",
            "task_type": "feature",
            "request_complexity": "medium",
            "stages": [
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
            "total_duration_ms": 25000,
            "total_tokens_used": 7500,
            "total_cost_cents": 85,
            "iteration_count": 1
        }

        response = client.post("/api/v1/learning/planning-outcomes", json=outcome_payload)
        assert response.status_code == 200
        outcome_id = response.json()["id"]

        # 2. Update with execution result
        exec_payload = {
            "success": True,
            "duration_seconds": 180,
            "tasks_completed": 5,
            "tasks_failed": 0
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/{outcome_id}/execution",
            json=exec_payload
        )
        assert response.status_code == 200

        # 3. Record user feedback
        feedback_payload = {
            "rating": 5,
            "feedback": "Great plan!",
            "plan_was_modified": False
        }

        response = client.patch(
            f"/api/v1/learning/planning-outcomes/{outcome_id}/feedback",
            json=feedback_payload
        )
        assert response.status_code == 200

        # 4. Verify complete record in database
        outcome = test_db.query(PlanningOutcome).filter_by(id=outcome_id).first()
        assert outcome is not None
        assert outcome.execution_success is True
        assert outcome.user_rating == 5
        assert "Great" in outcome.user_feedback

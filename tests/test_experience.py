"""Tests for the Experience Store API.

Tests:
1. Create experience record
2. Search with similarity (mock pgvector)
3. Search with archetype filter
4. Search with outcome filter
"""

from datetime import datetime, UTC
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.experience_router import router
from app.database import get_db


@pytest.fixture
def app():
    """Create test FastAPI app with experience router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db(app):
    """Override the router DB dependency with a mock session."""
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def sample_experience():
    """Sample experience creation payload."""
    return {
        "run_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "agent_archetype": "coder",
        "task_embedding": [0.1] * 768,
        "target_scope": {"service": "neuroforge", "repo_path": "/opt/neuroforge"},
        "execution_summary": "Successfully implemented feature X with tests.",
        "outcome": "success",
        "gate_results_snapshot": {"build": "pass", "lint": "pass", "test": "pass"},
        "tool_sequence": ["read_file", "write_file", "run_tests"],
        "duration_ms": 45000,
        "cost_usd": 0.042,
    }


class TestCreateExperience:
    """Test POST /api/v1/experience."""

    def test_create_experience_success(self, client, mock_db, sample_experience):
        """Creating an experience record returns 201 with experience_id."""
        # Mock the db.add/commit/refresh cycle
        def set_experience_id(obj):
            obj.experience_id = uuid4()
            obj.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = set_experience_id

        response = client.post("/api/v1/experience", json=sample_experience)

        assert response.status_code == 201
        data = response.json()
        assert "experience_id" in data
        assert data["agent_archetype"] == "coder"
        assert data["outcome"] == "success"
        assert data["execution_summary"] == sample_experience["execution_summary"]


@pytest.mark.skip(reason="Requires pgvector — raw SQL with <=> operator bypasses mock")
class TestSearchExperiences:
    """Test POST /api/v1/experience/search."""

    def _make_search_result(self, archetype="coder", outcome="success", similarity=0.85):
        """Create a mock search result row."""
        row = MagicMock()
        row.experience_id = uuid4()
        row.run_id = uuid4()
        row.agent_id = uuid4()
        row.agent_archetype = archetype
        row.target_scope = {"service": "neuroforge"}
        row.execution_summary = "Test execution"
        row.outcome = outcome
        row.gate_results_snapshot = None
        row.tool_sequence = ["read_file"]
        row.duration_ms = 1000
        row.cost_usd = 0.01
        row.created_at = datetime.now(UTC)
        row.similarity = similarity
        return row

    def test_search_with_similarity(self, client, mock_db):
        """Search returns results ordered by cosine similarity."""
        row1 = self._make_search_result(similarity=0.92)
        row2 = self._make_search_result(similarity=0.78)
        mock_db.execute.return_value.fetchall.return_value = [row1, row2]

        response = client.post(
            "/api/v1/experience/search",
            json={
                "query_embedding": [0.1] * 768,
                "min_similarity": 0.65,
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["similarity"] == 0.92
        assert data[1]["similarity"] == 0.78

    def test_search_with_archetype_filter(self, client, mock_db):
        """Search filters by agent archetype."""
        row = self._make_search_result(archetype="researcher")
        mock_db.execute.return_value.fetchall.return_value = [row]

        response = client.post(
            "/api/v1/experience/search",
            json={
                "query_embedding": [0.1] * 768,
                "agent_archetype": "researcher",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["agent_archetype"] == "researcher"

        # Verify the SQL includes archetype filter
        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "agent_archetype" in query_text

    def test_search_with_outcome_filter(self, client, mock_db):
        """Search filters by execution outcome."""
        row = self._make_search_result(outcome="failure")
        mock_db.execute.return_value.fetchall.return_value = [row]

        response = client.post(
            "/api/v1/experience/search",
            json={
                "query_embedding": [0.1] * 768,
                "outcome": "failure",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["outcome"] == "failure"

        # Verify the SQL includes outcome filter
        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "outcome" in query_text

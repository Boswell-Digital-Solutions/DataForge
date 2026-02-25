"""
Tests for Sentinel Agent API endpoints.

Covers:
  - Sweep CRUD (create, list, get, update, latest)
  - Healing event CRUD (create, list, update)
  - Filtering, pagination, and 404 handling
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestSweepEndpoints:
    """Test Sentinel sweep endpoints."""

    def test_create_sweep_light(self, client: TestClient):
        """POST /api/v1/sentinel/sweeps — create a light sweep."""
        response = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "light", "trigger": "manual"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sweep_type"] == "light"
        assert data["status"] == "running"
        assert data["trigger"] == "manual"
        assert data["overall_status"] == "unknown"
        assert data["dimensions_checked"] == []
        assert data["findings"] == []
        assert "id" in data
        assert "started_at" in data

    def test_create_sweep_deep(self, client: TestClient):
        """POST /api/v1/sentinel/sweeps — create a deep sweep."""
        response = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "deep", "trigger": "anomaly"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sweep_type"] == "deep"
        assert data["trigger"] == "anomaly"

    def test_create_sweep_default_trigger(self, client: TestClient):
        """POST /api/v1/sentinel/sweeps — default trigger is scheduled."""
        response = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "light"},
        )
        assert response.status_code == 201
        assert response.json()["trigger"] == "scheduled"

    def test_create_sweep_invalid_type(self, client: TestClient):
        """POST /api/v1/sentinel/sweeps — reject invalid sweep_type."""
        response = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "ultra"},
        )
        assert response.status_code == 422

    def test_list_sweeps_empty(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps — empty list initially."""
        response = client.get("/api/v1/sentinel/sweeps")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_sweeps_returns_created(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps — returns previously created sweeps."""
        # Create two sweeps
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "light"})
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "deep"})

        response = client.get("/api/v1/sentinel/sweeps")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_sweeps_filter_by_status(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps?status=running — filter by status."""
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "light"})

        response = client.get("/api/v1/sentinel/sweeps?status=running")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

        response = client.get("/api/v1/sentinel/sweeps?status=completed")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_sweeps_filter_by_type(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps?sweep_type=deep — filter by type."""
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "light"})
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "deep"})

        response = client.get("/api/v1/sentinel/sweeps?sweep_type=deep")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["sweep_type"] == "deep"

    def test_list_sweeps_pagination(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps — limit and offset work."""
        for _ in range(3):
            client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "light"})

        response = client.get("/api/v1/sentinel/sweeps?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

        response = client.get("/api/v1/sentinel/sweeps?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_get_sweep_by_id(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps/{id} — fetch by UUID."""
        create_resp = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "deep", "trigger": "manual"},
        )
        sweep_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/sentinel/sweeps/{sweep_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sweep_id
        assert data["sweep_type"] == "deep"

    def test_get_sweep_not_found(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps/{id} — 404 for unknown UUID."""
        response = client.get(f"/api/v1/sentinel/sweeps/{uuid4()}")
        assert response.status_code == 404

    def test_update_sweep_status(self, client: TestClient):
        """PATCH /api/v1/sentinel/sweeps/{id} — update status to completed."""
        create_resp = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "light"},
        )
        sweep_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/v1/sentinel/sweeps/{sweep_id}",
            json={
                "status": "completed",
                "overall_status": "healthy",
                "duration_ms": 450,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["overall_status"] == "healthy"
        assert data["duration_ms"] == 450

    def test_update_sweep_with_findings(self, client: TestClient):
        """PATCH /api/v1/sentinel/sweeps/{id} — update with dimension findings."""
        create_resp = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "deep"},
        )
        sweep_id = create_resp.json()["id"]

        findings = [
            {
                "dimension": "D1",
                "dimension_name": "Service Liveness",
                "status": "healthy",
                "details": "All 5 services responding",
                "metrics": {"latency_avg_ms": 42},
                "duration_ms": 120,
            },
            {
                "dimension": "D3",
                "dimension_name": "Circuit Breaker State",
                "status": "degraded",
                "details": "Rake breaker stuck open",
                "metrics": {"stuck_breakers": 1},
                "duration_ms": 80,
            },
        ]

        response = client.patch(
            f"/api/v1/sentinel/sweeps/{sweep_id}",
            json={
                "status": "completed",
                "overall_status": "degraded",
                "findings": findings,
                "duration_ms": 1200,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "degraded"
        assert len(data["findings"]) == 2
        assert "D1" in data["dimensions_checked"]
        assert "D3" in data["dimensions_checked"]

    def test_update_sweep_not_found(self, client: TestClient):
        """PATCH /api/v1/sentinel/sweeps/{id} — 404 for unknown UUID."""
        response = client.patch(
            f"/api/v1/sentinel/sweeps/{uuid4()}",
            json={"status": "completed"},
        )
        assert response.status_code == 404

    def test_latest_sweep(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps/latest/status — returns most recent sweep."""
        client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "light"})
        resp2 = client.post("/api/v1/sentinel/sweeps", json={"sweep_type": "deep"})
        latest_id = resp2.json()["id"]

        response = client.get("/api/v1/sentinel/sweeps/latest/status")
        assert response.status_code == 200
        # Latest should be the deep sweep (most recent started_at)
        data = response.json()
        assert data is not None
        assert data["id"] == latest_id

    def test_latest_sweep_empty(self, client: TestClient):
        """GET /api/v1/sentinel/sweeps/latest/status — null when no sweeps exist."""
        response = client.get("/api/v1/sentinel/sweeps/latest/status")
        assert response.status_code == 200
        # No sweeps — should return null
        assert response.json() is None


@pytest.mark.unit
class TestHealingEventEndpoints:
    """Test Sentinel healing event endpoints."""

    def _create_sweep(self, client: TestClient) -> str:
        """Helper: create a sweep and return its ID."""
        resp = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "light", "trigger": "manual"},
        )
        return resp.json()["id"]

    def test_create_healing_event(self, client: TestClient):
        """POST /api/v1/sentinel/healing — create a healing event."""
        sweep_id = self._create_sweep(client)

        response = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "cache_flush",
                "tier": "A",
                "action": "Flush Redis cache for degraded Rake service",
                "target_service": "rake",
                "governed": False,
                "details": {"reason": "D3 breaker stuck"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sweep_id"] == sweep_id
        assert data["playbook"] == "cache_flush"
        assert data["tier"] == "A"
        assert data["target_service"] == "rake"
        assert data["outcome"] == "pending"
        assert data["governed"] is False
        assert "id" in data
        assert "created_at" in data

    def test_create_healing_event_tier_b(self, client: TestClient):
        """POST /api/v1/sentinel/healing — supervised (Tier B) event."""
        sweep_id = self._create_sweep(client)

        response = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "config_sync",
                "tier": "B",
                "action": "Sync embedding dimensions across services",
                "governed": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "B"
        assert data["governed"] is True

    def test_create_healing_event_tier_c(self, client: TestClient):
        """POST /api/v1/sentinel/healing — escalation (Tier C) event."""
        sweep_id = self._create_sweep(client)

        response = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "escalate_critical",
                "tier": "C",
                "action": "DataForge unreachable — escalate to operator",
                "target_service": "dataforge",
                "governed": True,
            },
        )
        assert response.status_code == 201
        assert response.json()["tier"] == "C"

    def test_create_healing_event_sweep_not_found(self, client: TestClient):
        """POST /api/v1/sentinel/healing — 404 for unknown sweep_id."""
        response = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": str(uuid4()),
                "playbook": "cache_flush",
                "tier": "A",
                "action": "Test action",
            },
        )
        assert response.status_code == 404

    def test_list_healing_events_empty(self, client: TestClient):
        """GET /api/v1/sentinel/healing — empty list initially."""
        response = client.get("/api/v1/sentinel/healing")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_healing_events_returns_created(self, client: TestClient):
        """GET /api/v1/sentinel/healing — returns previously created events."""
        sweep_id = self._create_sweep(client)

        client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "cache_flush",
                "tier": "A",
                "action": "Flush caches",
            },
        )
        client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "breaker_reset",
                "tier": "A",
                "action": "Reset breaker",
            },
        )

        response = client.get("/api/v1/sentinel/healing")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_healing_events_filter_by_sweep(self, client: TestClient):
        """GET /api/v1/sentinel/healing?sweep_id=... — filter by sweep."""
        sweep1_id = self._create_sweep(client)
        sweep2_id = self._create_sweep(client)

        client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep1_id,
                "playbook": "cache_flush",
                "tier": "A",
                "action": "Flush from sweep 1",
            },
        )
        client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep2_id,
                "playbook": "breaker_reset",
                "tier": "A",
                "action": "Reset from sweep 2",
            },
        )

        response = client.get(f"/api/v1/sentinel/healing?sweep_id={sweep1_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["sweep_id"] == sweep1_id

    def test_list_healing_events_filter_by_tier(self, client: TestClient):
        """GET /api/v1/sentinel/healing?tier=A — filter by tier."""
        sweep_id = self._create_sweep(client)

        client.post(
            "/api/v1/sentinel/healing",
            json={"sweep_id": sweep_id, "playbook": "cache_flush", "tier": "A", "action": "a1"},
        )
        client.post(
            "/api/v1/sentinel/healing",
            json={"sweep_id": sweep_id, "playbook": "escalate", "tier": "C", "action": "c1", "governed": True},
        )

        response = client.get("/api/v1/sentinel/healing?tier=A")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["tier"] == "A"

    def test_list_healing_events_filter_by_outcome(self, client: TestClient):
        """GET /api/v1/sentinel/healing?outcome=pending — filter by outcome."""
        sweep_id = self._create_sweep(client)

        resp = client.post(
            "/api/v1/sentinel/healing",
            json={"sweep_id": sweep_id, "playbook": "cache_flush", "tier": "A", "action": "flush"},
        )
        event_id = resp.json()["id"]

        # All events start as pending
        response = client.get("/api/v1/sentinel/healing?outcome=pending")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        # Update to success and verify filter
        client.patch(
            f"/api/v1/sentinel/healing/{event_id}",
            json={"outcome": "success", "duration_ms": 200},
        )

        response = client.get("/api/v1/sentinel/healing?outcome=pending")
        assert response.status_code == 200
        assert response.json()["total"] == 0

        response = client.get("/api/v1/sentinel/healing?outcome=success")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_list_healing_events_pagination(self, client: TestClient):
        """GET /api/v1/sentinel/healing — pagination works."""
        sweep_id = self._create_sweep(client)

        for i in range(5):
            client.post(
                "/api/v1/sentinel/healing",
                json={"sweep_id": sweep_id, "playbook": f"playbook_{i}", "tier": "A", "action": f"action {i}"},
            )

        response = client.get("/api/v1/sentinel/healing?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_update_healing_event_outcome(self, client: TestClient):
        """PATCH /api/v1/sentinel/healing/{id} — update outcome."""
        sweep_id = self._create_sweep(client)

        create_resp = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "breaker_reset",
                "tier": "A",
                "action": "Reset stuck Rake breaker",
                "target_service": "rake",
            },
        )
        event_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/v1/sentinel/healing/{event_id}",
            json={
                "outcome": "success",
                "duration_ms": 320,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "success"
        assert data["duration_ms"] == 320

    def test_update_healing_event_escalated(self, client: TestClient):
        """PATCH /api/v1/sentinel/healing/{id} — mark as escalated."""
        sweep_id = self._create_sweep(client)

        create_resp = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "escalate_critical",
                "tier": "C",
                "action": "Escalate DataForge outage",
                "governed": True,
            },
        )
        event_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/v1/sentinel/healing/{event_id}",
            json={"outcome": "escalated", "approval_id": "gov-evt-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "escalated"
        assert data["approval_id"] == "gov-evt-12345"

    def test_update_healing_event_not_found(self, client: TestClient):
        """PATCH /api/v1/sentinel/healing/{id} — 404 for unknown UUID."""
        response = client.patch(
            f"/api/v1/sentinel/healing/{uuid4()}",
            json={"outcome": "success"},
        )
        assert response.status_code == 404


@pytest.mark.unit
class TestSweepHealingIntegration:
    """Test sweep + healing event integration."""

    def test_full_lifecycle(self, client: TestClient):
        """Full sweep lifecycle: create → findings → healing → outcome."""
        # 1. Create sweep
        sweep_resp = client.post(
            "/api/v1/sentinel/sweeps",
            json={"sweep_type": "deep", "trigger": "manual"},
        )
        sweep_id = sweep_resp.json()["id"]

        # 2. Update with findings
        client.patch(
            f"/api/v1/sentinel/sweeps/{sweep_id}",
            json={
                "status": "completed",
                "overall_status": "degraded",
                "findings": [
                    {
                        "dimension": "D3",
                        "dimension_name": "Circuit Breaker State",
                        "status": "degraded",
                        "details": "Rake breaker stuck open for 12m",
                        "metrics": {"stuck_duration_s": 720},
                        "duration_ms": 95,
                    },
                ],
                "duration_ms": 1800,
            },
        )

        # 3. Create healing event for the finding
        heal_resp = client.post(
            "/api/v1/sentinel/healing",
            json={
                "sweep_id": sweep_id,
                "playbook": "breaker_reset",
                "tier": "A",
                "action": "Probe Rake and trigger HALF_OPEN transition",
                "target_service": "rake",
                "details": {"stuck_duration_s": 720},
            },
        )
        event_id = heal_resp.json()["id"]
        assert heal_resp.json()["outcome"] == "pending"

        # 4. Update healing outcome
        outcome_resp = client.patch(
            f"/api/v1/sentinel/healing/{event_id}",
            json={"outcome": "success", "duration_ms": 250},
        )
        assert outcome_resp.json()["outcome"] == "success"

        # 5. Verify healing events are listed under the sweep
        healings = client.get(f"/api/v1/sentinel/healing?sweep_id={sweep_id}")
        assert healings.json()["total"] == 1
        assert healings.json()["items"][0]["id"] == event_id

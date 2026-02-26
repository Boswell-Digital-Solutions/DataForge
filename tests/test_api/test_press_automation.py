"""
Tests for PressForge v1.2 automation, governance, GEO, draftset, promptpack endpoints.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient


@pytest.mark.unit
class TestAutomationJobEndpoints:
    """Test automation job CRUD."""

    def test_create_automation_job(self, client: TestClient):
        resp = client.post("/api/v1/press/automation/jobs", json={
            "job_key": "journalist_refresh",
            "description": "Daily journalist profile refresh",
            "cron_schedule": "0 3 * * *",
            "config": {"stale_threshold_days": 30},
            "tier": 1,
            "cost_class": "low",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["job_key"] == "journalist_refresh"
        assert data["tier"] == 1
        assert data["enabled"] is True

    def test_list_automation_jobs(self, client: TestClient):
        # Create two jobs
        client.post("/api/v1/press/automation/jobs", json={
            "job_key": "test_job_a", "cron_schedule": "0 * * * *", "tier": 1,
        })
        client.post("/api/v1/press/automation/jobs", json={
            "job_key": "test_job_b", "cron_schedule": "0 * * * *", "tier": 2,
        })
        resp = client.get("/api/v1/press/automation/jobs")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_list_automation_jobs_filter_by_tier(self, client: TestClient):
        client.post("/api/v1/press/automation/jobs", json={
            "job_key": "tier_filter_t1", "cron_schedule": "0 * * * *", "tier": 1,
        })
        client.post("/api/v1/press/automation/jobs", json={
            "job_key": "tier_filter_t3", "cron_schedule": "0 * * * *", "tier": 3,
        })
        resp = client.get("/api/v1/press/automation/jobs", params={"tier": 1})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["tier"] == 1

    def test_update_automation_job(self, client: TestClient):
        create_resp = client.post("/api/v1/press/automation/jobs", json={
            "job_key": "update_test", "cron_schedule": "0 3 * * *", "tier": 1,
        })
        job_id = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/press/automation/jobs/{job_id}", json={
            "enabled": False, "cron_schedule": "0 6 * * *",
        })
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False
        assert resp.json()["cron_schedule"] == "0 6 * * *"


@pytest.mark.unit
class TestAutomationRunEndpoints:
    """Test automation run CRUD."""

    def _create_job(self, client: TestClient, key: str = "run_test_job") -> str:
        resp = client.post("/api/v1/press/automation/jobs", json={
            "job_key": key, "cron_schedule": "0 * * * *", "tier": 1,
        })
        return resp.json()["id"]

    def test_create_automation_run(self, client: TestClient):
        job_id = self._create_job(client, f"run_create_{uuid4().hex[:8]}")
        resp = client.post("/api/v1/press/automation/runs", json={
            "job_id": job_id,
            "job_key": "run_create_test",
            "status": "queued",
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "queued"

    def test_update_automation_run(self, client: TestClient):
        job_id = self._create_job(client, f"run_update_{uuid4().hex[:8]}")
        create_resp = client.post("/api/v1/press/automation/runs", json={
            "job_id": job_id, "job_key": "run_update_test",
        })
        run_id = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/press/automation/runs/{run_id}", json={
            "status": "success", "cost_tokens": 1500, "provider_used": "anthropic",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["cost_tokens"] == 1500

    def test_list_automation_runs_filter_by_status(self, client: TestClient):
        resp = client.get("/api/v1/press/automation/runs", params={"status": "success"})
        assert resp.status_code == 200


@pytest.mark.unit
class TestAutomationAlertEndpoints:
    """Test automation alert CRUD and dismiss."""

    def test_create_and_dismiss_alert(self, client: TestClient):
        resp = client.post("/api/v1/press/automation/alerts", json={
            "job_key": "journalist_refresh",
            "severity": "warn",
            "title": "Zero updates for 3 consecutive days",
            "detail": "No journalist profiles were updated since 2026-02-23",
        })
        assert resp.status_code == 201
        alert_id = resp.json()["id"]
        assert resp.json()["dismissed"] is False

        dismiss_resp = client.patch(
            f"/api/v1/press/automation/alerts/{alert_id}/dismiss",
            params={"dismissed_by": "charles"},
        )
        assert dismiss_resp.status_code == 200
        assert dismiss_resp.json()["dismissed"] is True
        assert dismiss_resp.json()["dismissed_by"] == "charles"

    def test_list_alerts_filter_undismissed(self, client: TestClient):
        resp = client.get("/api/v1/press/automation/alerts", params={"dismissed": False})
        assert resp.status_code == 200


@pytest.mark.unit
class TestAutomationOverrideEndpoints:
    """Test runtime config overrides with TTL validation."""

    def test_create_override_within_ttl(self, client: TestClient):
        expires = (datetime.utcnow() + timedelta(days=3)).isoformat()
        resp = client.post("/api/v1/press/automation/overrides", json={
            "job_key": "journalist_refresh",
            "override_config": {"stale_threshold_days": 14},
            "reason": "Book launch week — more aggressive refresh",
            "expires_at": expires,
            "created_by": "charles",
        })
        assert resp.status_code == 201

    def test_reject_override_exceeding_7day_ttl(self, client: TestClient):
        expires = (datetime.utcnow() + timedelta(days=10)).isoformat()
        resp = client.post("/api/v1/press/automation/overrides", json={
            "job_key": "journalist_refresh",
            "override_config": {"stale_threshold_days": 7},
            "reason": "Too long",
            "expires_at": expires,
            "created_by": "charles",
        })
        assert resp.status_code == 400

    def test_delete_override(self, client: TestClient):
        expires = (datetime.utcnow() + timedelta(days=1)).isoformat()
        create_resp = client.post("/api/v1/press/automation/overrides", json={
            "job_key": "del_test",
            "override_config": {},
            "reason": "temp",
            "expires_at": expires,
            "created_by": "charles",
        })
        override_id = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/press/automation/overrides/{override_id}")
        assert resp.status_code == 204


@pytest.mark.unit
class TestAgentLogEndpoints:
    """Test append-only agent log + decision recording."""

    def test_create_agent_log(self, client: TestClient):
        resp = client.post("/api/v1/press/agent-logs", json={
            "job_key": "evidence_staleness_sweep",
            "action_type": "widen_query",
            "input_state": {"coverage_score": 0.55, "campaign_id": str(uuid4())},
            "decision_rationale": "Coverage below 70%, widening query with governed retries",
            "output_action": {"new_query_terms": ["indie fantasy", "self-published"]},
            "risk_flags": {"high_risk": False, "escalation_required": False},
        })
        assert resp.status_code == 201
        assert resp.json()["accepted"] is None  # Not yet decided

    def test_record_decision_on_agent_log(self, client: TestClient):
        create_resp = client.post("/api/v1/press/agent-logs", json={
            "job_key": "test_decision",
            "action_type": "suggest_config",
            "decision_rationale": "Suggest increasing trust_floor",
            "output_action": {"suggested_trust_floor": 4},
        })
        log_id = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/press/agent-logs/{log_id}/decision", json={
            "accepted": True, "accepted_by": "charles",
        })
        assert resp.status_code == 200
        assert resp.json()["accepted"] is True

    def test_reject_duplicate_decision(self, client: TestClient):
        create_resp = client.post("/api/v1/press/agent-logs", json={
            "job_key": "dup_decision",
            "action_type": "escalate_human",
            "decision_rationale": "Test",
            "output_action": {},
        })
        log_id = create_resp.json()["id"]
        client.patch(f"/api/v1/press/agent-logs/{log_id}/decision", json={
            "accepted": True, "accepted_by": "charles",
        })
        dup_resp = client.patch(f"/api/v1/press/agent-logs/{log_id}/decision", json={
            "accepted": False, "accepted_by": "charles",
        })
        assert dup_resp.status_code == 409


@pytest.mark.unit
class TestProviderConfigEndpoints:
    """Test provider config CRUD."""

    def test_create_provider_config(self, client: TestClient):
        resp = client.post("/api/v1/press/provider-configs", json={
            "provider_key": "anthropic",
            "display_name": "Anthropic (Claude)",
            "supports_batch": True,
            "cost_per_1m_input": 3.0,
            "cost_per_1m_output": 15.0,
            "max_context_window": 200000,
        })
        assert resp.status_code == 201
        assert resp.json()["circuit_breaker_status"] == "closed"

    def test_update_circuit_breaker(self, client: TestClient):
        create_resp = client.post("/api/v1/press/provider-configs", json={
            "provider_key": f"test_cb_{uuid4().hex[:8]}",
            "display_name": "Test Provider",
        })
        config_id = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/press/provider-configs/{config_id}", json={
            "circuit_breaker_status": "open",
        })
        assert resp.status_code == 200
        assert resp.json()["circuit_breaker_status"] == "open"


@pytest.mark.unit
class TestGeoProbeEndpoints:
    """Test GEO probe + template CRUD."""

    def _create_campaign(self, client: TestClient) -> str:
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "GEO Test Campaign",
        })
        return resp.json()["id"]

    def test_create_geo_probe(self, client: TestClient):
        cid = self._create_campaign(client)
        resp = client.post("/api/v1/press/geo/probes", json={
            "campaign_id": cid,
            "provider": "chatgpt",
            "prompt_text": "What are the best indie fantasy books of 2026?",
            "brand_mentioned": True,
            "citation_found": False,
            "sentiment": "positive",
        })
        assert resp.status_code == 201
        assert resp.json()["brand_mentioned"] is True

    def test_create_geo_template(self, client: TestClient):
        cid = self._create_campaign(client)
        resp = client.post("/api/v1/press/geo/templates", json={
            "campaign_id": cid,
            "prompt_text": "Recommend books about {topic} in {genre}",
            "intent_category": "recommendation",
            "funnel_stage": "consideration",
        })
        assert resp.status_code == 201


@pytest.mark.unit
class TestSocialDraftsetEndpoints:
    """Test social draftset CRUD."""

    def _create_campaign(self, client: TestClient) -> str:
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "DraftSet Test Campaign",
        })
        return resp.json()["id"]

    def test_create_and_update_draftset(self, client: TestClient):
        cid = self._create_campaign(client)
        create_resp = client.post("/api/v1/press/social/draftsets", json={
            "campaign_id": cid,
            "intent": "announce",
            "platforms": ["facebook", "x", "linkedin"],
            "drafts": [
                {"platform": "facebook", "content": "Exciting news!", "char_count": 15},
                {"platform": "x", "content": "Big announcement", "char_count": 16},
            ],
        })
        assert create_resp.status_code == 201
        assert create_resp.json()["status"] == "draft"

        ds_id = create_resp.json()["id"]
        update_resp = client.patch(f"/api/v1/press/social/draftsets/{ds_id}", json={
            "status": "reviewed",
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "reviewed"


@pytest.mark.unit
class TestPromptPackEndpoints:
    """Test prompt pack CRUD."""

    def _create_campaign(self, client: TestClient) -> str:
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "PromptPack Test Campaign",
        })
        return resp.json()["id"]

    def test_create_prompt_pack(self, client: TestClient):
        cid = self._create_campaign(client)
        resp = client.post("/api/v1/press/media/promptpacks", json={
            "campaign_id": cid,
            "pack_name": "Book Launch Visual Pack",
            "sora_prompt": "Cinematic book reveal: leather-bound fantasy book...",
            "chatgpt_image_prompt": "Fantasy book cover with dragon and castle...",
            "gemini_prompt": "Generate a book promotion image: fantasy genre...",
            "aspect_ratios": {"facebook": "1200x628", "x": "1600x900"},
            "alt_text": "Fantasy book cover for The Dragon's Heir",
        })
        assert resp.status_code == 201
        assert resp.json()["pack_name"] == "Book Launch Visual Pack"


@pytest.mark.unit
class TestCampaignOutcomeEndpoints:
    """Test campaign outcome tracking."""

    def _create_campaign(self, client: TestClient) -> str:
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "Outcome Test Campaign",
        })
        return resp.json()["id"]

    def test_create_outcome(self, client: TestClient):
        cid = self._create_campaign(client)
        resp = client.post("/api/v1/press/campaign-outcomes", json={
            "campaign_id": cid,
            "outcome_type": "coverage_secured",
            "outcome_weight": 10,
            "notes": "Featured in Publisher's Weekly review",
        })
        assert resp.status_code == 201
        assert resp.json()["outcome_type"] == "coverage_secured"
        assert resp.json()["outcome_weight"] == 10

    def test_list_outcomes_by_campaign(self, client: TestClient):
        cid = self._create_campaign(client)
        client.post("/api/v1/press/campaign-outcomes", json={
            "campaign_id": cid, "outcome_type": "reply_received", "outcome_weight": 5,
        })
        client.post("/api/v1/press/campaign-outcomes", json={
            "campaign_id": cid, "outcome_type": "bounce", "outcome_weight": -3,
        })
        resp = client.get("/api/v1/press/campaign-outcomes", params={"campaign_id": cid})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


@pytest.mark.unit
class TestCampaignV12Fields:
    """Test v1.2 campaign_type and GEO share fields."""

    def test_campaign_type_default(self, client: TestClient):
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "Default Type Test",
        })
        assert resp.status_code == 201
        assert resp.json()["campaign_type"] == "book_launch"

    def test_campaign_type_specified(self, client: TestClient):
        resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "Author Platform",
            "campaign_type": "author_platform",
        })
        assert resp.status_code == 201
        assert resp.json()["campaign_type"] == "author_platform"

    def test_campaign_geo_share_update(self, client: TestClient):
        create_resp = client.post("/api/v1/press/campaigns", json={
            "project_id": str(uuid4()),
            "title": "GEO Share Test",
        })
        cid = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/press/campaigns/{cid}", json={
            "geo_share_pre": 0.12,
            "geo_share_post": 0.28,
        })
        assert resp.status_code == 200
        assert resp.json()["geo_share_pre"] == 0.12
        assert resp.json()["geo_share_post"] == 0.28

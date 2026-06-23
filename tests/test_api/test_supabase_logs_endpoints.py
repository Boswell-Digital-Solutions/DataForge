"""
Tests for the Supabase log events read API (GET /api/v1/supabase-logs/events).

Covers empty listing, redacted-row round-trip, category/since filtering, and
limit validation. The rows are the durable, already-redacted feed Sentinel reads
for anomaly sweeps.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.supabase_log_models import SupabaseLogEvent


def _add_event(
    db: Session,
    *,
    event_id: str,
    minutes_ago: int = 0,
    category: str = "auth",
    log_type: str = "auth",
) -> None:
    db.add(
        SupabaseLogEvent(
            id=event_id,
            event_time=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            log_type=log_type,
            level="error",
            status="401",
            method="POST",
            pathname="/auth/v1/token",
            latency_ms=12.0,
            category=category,
            message="authentication failed",
            event_metadata={"auth_user_hash": "abc123"},
            source="supabase",
            redacted=True,
        )
    )
    db.commit()


@pytest.mark.unit
class TestSupabaseLogEventsEndpoint:
    def test_empty_initially(self, client: TestClient):
        resp = client.get("/api/v1/supabase-logs/events")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_returns_redacted_rows(self, client: TestClient, db: Session):
        _add_event(db, event_id="e1")
        body = client.get("/api/v1/supabase-logs/events").json()
        assert body["total"] == 1
        row = body["items"][0]
        assert row["id"] == "e1"
        assert row["category"] == "auth"
        assert row["redacted"] is True
        assert row["event_metadata"]["auth_user_hash"] == "abc123"

    def test_filter_by_category(self, client: TestClient, db: Session):
        _add_event(db, event_id="auth-1", category="auth")
        _add_event(db, event_id="err-1", category="http_error", log_type="edge")
        body = client.get(
            "/api/v1/supabase-logs/events", params={"category": "http_error"}
        ).json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == "err-1"

    def test_filter_by_since(self, client: TestClient, db: Session):
        _add_event(db, event_id="recent", minutes_ago=1)
        _add_event(db, event_id="old", minutes_ago=120)
        since = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        body = client.get("/api/v1/supabase-logs/events", params={"since": since}).json()
        ids = [r["id"] for r in body["items"]]
        assert "recent" in ids
        assert "old" not in ids

    def test_limit_validation(self, client: TestClient):
        assert client.get("/api/v1/supabase-logs/events", params={"limit": 0}).status_code == 422
        assert (
            client.get("/api/v1/supabase-logs/events", params={"limit": 99999}).status_code == 422
        )

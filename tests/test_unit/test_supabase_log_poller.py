"""Focused production-path tests for the scheduled Supabase log poller."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.supabase_log_models import SupabaseLogEvent
from scripts import poll_supabase_logs as poller


class FakeResponse:
    def __init__(self, status_code: int, payload=None, *, json_error: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not json: PRIVATE-UPSTREAM-BODY")
        return self._payload


def configure_api(monkeypatch):
    monkeypatch.setattr(poller, "DATABASE_URL_IS_DEFAULT", False)
    monkeypatch.setattr(poller, "SUPABASE_PROJECT_REF", "abcdefghijklmnopqrst")
    monkeypatch.setattr(poller, "SUPABASE_ACCESS_TOKEN", "secret-management-token")
    monkeypatch.setattr(poller, "SUPABASE_API_BASE", "https://api.supabase.com")
    monkeypatch.setattr(poller, "SUPABASE_LOG_SOURCE_TABLE", "edge_logs")


@pytest.mark.unit
def test_missing_api_configuration_fails_before_network(monkeypatch):
    configure_api(monkeypatch)
    monkeypatch.setattr(poller, "SUPABASE_ACCESS_TOKEN", "")

    with pytest.raises(poller.PollerFailure) as raised:
        poller.validate_required_configuration(api_mode=True)

    assert raised.value.category is poller.FailureCategory.CONFIGURATION
    assert raised.value.code == "supabase_access_token_missing"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "category", "code"),
    [
        (401, poller.FailureCategory.AUTHENTICATION, "supabase_token_rejected"),
        (402, poller.FailureCategory.AUTHORIZATION, "supabase_logs_plan_required"),
        (403, poller.FailureCategory.AUTHORIZATION, "supabase_logs_access_forbidden"),
        (404, poller.FailureCategory.UPSTREAM_FAILURE, "supabase_project_or_endpoint_not_found"),
        (429, poller.FailureCategory.RATE_LIMITING, "supabase_logs_rate_limited"),
        (503, poller.FailureCategory.UPSTREAM_FAILURE, "supabase_api_server_error"),
    ],
)
def test_api_statuses_have_stable_categories(monkeypatch, status, category, code):
    configure_api(monkeypatch)

    with pytest.raises(poller.PollerFailure) as raised:
        poller.fetch_from_api(
            datetime.now(timezone.utc) - timedelta(minutes=5),
            10,
            http_get=lambda *args, **kwargs: FakeResponse(
                status, {"error": "PRIVATE-UPSTREAM-BODY"}
            ),
        )

    assert raised.value.category is category
    assert raised.value.code == code


@pytest.mark.unit
def test_network_failure_is_sanitized(monkeypatch):
    configure_api(monkeypatch)

    def fail_network(*args, **kwargs):
        raise httpx.RequestError("PRIVATE-NETWORK-DETAIL")

    with pytest.raises(poller.PollerFailure) as raised:
        poller.fetch_from_api(
            datetime.now(timezone.utc) - timedelta(minutes=5),
            10,
            http_get=fail_network,
        )

    assert raised.value.category is poller.FailureCategory.NETWORK_FAILURE
    assert "PRIVATE" not in str(raised.value)


@pytest.mark.unit
def test_response_schema_failure_does_not_expose_body(monkeypatch):
    configure_api(monkeypatch)

    with pytest.raises(poller.PollerFailure) as raised:
        poller.fetch_from_api(
            datetime.now(timezone.utc) - timedelta(minutes=5),
            10,
            http_get=lambda *args, **kwargs: FakeResponse(200, json_error=True),
        )

    assert raised.value.code == "supabase_response_not_json"
    assert "PRIVATE-UPSTREAM-BODY" not in str(raised.value)


@pytest.mark.unit
def test_success_uses_bounded_time_parameters_and_minimized_sql(monkeypatch):
    configure_api(monkeypatch)
    captured = {}

    def get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            200,
            {
                "result": [
                    {
                        "id": "event-1",
                        "timestamp": "2026-07-20T12:00:00Z",
                        "event_message": "upstream returned 503",
                    }
                ]
            },
        )

    rows = poller.fetch_from_api(
        datetime.now(timezone.utc) - timedelta(days=2),
        25,
        http_get=get,
    )

    assert rows[0]["log_type"] == "edge_logs"
    assert set(captured["params"]) == {
        "sql",
        "iso_timestamp_start",
        "iso_timestamp_end",
    }
    assert "select id, timestamp, event_message, source as log_type" in captured["params"]["sql"]
    assert "from logs" in captured["params"]["sql"]
    assert "source = 'edge_logs'" in captured["params"]["sql"]
    assert "metadata" not in captured["params"]["sql"]
    assert captured["url"].endswith("/analytics/endpoints/logs")
    start = datetime.fromisoformat(captured["params"]["iso_timestamp_start"])
    end = datetime.fromisoformat(captured["params"]["iso_timestamp_end"])
    assert end - start <= timedelta(hours=24)
    assert captured["headers"]["Authorization"] == "Bearer secret-management-token"


@pytest.mark.unit
def test_database_preflight_distinguishes_missing_migration():
    audit_engine = create_engine("sqlite:///:memory:")
    with Session(audit_engine) as session:
        with pytest.raises(poller.PollerFailure) as raised:
            poller.check_database_preflight(session)

    assert raised.value.category is poller.FailureCategory.DATABASE_MIGRATION_FAILURE
    assert raised.value.code == "supabase_log_events_table_missing"


@pytest.mark.unit
def test_invalid_overlap_fails_before_opening_a_session(monkeypatch, caplog):
    monkeypatch.setattr(poller, "SUPABASE_LOG_POLL_OVERLAP_SECONDS", -1)
    monkeypatch.setattr(
        poller,
        "SessionLocal",
        lambda: pytest.fail("session must not open for invalid CLI/config bounds"),
    )

    assert poller.main(["--once"]) == 1
    assert "code=poll_overlap_invalid" in caplog.text


@pytest.mark.unit
@pytest.mark.parametrize(
    ("setting", "code"),
    [
        ("SUPABASE_LOG_POLL_MAX_ROWS", "poll_limit_invalid"),
        ("SUPABASE_LOG_POLL_LOOKBACK_SECONDS", "poll_lookback_invalid"),
        ("SUPABASE_LOG_POLL_OVERLAP_SECONDS", "poll_overlap_invalid"),
    ],
)
def test_malformed_numeric_setting_fails_safely_before_session(
    monkeypatch, caplog, setting, code
):
    monkeypatch.setattr(poller, setting, None)
    monkeypatch.setattr(
        poller,
        "SessionLocal",
        lambda: pytest.fail("session must not open for malformed numeric config"),
    )

    assert poller.main(["--once"]) == 1
    assert f"code={code}" in caplog.text


@pytest.mark.unit
def test_persistence_is_idempotent_and_redacts(db, monkeypatch):
    monkeypatch.setattr(poller, "SUPABASE_LOG_IDENTITY_SALT", "test-salt")
    row = {
        "id": "same-event-id",
        "timestamp": "2026-07-20T12:00:00Z",
        "log_type": "auth_logs",
        "level": "error",
        "status": "401",
        "event_message": "login failed for private@example.com from 203.0.113.9",
        "auth_user": "private-user-id",
        "headers": {"authorization": "Bearer secret-token"},
    }

    first = poller.persist(db, [row], source_cursor="test-window", dry_run=False)
    second = poller.persist(db, [row], source_cursor="test-window", dry_run=False)

    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["duplicates"] == 1
    stored = db.get(SupabaseLogEvent, "same-event-id")
    assert "private@example.com" not in stored.message
    assert "203.0.113.9" not in stored.message
    assert "private-user-id" not in str(stored.event_metadata)
    assert "secret-token" not in str(stored.event_metadata)

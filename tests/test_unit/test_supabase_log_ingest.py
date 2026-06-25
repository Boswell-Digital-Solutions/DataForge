"""
Unit tests for Supabase log redaction + allow-list filtering.

These cover the security boundary: nothing sensitive is persisted, and routine
Postgres maintenance noise is dropped while security/operational signal is kept.
"""
import pytest

from app.utils.supabase_log_ingest import (
    classify_event,
    hash_identity,
    is_noise,
    normalize_event,
    parse_event_time,
    redact_message,
    should_persist,
)

# A real checkpoint row (the shape of the uploaded export) — pure noise.
CHECKPOINT_ROW = {
    "id": "43c26620-f6f4-4942-9121-8ce19764ed90",
    "timestamp": "2026-06-23T17:15:14.137000",
    "date": "2026-06-23T17:15:14.137Z",
    "level": "success",
    "status": "00000",
    "method": "",
    "pathname": "",
    "event_message": "checkpoint complete: wrote 2 buffers (0.0%); 1 recycled; lsn=D/95001CE0",
    "headers": {},
    "regions": [],
    "log_type": "postgres",
    "latency": 0,
    "auth_user": None,
}

# An auth request row with sensitive material in headers / message / auth_user.
AUTH_ROW = {
    "id": "ca8e4ac3-1e9c-4332-a6e0-bc49a266fd34",
    "timestamp": "2026-06-23T17:16:00.000Z",
    "level": "error",
    "status": "401",
    "method": "POST",
    "pathname": "/auth/v1/token",
    "event_message": "authentication failed for user alice@example.com from 203.0.113.7",
    "headers": {
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
        "cookie": "sb-access-token=secret",
        "content-type": "application/json",
    },
    "log_type": "auth",
    "latency": 12.5,
    "auth_user": "user-uuid-1234",
}


@pytest.mark.unit
class TestRedactMessage:
    def test_redacts_email(self):
        assert "alice@example.com" not in redact_message("login for alice@example.com")

    def test_redacts_ipv4(self):
        out = redact_message("request from 203.0.113.7 ok")
        assert "203.0.113.7" not in out and "[redacted-ip]" in out

    def test_redacts_bearer_and_jwt(self):
        out = redact_message(
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def used"
        )
        assert "eyJ" not in out
        assert "[redacted" in out

    def test_redacts_provider_keys(self):
        out = redact_message("key sk-ABCDEFGHIJKLMNOPQRSTUVWX leaked")
        assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" not in out

    def test_empty_is_safe(self):
        assert redact_message(None) == ""


@pytest.mark.unit
class TestHashIdentity:
    def test_deterministic_and_salted(self):
        a = hash_identity("user-1", "salt")
        b = hash_identity("user-1", "salt")
        c = hash_identity("user-1", "different-salt")
        assert a == b
        assert a != c
        assert a != "user-1"

    def test_dropped_without_salt_or_value(self):
        assert hash_identity("user-1", "") is None
        assert hash_identity(None, "salt") is None


@pytest.mark.unit
class TestShouldPersist:
    def test_checkpoint_noise_dropped(self):
        assert should_persist(CHECKPOINT_ROW) is False

    def test_auth_log_kept(self):
        assert should_persist(AUTH_ROW) is True

    def test_http_error_kept(self):
        assert should_persist(
            {"log_type": "edge", "level": "info", "status": "500", "event_message": "boom"}
        ) is True

    def test_postgres_error_kept(self):
        # A Postgres FATAL is signal, not noise, even though log_type is postgres.
        assert should_persist(
            {"log_type": "postgres", "level": "fatal",
             "event_message": "password authentication failed for user \"charlie\""}
        ) is True

    def test_plain_postgres_info_dropped(self):
        assert should_persist(
            {"log_type": "postgres", "level": "log",
             "event_message": "automatic vacuum of table \"public.documents\""}
        ) is False


@pytest.mark.unit
class TestClassify:
    def test_auth(self):
        assert classify_event(AUTH_ROW) == "auth"

    def test_http_error(self):
        assert classify_event(
            {"log_type": "edge", "level": "info", "status": "503", "event_message": "x"}
        ) == "http_error"

    def test_postgres_op(self):
        assert classify_event(CHECKPOINT_ROW) == "postgres_op"


@pytest.mark.unit
class TestNormalizeEvent:
    def test_filtered_row_returns_none(self):
        assert normalize_event(CHECKPOINT_ROW, salt="s") is None

    def test_kept_row_is_fully_redacted(self):
        out = normalize_event(AUTH_ROW, salt="pepper", source_cursor="win-1")
        assert out is not None

        # Identity preserved for dedup.
        assert out["id"] == AUTH_ROW["id"]
        assert out["category"] == "auth"
        assert out["source_cursor"] == "win-1"
        assert out["redacted"] is True

        # Message scrubbed.
        assert "alice@example.com" not in out["message"]
        assert "203.0.113.7" not in out["message"]

        # Sensitive headers dropped; only the benign one survives.
        kept_headers = out["event_metadata"].get("headers", {})
        assert "authorization" not in kept_headers
        assert "cookie" not in kept_headers
        assert kept_headers.get("content-type") == "application/json"

        # auth_user is hashed, never stored raw, and not present anywhere verbatim.
        assert out["event_metadata"]["auth_user_hash"] != "user-uuid-1234"
        assert "user-uuid-1234" not in str(out)

    def test_auth_user_dropped_without_salt(self):
        out = normalize_event(AUTH_ROW, salt="")
        assert "auth_user_hash" not in out["event_metadata"]
        assert "user-uuid-1234" not in str(out)

    def test_synthesizes_id_when_missing(self):
        row = dict(AUTH_ROW)
        row.pop("id")
        out = normalize_event(row, salt="s")
        assert out is not None and len(out["id"]) >= 16


@pytest.mark.unit
class TestParseEventTime:
    def test_iso_with_z(self):
        dt = parse_event_time({"timestamp": "2026-06-23T17:15:14.137Z"})
        assert dt.year == 2026 and dt.tzinfo is not None

    def test_epoch_microseconds(self):
        # Supabase analytics returns microsecond epochs.
        dt = parse_event_time({"timestamp": 1_782_840_914_137_000})
        assert dt.year >= 2026 and dt.tzinfo is not None

    def test_is_noise_matches_checkpoint(self):
        assert is_noise(CHECKPOINT_ROW["event_message"]) is True
        assert is_noise("authentication failed") is False

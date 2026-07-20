#!/usr/bin/env python3
"""
Pull Supabase logs into DataForge as redacted, durable evidence.

Designed to run as a scheduled job (Render cron) — it polls once and exits.
Two sources are supported:

    # Scheduled pull from the Supabase Management API (needs SUPABASE_* env)
    python -m scripts.poll_supabase_logs --once

    # Ingest a local Logs-Explorer JSON export (the dashboard "Download" shape).
    # Works with no Supabase credentials — handy for backfills and verification.
    python scripts/poll_supabase_logs.py --input-file supabase_logs.json

Every row passes through app/utils/supabase_log_ingest (redaction + allow-list)
before it is written. Re-pulling an overlapping window is idempotent: the
Supabase log id is the primary key and existing ids are skipped.

Idempotent · fail-closed on missing API credentials · no external state.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from enum import Enum
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Allow direct invocation (python scripts/poll_supabase_logs.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
    DATABASE_URL_IS_DEFAULT,
    SUPABASE_ACCESS_TOKEN,
    SUPABASE_API_BASE,
    SUPABASE_LOG_IDENTITY_SALT,
    SUPABASE_LOG_POLL_LOOKBACK_SECONDS,
    SUPABASE_LOG_POLL_MAX_ROWS,
    SUPABASE_LOG_POLL_OVERLAP_SECONDS,
    SUPABASE_LOG_SOURCE_TABLE,
    SUPABASE_PROJECT_REF,
)
from app.database import SessionLocal  # noqa: E402
from app.models.supabase_log_models import SupabaseLogEvent  # noqa: E402
from app.utils.supabase_log_ingest import normalize_event  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("poll_supabase_logs")

SUPABASE_LOG_TABLE = "supabase_log_events"
MAX_SUPABASE_LOG_WINDOW_SECONDS = 86_340  # safely below the API's 24-hour cap
MAX_POLL_ROWS = 10_000
_PROJECT_REF_RE = re.compile(r"^[a-z0-9]{8,40}$")
_SUPPORTED_LOG_SOURCES = frozenset(
    {
        "auth_logs",
        "edge_logs",
        "function_edge_logs",
        "function_logs",
        "postgres_logs",
        "postgrest_logs",
        "realtime_logs",
        "storage_logs",
        "supavisor_logs",
    }
)


class FailureCategory(str, Enum):
    """Stable, non-sensitive failure categories for cron diagnostics."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMITING = "rate_limiting"
    UPSTREAM_FAILURE = "upstream_failure"
    NETWORK_FAILURE = "network_failure"
    PAYLOAD_SCHEMA_FAILURE = "payload_schema_failure"
    DATABASE_FAILURE = "database_failure"
    DATABASE_MIGRATION_FAILURE = "database_migration_failure"


class PollerFailure(RuntimeError):
    """A deliberately sanitized operational failure."""

    def __init__(self, category: FailureCategory, code: str):
        self.category = category
        self.code = code
        super().__init__(f"category={category.value} code={code}")


def validate_required_configuration(*, api_mode: bool) -> None:
    """Fail before network or database use when required names are absent/unsafe."""
    if DATABASE_URL_IS_DEFAULT:
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "database_url_missing"
        )
    if not api_mode:
        return
    if not SUPABASE_PROJECT_REF:
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "supabase_project_ref_missing"
        )
    if not SUPABASE_ACCESS_TOKEN:
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "supabase_access_token_missing"
        )
    if not _PROJECT_REF_RE.fullmatch(SUPABASE_PROJECT_REF):
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "supabase_project_ref_invalid"
        )
    if SUPABASE_LOG_SOURCE_TABLE not in _SUPPORTED_LOG_SOURCES:
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "supabase_log_source_not_allowed"
        )
    if not SUPABASE_API_BASE.startswith("https://"):
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "supabase_api_https_required"
        )


def check_database_preflight(session) -> None:
    """Verify connectivity and the migrated table without reading event content."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise PollerFailure(
            FailureCategory.DATABASE_FAILURE, "database_connectivity_failed"
        ) from exc

    try:
        table_exists = inspect(session.get_bind()).has_table(SUPABASE_LOG_TABLE)
    except SQLAlchemyError as exc:
        raise PollerFailure(
            FailureCategory.DATABASE_FAILURE, "database_schema_check_failed"
        ) from exc
    if not table_exists:
        raise PollerFailure(
            FailureCategory.DATABASE_MIGRATION_FAILURE,
            "supabase_log_events_table_missing",
        )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def load_from_file(path: str) -> list[dict]:
    """Load raw log rows from a Supabase Logs-Explorer JSON export."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "input_file_invalid"
        ) from exc
    if isinstance(data, dict):  # tolerate {"result": [...]} or {"data": [...]}
        data = data.get("result") or data.get("data") or []
    if not isinstance(data, list):
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "input_rows_not_array"
        )
    if any(not isinstance(row, dict) for row in data):
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "input_row_not_object"
        )
    logger.info("Loaded %d raw rows from a local export", len(data))
    return data


def fetch_from_api(
    since: datetime,
    limit: int,
    *,
    http_get: Callable | None = None,
) -> list[dict]:
    """Pull rows from the Supabase Management API analytics logs endpoint.

    The current endpoint exposes one ClickHouse ``logs`` stream. The configured
    source is selected from a fixed allow-list and interpolated only after config
    validation. Top-level id/timestamp/event_message are the minimized fields
    relied on for classification.
    """
    import httpx

    validate_required_configuration(api_mode=True)

    if not 1 <= limit <= MAX_POLL_ROWS:
        raise PollerFailure(FailureCategory.CONFIGURATION, "poll_limit_invalid")

    until = datetime.now(tz=timezone.utc)
    normalized_since = since.astimezone(timezone.utc)
    oldest_supported = until - timedelta(seconds=MAX_SUPABASE_LOG_WINDOW_SECONDS)
    if normalized_since < oldest_supported:
        # The analytics endpoint rejects windows over 24 hours. Prefer a
        # bounded recent window over a permanently failing/stuck cron cursor.
        normalized_since = oldest_supported
        logger.warning("Poll cursor exceeded the API window and was safely clamped")
    if normalized_since > until:
        raise PollerFailure(
            FailureCategory.CONFIGURATION, "poll_cursor_in_future"
        )

    # Current Supabase unified logs endpoint uses ClickHouse SQL over one `logs`
    # table. The API timestamp parameters define the cursor window, so the SQL
    # needs only source filtering, ordering, projection, and a bounded limit.
    sql = (
        f"select id, timestamp, event_message, source as log_type "
        f"from logs "
        f"where source = '{SUPABASE_LOG_SOURCE_TABLE}' "
        f"order by timestamp asc limit {int(limit)}"
    )
    url = f"{SUPABASE_API_BASE}/v1/projects/{SUPABASE_PROJECT_REF}/analytics/endpoints/logs"
    logger.info(
        "Checking Supabase log API access (source=%s)",
        SUPABASE_LOG_SOURCE_TABLE,
    )

    try:
        get = http_get or httpx.get
        resp = get(
            url,
            params={
                "sql": sql,
                "iso_timestamp_start": normalized_since.isoformat(),
                "iso_timestamp_end": until.isoformat(),
            },
            headers={"Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"},
            timeout=30.0,
        )
    except (httpx.RequestError, TimeoutError, OSError) as exc:
        raise PollerFailure(
            FailureCategory.NETWORK_FAILURE, "supabase_api_unreachable"
        ) from exc

    status_code = int(resp.status_code)
    if status_code == 401:
        raise PollerFailure(
            FailureCategory.AUTHENTICATION, "supabase_token_rejected"
        )
    if status_code == 403:
        raise PollerFailure(
            FailureCategory.AUTHORIZATION, "supabase_logs_access_forbidden"
        )
    if status_code == 402:
        raise PollerFailure(
            FailureCategory.AUTHORIZATION, "supabase_logs_plan_required"
        )
    if status_code == 404:
        raise PollerFailure(
            FailureCategory.UPSTREAM_FAILURE, "supabase_project_or_endpoint_not_found"
        )
    if status_code == 429:
        raise PollerFailure(
            FailureCategory.RATE_LIMITING, "supabase_logs_rate_limited"
        )
    if status_code >= 500:
        raise PollerFailure(
            FailureCategory.UPSTREAM_FAILURE, "supabase_api_server_error"
        )
    if status_code >= 400:
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "supabase_log_query_rejected"
        )

    try:
        payload = resp.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "supabase_response_not_json"
        ) from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE, "supabase_query_error"
        )
    rows = payload.get("result", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE,
            "supabase_result_array_missing",
        )
    if any(not isinstance(row, dict) for row in rows):
        raise PollerFailure(
            FailureCategory.PAYLOAD_SCHEMA_FAILURE,
            "supabase_result_row_invalid",
        )
    for row in rows:
        row.setdefault("log_type", SUPABASE_LOG_SOURCE_TABLE)
    logger.info("Fetched %d raw rows from Supabase API", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Cursor + persistence
# ---------------------------------------------------------------------------


def get_cursor(session) -> datetime | None:
    """Most recent event_time already stored, for incremental pulls."""
    newest = (
        session.query(SupabaseLogEvent.event_time)
        .order_by(SupabaseLogEvent.event_time.desc())
        .first()
    )
    return newest[0] if newest else None


def persist(session, rows: list[dict], *, source_cursor: str | None, dry_run: bool) -> dict:
    """Redact + filter rows, then insert the ones not already present.

    Dialect-agnostic idempotency: existing ids are looked up and skipped, so a
    re-pulled overlapping window never double-writes (and never errors on PK).
    """
    normalized = [
        n
        for r in rows
        if (n := normalize_event(r, salt=SUPABASE_LOG_IDENTITY_SALT, source_cursor=source_cursor))
    ]
    filtered_out = len(rows) - len(normalized)

    # De-dupe within the batch, then against what is already stored.
    by_id: dict[str, dict] = {n["id"]: n for n in normalized}
    ids = list(by_id)
    existing: set[str] = set()
    for i in range(0, len(ids), 500):
        chunk = ids[i : i + 500]
        existing.update(
            row[0]
            for row in session.query(SupabaseLogEvent.id)
            .filter(SupabaseLogEvent.id.in_(chunk))
            .all()
        )
    new_rows = [n for n in by_id.values() if n["id"] not in existing]

    stats = {
        "raw": len(rows),
        "filtered_out": filtered_out,
        "duplicates": len(normalized) - len(new_rows),
        "inserted": len(new_rows),
    }

    if dry_run:
        logger.info("[dry-run] would insert %d rows (%s)", len(new_rows), stats)
        return stats

    if new_rows:
        session.bulk_insert_mappings(SupabaseLogEvent, new_rows)
        session.commit()
    logger.info("Inserted %d new rows (%s)", len(new_rows), stats)
    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull Supabase logs into DataForge.")
    parser.add_argument("--input-file", help="Ingest a local Logs-Explorer JSON export instead of the API.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit (default; cron-friendly).")
    parser.add_argument("--limit", type=int, default=SUPABASE_LOG_POLL_MAX_ROWS, help="Max rows per pull.")
    parser.add_argument("--lookback-seconds", type=int, default=SUPABASE_LOG_POLL_LOOKBACK_SECONDS,
                        help="On an empty table, how far back to start.")
    parser.add_argument("--dry-run", action="store_true", help="Redact + filter but do not write.")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate configuration, database/table, and API access; do not ingest.",
    )
    args = parser.parse_args(argv)

    if not isinstance(args.limit, int) or not 1 <= args.limit <= MAX_POLL_ROWS:
        logger.error(
            "poller_failed category=%s code=%s",
            FailureCategory.CONFIGURATION.value,
            "poll_limit_invalid",
        )
        return 1
    if (
        not isinstance(args.lookback_seconds, int)
        or not 1 <= args.lookback_seconds <= MAX_SUPABASE_LOG_WINDOW_SECONDS
    ):
        logger.error(
            "poller_failed category=%s code=%s",
            FailureCategory.CONFIGURATION.value,
            "poll_lookback_invalid",
        )
        return 1
    if (
        not isinstance(SUPABASE_LOG_POLL_OVERLAP_SECONDS, int)
        or not 0
        <= SUPABASE_LOG_POLL_OVERLAP_SECONDS
        <= MAX_SUPABASE_LOG_WINDOW_SECONDS
    ):
        logger.error(
            "poller_failed category=%s code=%s",
            FailureCategory.CONFIGURATION.value,
            "poll_overlap_invalid",
        )
        return 1

    session = SessionLocal()
    try:
        validate_required_configuration(api_mode=not bool(args.input_file))
        check_database_preflight(session)

        if args.input_file:
            rows = load_from_file(args.input_file)
            cursor_label = "local-export"
        else:
            cursor = get_cursor(session)
            if cursor:
                since = cursor - timedelta(seconds=SUPABASE_LOG_POLL_OVERLAP_SECONDS)
            else:
                since = datetime.now(tz=timezone.utc) - timedelta(seconds=args.lookback_seconds)
            rows = fetch_from_api(since, 1 if args.preflight_only else args.limit)
            cursor_label = since.strftime("%Y%m%dT%H%M%SZ")

        logger.info(
            "Poller preflight passed (configuration, database, table%s)",
            ", supabase_api" if not args.input_file else "",
        )
        if args.preflight_only:
            return 0

        stats = persist(session, rows, source_cursor=cursor_label, dry_run=args.dry_run)
        logger.info("Done: %s", stats)
        return 0
    except PollerFailure as exc:
        session.rollback()
        logger.error(
            "poller_failed category=%s code=%s",
            exc.category.value,
            exc.code,
        )
        return 1
    except SQLAlchemyError:
        session.rollback()
        logger.error(
            "poller_failed category=%s code=%s",
            FailureCategory.DATABASE_FAILURE.value,
            "database_operation_failed",
        )
        return 1
    except Exception:
        session.rollback()
        logger.error(
            "poller_failed category=%s code=%s",
            FailureCategory.PAYLOAD_SCHEMA_FAILURE.value,
            "unexpected_internal_failure",
        )
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())

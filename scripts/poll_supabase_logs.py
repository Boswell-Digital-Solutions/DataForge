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
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow direct invocation (python scripts/poll_supabase_logs.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
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


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def load_from_file(path: str) -> list[dict]:
    """Load raw log rows from a Supabase Logs-Explorer JSON export."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):  # tolerate {"result": [...]} or {"data": [...]}
        data = data.get("result") or data.get("data") or []
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array of log rows in {path}")
    logger.info("Loaded %d raw rows from %s", len(data), path)
    return data


def fetch_from_api(since: datetime, limit: int) -> list[dict]:
    """Pull rows from the Supabase Management API analytics logs endpoint.

    NOTE: the analytics SQL schema is project/source specific. The source table
    and SQL are overridable (SUPABASE_LOG_SOURCE_TABLE) so this can be tuned
    without code changes; the redaction/allow-list pipeline is identical
    regardless of where the rows come from. Top-level id/timestamp/event_message
    are the fields relied on for classification.
    """
    import httpx

    if not SUPABASE_PROJECT_REF or not SUPABASE_ACCESS_TOKEN:
        raise SystemExit(
            "SUPABASE_PROJECT_REF and SUPABASE_ACCESS_TOKEN are required for API "
            "mode. Set them (cron env) or use --input-file for a local export."
        )

    iso = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = (
        f"select id, timestamp, event_message, metadata "
        f"from {SUPABASE_LOG_SOURCE_TABLE} "
        f"where timestamp > '{iso}' "
        f"order by timestamp asc limit {int(limit)}"
    )
    url = f"{SUPABASE_API_BASE}/v1/projects/{SUPABASE_PROJECT_REF}/analytics/endpoints/logs.all"
    logger.info("Querying Supabase analytics since %s (source=%s)", iso, SUPABASE_LOG_SOURCE_TABLE)

    resp = httpx.get(
        url,
        params={"sql": sql},
        headers={"Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("result", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Unexpected analytics API response shape (no result array)")
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
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        if args.input_file:
            rows = load_from_file(args.input_file)
            cursor_label = f"file:{Path(args.input_file).name}"
        else:
            cursor = get_cursor(session)
            if cursor:
                since = cursor - timedelta(seconds=SUPABASE_LOG_POLL_OVERLAP_SECONDS)
            else:
                since = datetime.now(tz=timezone.utc) - timedelta(seconds=args.lookback_seconds)
            rows = fetch_from_api(since, args.limit)
            cursor_label = since.strftime("%Y%m%dT%H%M%SZ")

        stats = persist(session, rows, source_cursor=cursor_label, dry_run=args.dry_run)
        logger.info("Done: %s", stats)
        return 0
    except Exception:
        session.rollback()
        logger.exception("Supabase log poll failed")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""
Supabase log ingestion — redaction, classification, and allow-list filtering.

This module is the security boundary for pulling Supabase logs into DataForge.
It is intentionally free of any database or network dependency so the rules can
be unit-tested in isolation. The poller (``scripts/poll_supabase_logs.py``) calls
``normalize_event`` for each raw log row; everything that gets persisted has
already passed through here.

Design rules (fail-closed):
  * Sensitive request fields (``headers``, ``auth_user``, nested ``logs``) are
    never stored verbatim. Headers are dropped except a tiny benign allow-list;
    ``auth_user`` is one-way hashed when a salt is configured, otherwise dropped.
  * ``event_message`` is scrubbed for emails, IP addresses, bearer tokens, JWTs
    and provider keys before storage.
  * Only a small allow-list of structural metadata keys is kept; anything not
    explicitly recognised is discarded rather than persisted "just in case".
  * Persistence is opt-in (``should_persist``): security/operational signal is
    kept, routine Postgres maintenance noise (checkpoints, vacuum, WAL) is not.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Allow-list configuration (env-overridable, comma-separated)
# ---------------------------------------------------------------------------


def _env_set(name: str, default: str) -> frozenset[str]:
    return frozenset(
        part.strip().lower()
        for part in os.getenv(name, default).split(",")
        if part.strip()
    )


# Log sources whose entries are inherently security/operational signal.
PERSIST_LOG_TYPES = _env_set(
    "SUPABASE_LOG_PERSIST_LOG_TYPES",
    "auth,auth_logs,postgrest,edge,edge_logs,function_edge_logs,function_logs,"
    "api,storage,realtime",
)

# Severities worth keeping regardless of source.
PERSIST_LEVELS = _env_set(
    "SUPABASE_LOG_PERSIST_LEVELS",
    "error,warning,fatal,panic,critical",
)

# Header keys that may be persisted (lower-cased). Everything else — crucially
# Authorization / Cookie / apikey — is dropped.
SAFE_HEADER_KEYS = _env_set(
    "SUPABASE_LOG_SAFE_HEADER_KEYS",
    "content-type,content-length",
)

# ---------------------------------------------------------------------------
# Redaction patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[A-Fa-f0-9]{0,4}:){2,7}[A-Fa-f0-9]{0,4}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9._\-]{10,}")
_KEY_RE = re.compile(r"\b(?:sb[a-z]?_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{16,})")

# Routine Postgres maintenance chatter — zero security value, high volume.
_NOISE_RE = re.compile(
    r"(?i)\b("
    r"checkpoint (?:starting|complete)|"
    r"restartpoint (?:starting|complete)|"
    r"automatic (?:vacuum|analyze)|"
    r"recycled .* wal|"
    r"\d+ wal file"
    r")\b"
)

# Messages that signal security-relevant activity even from a noisy source.
_SECURITY_RE = re.compile(
    r"(?i)\b("
    r"authentication (?:failed|failure)|password authentication|"
    r"permission denied|role \"|grant |revoke |"
    r"login|logout|sign(?:ed)? in|sign(?:ed)? out|"
    r"invalid (?:token|credentials|jwt)|unauthorized|forbidden"
    r")\b"
)

_NOISE_LEVELS = frozenset({"success", "info", "log", "debug", "notice", "", "00000"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hash_identity(value: Any, salt: str) -> Optional[str]:
    """One-way, salted hash of an identity (e.g. ``auth_user``).

    Returns a short hex digest so events can be correlated to the same subject
    without storing who it was. With no salt configured there is no safe way to
    pseudonymise, so the caller drops the value instead (returns ``None``).
    """
    if value in (None, "") or not salt:
        return None
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return digest[:16]


def redact_message(text: Optional[str]) -> str:
    """Scrub PII and credentials from a free-text log message."""
    if not text:
        return ""
    text = _BEARER_RE.sub("bearer [redacted-token]", text)
    text = _JWT_RE.sub("[redacted-jwt]", text)
    text = _KEY_RE.sub("[redacted-key]", text)
    text = _EMAIL_RE.sub("[redacted-email]", text)
    text = _IPV4_RE.sub("[redacted-ip]", text)
    text = _IPV6_RE.sub("[redacted-ip]", text)
    return text


def _safe_headers(raw_headers: Any) -> dict[str, str]:
    """Keep only benign, allow-listed headers; drop everything else."""
    if not isinstance(raw_headers, dict):
        return {}
    kept: dict[str, str] = {}
    for key, val in raw_headers.items():
        if str(key).lower() in SAFE_HEADER_KEYS and val is not None:
            kept[str(key).lower()] = str(val)
    return kept


def parse_event_time(raw: dict[str, Any]) -> datetime:
    """Best-effort parse of an event timestamp into a tz-aware UTC datetime.

    Handles ISO-8601 strings (with or without ``Z``) and epoch ints/floats in
    seconds or microseconds (the Supabase analytics API returns microseconds).
    Falls back to ``now`` so a malformed timestamp never drops an event.
    """
    for key in ("timestamp", "date", "event_time"):
        val = raw.get(key)
        if val in (None, ""):
            continue
        if isinstance(val, (int, float)):
            # Heuristic: > 1e14 ⇒ microseconds, else seconds.
            seconds = val / 1_000_000 if val > 1e14 else float(val)
            try:
                return datetime.fromtimestamp(seconds, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
        if isinstance(val, str):
            text = val.strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                continue
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def _http_status_is_error(status: Any) -> bool:
    text = str(status or "").strip()
    return len(text) == 3 and text[0] in {"4", "5"} and text.isdigit()


def is_noise(message: Optional[str]) -> bool:
    """True for routine Postgres maintenance lines with no security value."""
    return bool(message) and bool(_NOISE_RE.search(message))


def matches_security_pattern(message: Optional[str]) -> bool:
    return bool(message) and bool(_SECURITY_RE.search(message))


# ---------------------------------------------------------------------------
# Classification + allow-list
# ---------------------------------------------------------------------------


def classify_event(raw: dict[str, Any]) -> str:
    """Coarse category used for indexing and Sentinel queries."""
    log_type = str(raw.get("log_type") or "").lower()
    level = str(raw.get("level") or "").lower()
    message = str(raw.get("event_message") or "")
    status = raw.get("status")

    if matches_security_pattern(message) or log_type in {"auth", "auth_logs"}:
        return "auth"
    if _http_status_is_error(status):
        return "http_error"
    if level in {"error", "fatal", "panic", "critical"}:
        return "error"
    if level == "warning":
        return "warning"
    if log_type == "postgres":
        return "postgres_op"
    return "other"


def should_persist(raw: dict[str, Any]) -> bool:
    """Allow-list: keep security/operational signal, drop maintenance noise."""
    log_type = str(raw.get("log_type") or "").lower()
    level = str(raw.get("level") or "").lower()
    message = str(raw.get("event_message") or "")

    # Drop routine Postgres maintenance chatter (only when low-severity).
    if log_type == "postgres" and level in _NOISE_LEVELS and is_noise(message):
        return False

    if log_type in PERSIST_LOG_TYPES:
        return True
    if level in PERSIST_LEVELS:
        return True
    if _http_status_is_error(raw.get("status")):
        return True
    if matches_security_pattern(message):
        return True
    return False


# ---------------------------------------------------------------------------
# Normalisation (the single entry point used by the poller)
# ---------------------------------------------------------------------------


def _synthesize_id(raw: dict[str, Any], event_time: datetime) -> str:
    basis = f"{event_time.isoformat()}|{raw.get('event_message', '')}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def normalize_event(
    raw: dict[str, Any],
    *,
    salt: str = "",
    source_cursor: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Convert a raw Supabase log row into a persistable, redacted column dict.

    Returns ``None`` when the row is filtered out by the allow-list, so the
    poller can simply skip falsy results.
    """
    if not should_persist(raw):
        return None

    event_time = parse_event_time(raw)
    message = redact_message(raw.get("event_message"))

    metadata: dict[str, Any] = {}
    safe_headers = _safe_headers(raw.get("headers"))
    if safe_headers:
        metadata["headers"] = safe_headers
    if raw.get("regions"):
        metadata["regions"] = raw["regions"]
    if raw.get("log_count") is not None:
        metadata["log_count"] = raw["log_count"]
    nested = raw.get("logs")
    if isinstance(nested, list) and nested:
        metadata["logs_count"] = len(nested)
    auth_hash = hash_identity(raw.get("auth_user"), salt)
    if auth_hash:
        metadata["auth_user_hash"] = auth_hash

    raw_id = raw.get("id")
    event_id = str(raw_id) if raw_id not in (None, "") else _synthesize_id(raw, event_time)

    return {
        "id": event_id,
        "event_time": event_time,
        "log_type": (str(raw["log_type"])[:40] if raw.get("log_type") else None),
        "level": (str(raw["level"])[:20] if raw.get("level") else None),
        "status": (str(raw["status"])[:20] if raw.get("status") not in (None, "") else None),
        "method": (str(raw["method"])[:10] if raw.get("method") else None),
        "pathname": (str(raw["pathname"])[:500] if raw.get("pathname") else None),
        "latency_ms": _coerce_float(raw.get("latency")),
        "category": classify_event(raw),
        "message": message,
        "event_metadata": metadata,
        "source": "supabase",
        "redacted": True,
        "source_cursor": source_cursor,
    }


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

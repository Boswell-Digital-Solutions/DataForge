"""Admin Token Rotation Management for DataForge.

Handles automatic rotation of the ROTATION_ADMIN_TOKEN used by Forge_Command
for cloud sync operations. Tokens rotate every 72 hours by default.

Security Model:
- Current valid token required to rotate
- Previous token remains valid for grace period (1 hour) after rotation
- Rotation events are logged for audit
- Only token HASHES are stored (sha256 + salt); the plaintext is returned once

Storage (IMPORTANT): tokens live in the shared **Postgres** DB, not SQLite. The
previous SQLite store (`tokens.db`) was on Render's ephemeral filesystem, so it was
WIPED on every redeploy — DataForge then fell back to only the static env token and
rejected Forge_Command's rotated token (401), permanently deadlocking the key sync.
Postgres survives redeploys, so rotation stays in sync across deploys. (Mirrors the
earlier secrets-store migration off ephemeral SQLite.)
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)

# Rotation settings
ROTATION_INTERVAL_HOURS = int(os.environ.get("TOKEN_ROTATION_HOURS", "72"))
GRACE_PERIOD_HOURS = int(os.environ.get("TOKEN_GRACE_PERIOD_HOURS", "1"))

# Ephemeral per-process token salt for non-production when TOKEN_SALT is unset.
# Generated once so hashes are stable within a run, never a source constant.
_DEV_FALLBACK_TOKEN_SALT = secrets.token_urlsafe(32)
TOKEN_LENGTH = 48

_tables_ready = False


def _ensure_tables() -> None:
    """Create the admin-token tables in Postgres if absent (idempotent).

    Durable store: survives Render redeploys (unlike the old ephemeral SQLite).
    """
    global _tables_ready
    if _tables_ready:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_tokens (
                id BIGSERIAL PRIMARY KEY,
                token_hash TEXT NOT NULL,
                token_prefix TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                expires_at TIMESTAMPTZ,
                revoked_at TIMESTAMPTZ,
                rotated_from_id BIGINT,
                source TEXT DEFAULT 'manual'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_token_rotation_log (
                id BIGSERIAL PRIMARY KEY,
                old_token_id BIGINT,
                new_token_id BIGINT,
                rotated_at TIMESTAMPTZ NOT NULL,
                rotated_by TEXT,
                reason TEXT
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_admin_tokens_active "
            "ON admin_tokens (created_at DESC) WHERE revoked_at IS NULL"
        ))
    _tables_ready = True


try:
    _ensure_tables()
except Exception as e:  # DB may not be reachable at import; created lazily on first use
    logger.warning(f"Admin-token table init deferred: {e}")


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    import hashlib
    salt = os.environ.get("TOKEN_SALT", "")
    if not salt:
        environment = os.environ.get("ENVIRONMENT", "development")
        if environment == "production":
            raise RuntimeError("TOKEN_SALT must be set in production")
        salt = _DEV_FALLBACK_TOKEN_SALT
    return hashlib.sha256(f"{salt}:{token}".encode()).hexdigest()


def _verify_token_hash(token: str, stored_hash: str) -> bool:
    """Verify a token against its hash."""
    return secrets.compare_digest(_hash_token(token), stored_hash)


def get_current_admin_token() -> Optional[str]:
    """Get the current active admin token PREFIX from the database.

    Only hashes are stored, so this returns the prefix (for status/display). Falls
    back to the environment variable when no DB token exists.
    """
    try:
        _ensure_tables()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT token_prefix
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY created_at DESC
                LIMIT 1
            """), {"now": datetime.now(timezone.utc)}).first()
            if row:
                return row[0]
    except Exception as e:
        logger.debug(f"No DB token, using env: {e}")

    return os.environ.get("ROTATION_ADMIN_TOKEN", "")


def validate_admin_token(token: str) -> bool:
    """Validate an admin token.

    Accepts, in order:
    1. The static env var ``ROTATION_ADMIN_TOKEN`` (bootstrap / backward compat).
    2. Any non-revoked, non-expired token in the admin_tokens DB — i.e. the current
       token (valid for the full rotation interval) AND a just-rotated-out previous
       token still inside its grace window. Validity is governed by ``expires_at``
       (set correctly at rotation), NOT by a created_at recency window.
    """
    if not token:
        return False

    # 1. Env var (bootstrap / backward compatibility).
    env_token = os.environ.get("ROTATION_ADMIN_TOKEN", "")
    if env_token and secrets.compare_digest(token, env_token):
        return True

    # 2. Any active (non-revoked, non-expired) DB token.
    try:
        _ensure_tables()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT token_hash
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY created_at DESC
            """), {"now": datetime.now(timezone.utc)}).all()
            for row in rows:
                if _verify_token_hash(token, row[0]):
                    return True
    except Exception as e:
        logger.debug(f"Token validation DB error: {e}")

    return False


def rotate_admin_token(current_token: str, rotated_by: str = "system") -> tuple[str, dict]:
    """Rotate the admin token.

    Args:
        current_token: Current valid token (for authentication).
        rotated_by: Identifier of who/what initiated rotation.

    Returns:
        Tuple of (new_token, rotation_info).

    Raises:
        ValueError: If current token is invalid.
    """
    if not validate_admin_token(current_token):
        raise ValueError("Invalid current token")

    _ensure_tables()

    new_token = f"forge-{secrets.token_urlsafe(TOKEN_LENGTH)}"
    token_hash = _hash_token(new_token)
    token_prefix = new_token[:16]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ROTATION_INTERVAL_HOURS + GRACE_PERIOD_HOURS)
    grace_expires = now + timedelta(hours=GRACE_PERIOD_HOURS)

    with engine.begin() as conn:
        # Current active token (will become the "previous" token in grace).
        old = conn.execute(text("""
            SELECT id FROM admin_tokens
            WHERE revoked_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)).first()
        old_token_id = old[0] if old else None

        new_token_id = conn.execute(text("""
            INSERT INTO admin_tokens
                (token_hash, token_prefix, created_at, expires_at, rotated_from_id, source)
            VALUES (:h, :p, :created, :expires, :from_id, 'auto_rotation')
            RETURNING id
        """), {
            "h": token_hash, "p": token_prefix, "created": now,
            "expires": expires_at, "from_id": old_token_id,
        }).scalar_one()

        conn.execute(text("""
            INSERT INTO admin_token_rotation_log
                (old_token_id, new_token_id, rotated_at, rotated_by, reason)
            VALUES (:old, :new, :at, :by, 'scheduled_rotation')
        """), {"old": old_token_id, "new": new_token_id, "at": now, "by": rotated_by})

        # Old token keeps working only until the grace window closes.
        if old_token_id:
            conn.execute(text("""
                UPDATE admin_tokens
                SET expires_at = :grace
                WHERE id = :id AND (expires_at IS NULL OR expires_at > :grace)
            """), {"grace": grace_expires, "id": old_token_id})

    logger.info(f"Admin token rotated by {rotated_by}, new prefix: {token_prefix}")

    return new_token, {
        "token_id": new_token_id,
        "token_prefix": token_prefix,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "grace_period_hours": GRACE_PERIOD_HOURS,
        "rotated_from_id": old_token_id,
    }


def get_rotation_status() -> dict:
    """Get current token rotation status."""
    try:
        _ensure_tables()
        now = datetime.now(timezone.utc)
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT id, token_prefix, created_at, expires_at
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY created_at DESC
                LIMIT 1
            """), {"now": now}).mappings().first()

            rotation_count = conn.execute(text("""
                SELECT COUNT(*) FROM admin_token_rotation_log WHERE rotated_at > :cutoff
            """), {"cutoff": now - timedelta(days=30)}).scalar() or 0

            if row:
                created_at = row["created_at"]
                next_rotation = created_at + timedelta(hours=ROTATION_INTERVAL_HOURS)
                return {
                    "current_token_prefix": row["token_prefix"],
                    "created_at": created_at.isoformat() if created_at else None,
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                    "next_rotation_at": next_rotation.isoformat(),
                    "rotation_interval_hours": ROTATION_INTERVAL_HOURS,
                    "grace_period_hours": GRACE_PERIOD_HOURS,
                    "rotations_last_30_days": rotation_count,
                    "using_db_token": True,
                }
    except Exception as e:
        logger.debug(f"Rotation status error: {e}")

    # Fallback status when using env token (no DB token yet).
    return {
        "current_token_prefix": "forge-admin-...",
        "created_at": None,
        "expires_at": None,
        "next_rotation_at": None,
        "rotation_interval_hours": ROTATION_INTERVAL_HOURS,
        "grace_period_hours": GRACE_PERIOD_HOURS,
        "rotations_last_30_days": 0,
        "using_db_token": False,
        "note": "Using environment variable token (not auto-rotating)",
    }


def get_rotation_history(limit: int = 10) -> list[dict]:
    """Get recent rotation history."""
    try:
        _ensure_tables()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    r.id,
                    r.rotated_at,
                    r.rotated_by,
                    r.reason,
                    old.token_prefix AS old_token_prefix,
                    new.token_prefix AS new_token_prefix
                FROM admin_token_rotation_log r
                LEFT JOIN admin_tokens old ON r.old_token_id = old.id
                LEFT JOIN admin_tokens new ON r.new_token_id = new.id
                ORDER BY r.rotated_at DESC
                LIMIT :limit
            """), {"limit": limit}).mappings().all()
            return [
                {
                    "id": row["id"],
                    "rotated_at": row["rotated_at"].isoformat() if row["rotated_at"] else None,
                    "rotated_by": row["rotated_by"],
                    "reason": row["reason"],
                    "old_token_prefix": row["old_token_prefix"],
                    "new_token_prefix": row["new_token_prefix"],
                }
                for row in rows
            ]
    except Exception as e:
        logger.debug(f"Rotation history error: {e}")
        return []

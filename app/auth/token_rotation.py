"""Admin Token Rotation Management for DataForge.

Handles automatic rotation of the ROTATION_ADMIN_TOKEN used by Forge_Command
for cloud sync operations. Tokens rotate every 72 hours by default.

Security Model:
- Current valid token required to rotate
- Previous token remains valid for grace period (1 hour)
- Rotation events are logged for audit
- Tokens stored encrypted in database
"""

import os
import secrets
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Token storage path - default to persistent, secure location (not /tmp)
_default_db_dir = os.path.join(os.environ.get("HOME", "/var/lib/dataforge"), ".dataforge")
TOKEN_DB_PATH = os.environ.get("DATAFORGE_TOKEN_DB", os.path.join(_default_db_dir, "tokens.db"))

# Rotation settings
ROTATION_INTERVAL_HOURS = int(os.environ.get("TOKEN_ROTATION_HOURS", "72"))
GRACE_PERIOD_HOURS = int(os.environ.get("TOKEN_GRACE_PERIOD_HOURS", "1"))
TOKEN_LENGTH = 48


def _ensure_db():
    """Initialize token database."""
    db_path = Path(TOKEN_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(TOKEN_DB_PATH)
    cursor = conn.cursor()

    # Admin tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL,
            token_prefix TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            revoked_at TEXT,
            rotated_from_id INTEGER,
            source TEXT DEFAULT 'manual'
        )
    """)

    # Rotation log for audit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rotation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            old_token_id INTEGER,
            new_token_id INTEGER,
            rotated_at TEXT NOT NULL,
            rotated_by TEXT,
            reason TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Token DB initialized: {TOKEN_DB_PATH}")


try:
    _ensure_db()
except Exception as e:
    logger.warning(f"Token DB init failed: {e}")


@contextmanager
def get_token_db():
    """Get database connection."""
    Path(TOKEN_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TOKEN_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    import hashlib
    salt = os.environ.get("TOKEN_SALT", "")
    if not salt:
        environment = os.environ.get("ENVIRONMENT", "development")
        if environment == "production":
            raise RuntimeError("TOKEN_SALT must be set in production")
        salt = "dataforge-dev-token-salt-NOT-FOR-PRODUCTION"
    return hashlib.sha256(f"{salt}:{token}".encode()).hexdigest()


def _verify_token_hash(token: str, stored_hash: str) -> bool:
    """Verify a token against its hash."""
    return secrets.compare_digest(_hash_token(token), stored_hash)


def get_current_admin_token() -> Optional[str]:
    """Get the current active admin token from database.

    Falls back to environment variable if no DB token exists.
    """
    try:
        with get_token_db() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                SELECT token_hash, token_prefix
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 1
            """, (now,))

            row = cursor.fetchone()
            if row:
                # Return the prefix (we can't return the actual token from hash)
                return row["token_prefix"]
    except Exception as e:
        logger.debug(f"No DB token, using env: {e}")

    # Fall back to environment variable
    return os.environ.get("ROTATION_ADMIN_TOKEN", "")


def validate_admin_token(token: str) -> bool:
    """Validate an admin token.

    Checks:
    1. Current token in database
    2. Previous token within grace period
    3. Environment variable fallback
    """
    if not token:
        return False

    # Check environment variable first (for backward compatibility)
    env_token = os.environ.get("ROTATION_ADMIN_TOKEN", "")
    if secrets.compare_digest(token, env_token):
        return True

    try:
        with get_token_db() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            grace_cutoff = (now - timedelta(hours=GRACE_PERIOD_HOURS)).isoformat()
            now_str = now.isoformat()

            # Check current and recent tokens
            cursor.execute("""
                SELECT token_hash
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > ?)
                AND created_at > ?
                ORDER BY created_at DESC
            """, (now_str, grace_cutoff))

            for row in cursor.fetchall():
                if _verify_token_hash(token, row["token_hash"]):
                    return True
    except Exception as e:
        logger.debug(f"Token validation DB error: {e}")

    return False


def rotate_admin_token(current_token: str, rotated_by: str = "system") -> tuple[str, dict]:
    """Rotate the admin token.

    Args:
        current_token: Current valid token (for authentication)
        rotated_by: Identifier of who/what initiated rotation

    Returns:
        Tuple of (new_token, rotation_info)

    Raises:
        ValueError: If current token is invalid
    """
    if not validate_admin_token(current_token):
        raise ValueError("Invalid current token")

    # Generate new token
    new_token = f"forge-{secrets.token_urlsafe(TOKEN_LENGTH)}"
    token_hash = _hash_token(new_token)
    token_prefix = new_token[:16]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ROTATION_INTERVAL_HOURS + GRACE_PERIOD_HOURS)

    with get_token_db() as conn:
        cursor = conn.cursor()

        # Get current token ID
        old_token_id = None
        cursor.execute("""
            SELECT id FROM admin_tokens
            WHERE revoked_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            old_token_id = row["id"]

        # Insert new token
        cursor.execute("""
            INSERT INTO admin_tokens
            (token_hash, token_prefix, created_at, expires_at, rotated_from_id, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token_hash, token_prefix, now.isoformat(), expires_at.isoformat(),
              old_token_id, "auto_rotation"))

        new_token_id = cursor.lastrowid

        # Log rotation
        cursor.execute("""
            INSERT INTO rotation_log
            (old_token_id, new_token_id, rotated_at, rotated_by, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (old_token_id, new_token_id, now.isoformat(), rotated_by, "scheduled_rotation"))

        # Mark old token as expiring after grace period
        if old_token_id:
            grace_expires = (now + timedelta(hours=GRACE_PERIOD_HOURS)).isoformat()
            cursor.execute("""
                UPDATE admin_tokens
                SET expires_at = ?
                WHERE id = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (grace_expires, old_token_id, grace_expires))

        conn.commit()

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
        with get_token_db() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            # Get current token info
            cursor.execute("""
                SELECT id, token_prefix, created_at, expires_at
                FROM admin_tokens
                WHERE revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 1
            """, (now,))

            row = cursor.fetchone()

            # Get recent rotation count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM rotation_log
                WHERE rotated_at > ?
            """, ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),))
            rotation_count = cursor.fetchone()["count"]

            if row:
                created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                next_rotation = created_at + timedelta(hours=ROTATION_INTERVAL_HOURS)

                return {
                    "current_token_prefix": row["token_prefix"],
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                    "next_rotation_at": next_rotation.isoformat(),
                    "rotation_interval_hours": ROTATION_INTERVAL_HOURS,
                    "grace_period_hours": GRACE_PERIOD_HOURS,
                    "rotations_last_30_days": rotation_count,
                    "using_db_token": True,
                }
    except Exception as e:
        logger.debug(f"Rotation status error: {e}")

    # Fallback status when using env token
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
        with get_token_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    r.id,
                    r.rotated_at,
                    r.rotated_by,
                    r.reason,
                    old.token_prefix as old_token_prefix,
                    new.token_prefix as new_token_prefix
                FROM rotation_log r
                LEFT JOIN admin_tokens old ON r.old_token_id = old.id
                LEFT JOIN admin_tokens new ON r.new_token_id = new.id
                ORDER BY r.rotated_at DESC
                LIMIT ?
            """, (limit,))

            return [
                {
                    "id": row["id"],
                    "rotated_at": row["rotated_at"],
                    "rotated_by": row["rotated_by"],
                    "reason": row["reason"],
                    "old_token_prefix": row["old_token_prefix"],
                    "new_token_prefix": row["new_token_prefix"],
                }
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.debug(f"Rotation history error: {e}")
        return []

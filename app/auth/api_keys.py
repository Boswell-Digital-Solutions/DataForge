"""API Key Authentication for DataForge.

Database-backed API key authentication supporting:
- SHA-256 password hashing for key storage
- Key prefix lookup for fast authentication
- Key expiration and revocation
- Multiple active keys simultaneously
- Emergency bypass via EMERGENCY_OPS_KEY header
- Admin token protection for key management

Per ForgeCommand Key Rotation Master Plan v3.0
"""

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import hashlib
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Database path - default to persistent, secure location (not /tmp)
_default_db_dir = os.path.join(os.environ.get("HOME", "/var/lib/dataforge"), ".dataforge")
API_KEYS_DB_PATH = os.environ.get("DATAFORGE_API_KEYS_DB", os.path.join(_default_db_dir, "api_keys.db"))

# Environment variables for admin/emergency access
# Admin token - required in production, dev default for local development only
ROTATION_ADMIN_TOKEN = os.environ.get("ROTATION_ADMIN_TOKEN", "")
EMERGENCY_OPS_KEY = os.environ.get("EMERGENCY_OPS_KEY", "")

KEY_PREFIX_LENGTH = 10
KEY_LENGTH = 48


class ApiKeyInfo(BaseModel):
    """API key metadata (safe to expose)."""
    id: str
    key_prefix: str
    created_at: str
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    last_used_at: Optional[str] = None
    metadata: dict = {}


def _ensure_db_dir():
    db_path = Path(API_KEYS_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _init_db():
    _ensure_db_dir()
    conn = sqlite3.connect(API_KEYS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            revoked_at TEXT,
            last_used_at TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)
    """)
    conn.commit()
    conn.close()
    logger.info(f"DataForge API keys DB initialized: {API_KEYS_DB_PATH}")


try:
    _init_db()
except Exception as e:
    logger.warning(f"API keys DB init failed: {e}")


@contextmanager
def get_db():
    _ensure_db_dir()
    conn = sqlite3.connect(API_KEYS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def hash_api_key(key: str) -> str:
    salt = os.environ.get("API_KEY_SALT", "")
    if not salt:
        environment = os.environ.get("ENVIRONMENT", "development")
        if environment == "production":
            raise RuntimeError(
                "API_KEY_SALT must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        salt = "dataforge-dev-salt-NOT-FOR-PRODUCTION"
    return hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()


def verify_api_key_hash(key: str, stored_hash: str) -> bool:
    return secrets.compare_digest(hash_api_key(key), stored_hash)


def create_api_key(metadata: Optional[dict] = None, expires_at: Optional[datetime] = None) -> tuple[str, str]:
    key_id = secrets.token_urlsafe(16)
    plaintext_key = secrets.token_urlsafe(KEY_LENGTH)
    key_prefix = plaintext_key[:KEY_PREFIX_LENGTH]
    key_hash = hash_api_key(plaintext_key)
    now = datetime.now(timezone.utc).isoformat()
    expires_str = expires_at.isoformat() if expires_at else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_keys (id, key_prefix, key_hash, created_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key_id, key_prefix, key_hash, now, expires_str, json.dumps(metadata or {})))
        conn.commit()

    logger.info(f"DataForge API key created: {key_id}")
    return plaintext_key, key_id


def validate_api_key(key: str) -> Optional[ApiKeyInfo]:
    if not key or len(key) < KEY_PREFIX_LENGTH:
        return None

    key_prefix = key[:KEY_PREFIX_LENGTH]
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, key_prefix, key_hash, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys
            WHERE key_prefix = ? AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > ?)
        """, (key_prefix, now))

        for row in cursor.fetchall():
            if verify_api_key_hash(key, row["key_hash"]):
                cursor.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row["id"]))
                conn.commit()
                return ApiKeyInfo(
                    id=row["id"],
                    key_prefix=row["key_prefix"],
                    created_at=row["created_at"],
                    expires_at=row["expires_at"],
                    revoked_at=row["revoked_at"],
                    last_used_at=now,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
    return None


def revoke_api_key(key_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (now, key_id))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"DataForge API key revoked: {key_id}")
            return True
    return False


def list_api_keys() -> list[ApiKeyInfo]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, key_prefix, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys ORDER BY created_at DESC
        """)
        return [
            ApiKeyInfo(
                id=row["id"],
                key_prefix=row["key_prefix"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                revoked_at=row["revoked_at"],
                last_used_at=row["last_used_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
            for row in cursor.fetchall()
        ]


def get_api_key_info(key_id: str) -> Optional[ApiKeyInfo]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, key_prefix, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys WHERE id = ?
        """, (key_id,))
        row = cursor.fetchone()
        if row:
            return ApiKeyInfo(
                id=row["id"],
                key_prefix=row["key_prefix"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                revoked_at=row["revoked_at"],
                last_used_at=row["last_used_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
    return None


def is_emergency_key(key: str) -> bool:
    if not EMERGENCY_OPS_KEY:
        return False
    return secrets.compare_digest(key, EMERGENCY_OPS_KEY)


def is_admin_token(token: str) -> bool:
    if not ROTATION_ADMIN_TOKEN:
        return False
    return secrets.compare_digest(token, ROTATION_ADMIN_TOKEN)

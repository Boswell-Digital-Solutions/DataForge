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
from datetime import datetime, timezone
from typing import Optional
import hashlib
import logging

from pydantic import BaseModel
from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)

# API keys are stored in DataForge's durable Postgres (Supabase), NOT a local
# SQLite file: Render's filesystem is ephemeral, so issued keys were wiped on
# every redeploy. Postgres persistence keeps minted keys valid across deploys.

# Environment variables for admin/emergency access
# Admin token - required in production, dev default for local development only
ROTATION_ADMIN_TOKEN = os.environ.get("ROTATION_ADMIN_TOKEN", "")
EMERGENCY_OPS_KEY = os.environ.get("EMERGENCY_OPS_KEY", "")

# Ephemeral per-process salt used only when API_KEY_SALT is unset outside
# production. Generated once so hashes stay stable within a run, but never a
# predictable constant baked into source.
_DEV_FALLBACK_SALT = secrets.token_urlsafe(32)

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


def _init_db():
    with engine.begin() as conn:
        conn.execute(text("""
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
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)"
        ))
    logger.info("DataForge API keys table ready in Postgres (api_keys)")


try:
    _init_db()
except Exception as e:
    logger.warning(f"API keys table init failed: {e}")


def hash_api_key(key: str) -> str:
    salt = os.environ.get("API_KEY_SALT", "")
    if not salt:
        environment = os.environ.get("ENVIRONMENT", "development")
        if environment == "production":
            raise RuntimeError(
                "API_KEY_SALT must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        salt = _DEV_FALLBACK_SALT
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

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO api_keys (id, key_prefix, key_hash, created_at, expires_at, metadata)
            VALUES (:id, :key_prefix, :key_hash, :created_at, :expires_at, :metadata)
        """), {"id": key_id, "key_prefix": key_prefix, "key_hash": key_hash,
               "created_at": now, "expires_at": expires_str,
               "metadata": json.dumps(metadata or {})})

    logger.info(f"DataForge API key created: {key_id}")
    return plaintext_key, key_id


def validate_api_key(key: str) -> Optional[ApiKeyInfo]:
    if not key or len(key) < KEY_PREFIX_LENGTH:
        return None

    key_prefix = key[:KEY_PREFIX_LENGTH]
    now = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, key_prefix, key_hash, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys
            WHERE key_prefix = :key_prefix AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > :now)
        """), {"key_prefix": key_prefix, "now": now}).mappings().fetchall()

        for row in rows:
            if verify_api_key_hash(key, row["key_hash"]):
                conn.execute(
                    text("UPDATE api_keys SET last_used_at = :now WHERE id = :id"),
                    {"now": now, "id": row["id"]},
                )
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
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE api_keys SET revoked_at = :now WHERE id = :id AND revoked_at IS NULL"),
            {"now": now, "id": key_id},
        )
        if (result.rowcount or 0) > 0:
            logger.info(f"DataForge API key revoked: {key_id}")
            return True
    return False


def list_api_keys() -> list[ApiKeyInfo]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, key_prefix, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys ORDER BY created_at DESC
        """)).mappings().fetchall()
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
            for row in rows
        ]


def get_api_key_info(key_id: str) -> Optional[ApiKeyInfo]:
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, key_prefix, created_at, expires_at, revoked_at, last_used_at, metadata
            FROM api_keys WHERE id = :id
        """), {"id": key_id}).mappings().fetchone()
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

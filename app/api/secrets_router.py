"""LLM Provider Secrets Management for Forge Ecosystem.

Stores and serves LLM API keys (OpenAI, Anthropic, Google, XAI) that are
synced from Forge_Command desktop app to cloud services.

Security Model:
- Secrets are encrypted at rest using Fernet symmetric encryption
- Admin token required for write operations (sync from Forge_Command)
- Service API key required for read operations (service consumption)
- Secrets are never logged or exposed in error messages

Per the Forge architecture, Forge_Command is the source of truth for
user-configured API keys. DataForge acts as a secure relay to cloud services.
"""

import os
import logging
import secrets as python_secrets
from datetime import datetime, timezone
from typing import Annotated, Optional
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.auth import (
    validate_api_key,
    is_admin_token,
    is_emergency_key,
    ApiKeyInfo,
    ROTATION_ADMIN_TOKEN,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/secrets", tags=["LLM Secrets"])
bearer_scheme = HTTPBearer(auto_error=False)

# Supported LLM providers
SUPPORTED_PROVIDERS = {"openai", "anthropic", "google", "xai", "ollama"}

# Encryption key from environment (must be set in production)
SECRETS_ENCRYPTION_KEY = os.environ.get("SECRETS_ENCRYPTION_KEY", "")

# In-memory fallback for development (NOT for production)
_dev_secrets_store: dict[str, str] = {}


def _get_fernet():
    """Get Fernet cipher for encryption/decryption."""
    if not SECRETS_ENCRYPTION_KEY:
        return None
    try:
        from cryptography.fernet import Fernet
        # Derive a valid Fernet key from the env key
        import hashlib
        import base64
        key_bytes = hashlib.sha256(SECRETS_ENCRYPTION_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)
    except ImportError:
        logger.warning("cryptography not installed, using dev mode")
        return None


def _encrypt_secret(value: str) -> str:
    """Encrypt a secret value."""
    fernet = _get_fernet()
    if fernet:
        return fernet.encrypt(value.encode()).decode()
    return value  # Dev mode: no encryption


def _decrypt_secret(encrypted: str) -> str:
    """Decrypt a secret value."""
    fernet = _get_fernet()
    if fernet:
        try:
            return fernet.decrypt(encrypted.encode()).decode()
        except Exception:
            return ""
    return encrypted  # Dev mode: no encryption


# Database path for secrets (separate from API keys)
import sqlite3
from pathlib import Path

SECRETS_DB_PATH = os.environ.get("DATAFORGE_SECRETS_DB", "/tmp/dataforge/secrets.db")


def _ensure_db():
    """Initialize secrets database."""
    db_path = Path(SECRETS_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(SECRETS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_secrets (
            provider TEXT PRIMARY KEY,
            encrypted_value TEXT NOT NULL,
            synced_at TEXT NOT NULL,
            synced_from TEXT,
            checksum TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Secrets DB initialized: {SECRETS_DB_PATH}")


try:
    _ensure_db()
except Exception as e:
    logger.warning(f"Secrets DB init failed (will use memory): {e}")


@contextmanager
def get_secrets_db():
    """Get database connection."""
    Path(SECRETS_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SECRETS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class SecretAuthContext:
    """Authentication context for secrets API."""
    def __init__(self, auth_mode: str, key_info: Optional[ApiKeyInfo] = None,
                 is_admin: bool = False):
        self.auth_mode = auth_mode
        self.key_info = key_info
        self.is_admin = is_admin


async def get_secrets_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
    x_emergency_key: Annotated[Optional[str], Header(alias="X-Emergency-Key")] = None,
) -> SecretAuthContext:
    """Authenticate for secrets API."""
    # Emergency key grants full access
    if x_emergency_key and is_emergency_key(x_emergency_key):
        return SecretAuthContext(auth_mode="emergency", is_admin=True)

    # Admin token grants write access
    if x_admin_token and is_admin_token(x_admin_token):
        return SecretAuthContext(auth_mode="admin", is_admin=True)

    # Bearer token grants read access
    if credentials and credentials.scheme.lower() == "bearer":
        key_info = validate_api_key(credentials.credentials)
        if key_info:
            return SecretAuthContext(auth_mode="api_key", key_info=key_info)

    return SecretAuthContext(auth_mode="none")


async def require_secrets_read(
    auth: Annotated[SecretAuthContext, Depends(get_secrets_auth)]
) -> SecretAuthContext:
    """Require read access to secrets."""
    if auth.auth_mode == "none":
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth


async def require_secrets_write(
    auth: Annotated[SecretAuthContext, Depends(get_secrets_auth)]
) -> SecretAuthContext:
    """Require write access to secrets (admin only)."""
    if auth.auth_mode == "none":
        raise HTTPException(status_code=401, detail="Authentication required")
    if not auth.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required for write operations")
    return auth


class SecretSyncRequest(BaseModel):
    """Request to sync secrets from Forge_Command."""
    secrets: dict[str, str] = Field(
        ...,
        description="Map of provider name to API key value"
    )
    source_id: Optional[str] = Field(
        None,
        description="Identifier of the Forge_Command instance"
    )


class SecretSyncResponse(BaseModel):
    """Response from secrets sync."""
    synced: list[str]
    failed: list[str]
    timestamp: str


class SecretResponse(BaseModel):
    """Response with a single secret."""
    provider: str
    available: bool
    synced_at: Optional[str] = None


@router.post("/sync", response_model=SecretSyncResponse)
async def sync_secrets(
    request: SecretSyncRequest,
    auth: Annotated[SecretAuthContext, Depends(require_secrets_write)],
):
    """Sync LLM API keys from Forge_Command.

    This endpoint receives API keys from Forge_Command desktop app
    and stores them encrypted for consumption by cloud services.

    Requires admin authentication (X-Admin-Token header).
    """
    synced = []
    failed = []
    now = datetime.now(timezone.utc).isoformat()

    for provider, value in request.secrets.items():
        provider_lower = provider.lower()

        if provider_lower not in SUPPORTED_PROVIDERS:
            logger.warning(f"Unknown provider in sync request: {provider}")
            failed.append(provider)
            continue

        if not value or not value.strip():
            # Empty value means clear the secret
            try:
                with get_secrets_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM llm_secrets WHERE provider = ?", (provider_lower,))
                    conn.commit()
                synced.append(provider_lower)
                logger.info(f"Cleared secret for provider: {provider_lower}")
            except Exception as e:
                logger.error(f"Failed to clear secret for {provider_lower}: {e}")
                failed.append(provider_lower)
            continue

        try:
            encrypted = _encrypt_secret(value.strip())
            checksum = python_secrets.token_hex(8)

            with get_secrets_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO llm_secrets
                    (provider, encrypted_value, synced_at, synced_from, checksum)
                    VALUES (?, ?, ?, ?, ?)
                """, (provider_lower, encrypted, now, request.source_id, checksum))
                conn.commit()

            synced.append(provider_lower)
            logger.info(f"Synced secret for provider: {provider_lower}")
        except Exception as e:
            logger.error(f"Failed to sync secret for {provider_lower}: {e}")
            failed.append(provider_lower)

    return SecretSyncResponse(synced=synced, failed=failed, timestamp=now)


@router.get("/{provider}", response_model=SecretResponse)
async def get_secret_status(
    provider: str,
    auth: Annotated[SecretAuthContext, Depends(require_secrets_read)],
):
    """Check if a secret is available for a provider.

    Returns availability status without exposing the actual key.
    Use the /secrets/{provider}/value endpoint to get the actual key.
    """
    provider_lower = provider.lower()

    if provider_lower not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        with get_secrets_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT synced_at FROM llm_secrets WHERE provider = ?",
                (provider_lower,)
            )
            row = cursor.fetchone()

            if row:
                return SecretResponse(
                    provider=provider_lower,
                    available=True,
                    synced_at=row["synced_at"]
                )
            return SecretResponse(provider=provider_lower, available=False)
    except Exception as e:
        logger.error(f"Failed to check secret status for {provider_lower}: {e}")
        return SecretResponse(provider=provider_lower, available=False)


@router.get("/{provider}/value")
async def get_secret_value(
    provider: str,
    auth: Annotated[SecretAuthContext, Depends(require_secrets_read)],
):
    """Get the actual API key for a provider.

    This endpoint returns the decrypted API key for use by cloud services.
    Requires service authentication (Bearer token).
    """
    provider_lower = provider.lower()

    if provider_lower not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        with get_secrets_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT encrypted_value FROM llm_secrets WHERE provider = ?",
                (provider_lower,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No secret configured for provider: {provider}"
                )

            decrypted = _decrypt_secret(row["encrypted_value"])
            if not decrypted:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to decrypt secret"
                )

            # Log access (but never log the actual key)
            logger.info(
                f"Secret accessed: provider={provider_lower}, "
                f"auth_mode={auth.auth_mode}"
            )

            return {"provider": provider_lower, "key": decrypted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve secret for {provider_lower}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("")
async def list_secrets(
    auth: Annotated[SecretAuthContext, Depends(require_secrets_read)],
):
    """List all configured secrets (without values).

    Returns the status of all LLM provider secrets.
    """
    result = []

    try:
        with get_secrets_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT provider, synced_at FROM llm_secrets")
            rows = cursor.fetchall()

            configured = {row["provider"]: row["synced_at"] for row in rows}

            for provider in SUPPORTED_PROVIDERS:
                if provider in configured:
                    result.append(SecretResponse(
                        provider=provider,
                        available=True,
                        synced_at=configured[provider]
                    ))
                else:
                    result.append(SecretResponse(
                        provider=provider,
                        available=False
                    ))
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        # Return all as unavailable on error
        for provider in SUPPORTED_PROVIDERS:
            result.append(SecretResponse(provider=provider, available=False))

    return {"secrets": result}


@router.delete("/{provider}")
async def delete_secret(
    provider: str,
    auth: Annotated[SecretAuthContext, Depends(require_secrets_write)],
):
    """Delete a secret for a provider.

    Requires admin authentication.
    """
    provider_lower = provider.lower()

    if provider_lower not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        with get_secrets_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM llm_secrets WHERE provider = ?", (provider_lower,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted secret for provider: {provider_lower}")
                return {"provider": provider_lower, "deleted": True}
            return {"provider": provider_lower, "deleted": False, "message": "Not found"}
    except Exception as e:
        logger.error(f"Failed to delete secret for {provider_lower}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

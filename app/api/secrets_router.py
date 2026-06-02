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
SUPPORTED_PROVIDERS = {"openai", "anthropic", "google", "xai", "deepseek", "ollama"}

# Forge service admin tokens. Forge_Command generates + rotates these and syncs
# them here; each service reads its OWN token (GET /secrets/{name}/value) to
# validate inbound admin calls. Kept distinct from SUPPORTED_PROVIDERS so the
# LLM secrets listing (GET /secrets) is not polluted with service tokens.
SERVICE_TOKENS = {"neuroforge", "forgeagents", "dataforge", "rake"}

# Names accepted for sync/read/delete (LLM provider keys + service admin tokens).
_ALLOWED_NAMES = SUPPORTED_PROVIDERS | SERVICE_TOKENS

# Encryption key from environment - required in production
_env = os.environ.get("ENVIRONMENT", "development")
SECRETS_ENCRYPTION_KEY = os.environ.get("SECRETS_ENCRYPTION_KEY", "")
if not SECRETS_ENCRYPTION_KEY:
    if _env == "production":
        raise RuntimeError(
            "SECRETS_ENCRYPTION_KEY must be set in production. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    # Non-production: derive an ephemeral key so secrets are still encrypted at
    # rest (never stored as plaintext) without shipping a predictable constant.
    import secrets as _py_secrets
    SECRETS_ENCRYPTION_KEY = _py_secrets.token_urlsafe(32)
    logger.warning(
        "SECRETS_ENCRYPTION_KEY not set; using an ephemeral per-process dev key. "
        "Stored secrets will not be decryptable after a restart."
    )

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
    if not fernet:
        # Never persist secrets in plaintext. If encryption is unavailable
        # (e.g. cryptography not installed), refuse rather than degrade.
        raise RuntimeError(
            "Secrets encryption unavailable; refusing to store secret in plaintext. "
            "Install 'cryptography' and set SECRETS_ENCRYPTION_KEY."
        )
    return fernet.encrypt(value.encode()).decode()


def _decrypt_secret(encrypted: str) -> str:
    """Decrypt a secret value."""
    fernet = _get_fernet()
    if fernet:
        try:
            return fernet.decrypt(encrypted.encode()).decode()
        except Exception:
            return ""
    return encrypted  # Dev mode: no encryption


# Secrets are stored in DataForge's durable Postgres (Supabase), NOT a local
# SQLite file: on Render the filesystem is ephemeral, so a SQLite secrets.db was
# wiped on every redeploy. Postgres is the source of truth and survives deploys.
from sqlalchemy import text
from app.database import engine as _pg_engine


def _ensure_db():
    """Create the llm_secrets table in Postgres if it doesn't exist."""
    with _pg_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS llm_secrets (
                provider TEXT PRIMARY KEY,
                encrypted_value TEXT NOT NULL,
                synced_at TEXT NOT NULL,
                synced_from TEXT,
                checksum TEXT
            )
        """))
    logger.info("Secrets table ready in Postgres (llm_secrets)")


try:
    _ensure_db()
except Exception as e:
    logger.warning(f"Secrets table init failed: {e}")


def _upsert_secret(provider: str, encrypted: str, synced_at: str,
                   synced_from: Optional[str], checksum: str) -> None:
    with _pg_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO llm_secrets (provider, encrypted_value, synced_at, synced_from, checksum)
            VALUES (:provider, :encrypted, :synced_at, :synced_from, :checksum)
            ON CONFLICT (provider) DO UPDATE SET
                encrypted_value = EXCLUDED.encrypted_value,
                synced_at = EXCLUDED.synced_at,
                synced_from = EXCLUDED.synced_from,
                checksum = EXCLUDED.checksum
        """), {"provider": provider, "encrypted": encrypted, "synced_at": synced_at,
               "synced_from": synced_from, "checksum": checksum})


def _delete_secret_row(provider: str) -> int:
    with _pg_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM llm_secrets WHERE provider = :provider"),
            {"provider": provider},
        )
        return result.rowcount or 0


def _get_synced_at(provider: str) -> Optional[str]:
    with _pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT synced_at FROM llm_secrets WHERE provider = :provider"),
            {"provider": provider},
        ).fetchone()
        return row[0] if row else None


def _get_encrypted_value(provider: str) -> Optional[str]:
    with _pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT encrypted_value FROM llm_secrets WHERE provider = :provider"),
            {"provider": provider},
        ).fetchone()
        return row[0] if row else None


def _list_synced() -> dict[str, str]:
    with _pg_engine.connect() as conn:
        rows = conn.execute(text("SELECT provider, synced_at FROM llm_secrets")).fetchall()
        return {r[0]: r[1] for r in rows}


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

        if provider_lower not in _ALLOWED_NAMES:
            logger.warning(f"Unknown provider in sync request: {provider}")
            failed.append(provider)
            continue

        if not value or not value.strip():
            # Empty value means clear the secret
            try:
                _delete_secret_row(provider_lower)
                synced.append(provider_lower)
                logger.info(f"Cleared secret for provider: {provider_lower}")
            except Exception as e:
                logger.error(f"Failed to clear secret for {provider_lower}: {e}")
                failed.append(provider_lower)
            continue

        try:
            encrypted = _encrypt_secret(value.strip())
            checksum = python_secrets.token_hex(8)

            _upsert_secret(provider_lower, encrypted, now, request.source_id, checksum)

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

    if provider_lower not in _ALLOWED_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        synced_at = _get_synced_at(provider_lower)
        if synced_at:
            return SecretResponse(provider=provider_lower, available=True, synced_at=synced_at)
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

    if provider_lower not in _ALLOWED_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        encrypted = _get_encrypted_value(provider_lower)
        if not encrypted:
            raise HTTPException(
                status_code=404,
                detail=f"No secret configured for provider: {provider}"
            )

        decrypted = _decrypt_secret(encrypted)
        if not decrypted:
            raise HTTPException(status_code=500, detail="Failed to decrypt secret")

        # Log access (but never log the actual key)
        logger.info(
            f"Secret accessed: provider={provider_lower}, auth_mode={auth.auth_mode}"
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
        configured = _list_synced()
        for provider in SUPPORTED_PROVIDERS:
            if provider in configured:
                result.append(SecretResponse(
                    provider=provider, available=True, synced_at=configured[provider]
                ))
            else:
                result.append(SecretResponse(provider=provider, available=False))
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

    if provider_lower not in _ALLOWED_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        deleted = _delete_secret_row(provider_lower)
        if deleted > 0:
            logger.info(f"Deleted secret for provider: {provider_lower}")
            return {"provider": provider_lower, "deleted": True}
        return {"provider": provider_lower, "deleted": False, "message": "Not found"}
    except Exception as e:
        logger.error(f"Failed to delete secret for {provider_lower}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

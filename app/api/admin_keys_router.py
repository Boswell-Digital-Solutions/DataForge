"""Admin API Key Management Endpoints for DataForge.

Per ForgeCommand Key Rotation Master Plan v3.0
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.auth import (
    create_api_key,
    list_api_keys,
    get_api_key_info,
    revoke_api_key,
    validate_api_key,
    is_emergency_key,
    is_admin_token,
    ApiKeyInfo,
    ROTATION_ADMIN_TOKEN,
    EMERGENCY_OPS_KEY,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api-keys", tags=["Admin - API Keys"])
auth_info_router = APIRouter(tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, auth_mode: str, key_info: Optional[ApiKeyInfo] = None,
                 is_emergency: bool = False, is_admin: bool = False):
        self.auth_mode = auth_mode
        self.key_info = key_info
        self.is_emergency = is_emergency
        self.is_admin = is_admin

    @property
    def key_id(self) -> Optional[str]:
        return self.key_info.id if self.key_info else None

    @property
    def key_prefix(self) -> Optional[str]:
        return self.key_info.key_prefix if self.key_info else None


async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    x_emergency_key: Annotated[Optional[str], Header(alias="X-Emergency-Key")] = None,
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
) -> AuthContext:
    if x_emergency_key and is_emergency_key(x_emergency_key):
        return AuthContext(auth_mode="emergency", is_emergency=True, is_admin=True)
    if x_admin_token and is_admin_token(x_admin_token):
        return AuthContext(auth_mode="admin", is_admin=True)
    if credentials and credentials.scheme.lower() == "bearer":
        key_info = validate_api_key(credentials.credentials)
        if key_info:
            return AuthContext(auth_mode="api_key", key_info=key_info)
    return AuthContext(auth_mode="none")


async def require_api_key(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
    if auth.auth_mode == "none":
        raise HTTPException(status_code=401, detail="API key required")
    return auth


async def require_admin(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
    if auth.auth_mode == "none":
        raise HTTPException(status_code=401, detail="Admin authentication required")
    if not auth.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth


class GenerateKeyRequest(BaseModel):
    expires_in_days: Optional[int] = Field(default=30, ge=1, le=365)
    metadata: Optional[dict] = None


class GenerateKeyResponse(BaseModel):
    key_id: str
    api_key: str
    key_prefix: str
    expires_at: Optional[str] = None
    message: str = "Store this key securely. It will not be shown again."


@router.post("/generate", response_model=GenerateKeyResponse, status_code=201)
async def generate_key(auth: Annotated[AuthContext, Depends(require_admin)],
                       request: GenerateKeyRequest = GenerateKeyRequest()):
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)
    plaintext_key, key_id = create_api_key(metadata=request.metadata, expires_at=expires_at)
    return GenerateKeyResponse(
        key_id=key_id,
        api_key=plaintext_key,
        key_prefix=plaintext_key[:10],
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("")
async def list_keys_endpoint(auth: Annotated[AuthContext, Depends(require_admin)]):
    keys = list_api_keys()
    return {"keys": keys, "total": len(keys)}


@router.post("/{key_id}/revoke")
async def revoke_key_endpoint(key_id: str, auth: Annotated[AuthContext, Depends(require_admin)]):
    if revoke_api_key(key_id):
        return {"key_id": key_id, "revoked": True}
    key_info = get_api_key_info(key_id)
    if key_info and key_info.revoked_at:
        return {"key_id": key_id, "revoked": False, "message": "Already revoked"}
    raise HTTPException(status_code=404, detail=f"API key not found: {key_id}")


@auth_info_router.get("/auth/whoami")
async def whoami(auth: Annotated[AuthContext, Depends(require_api_key)]):
    return {
        "service": "dataforge",
        "auth_mode": auth.auth_mode,
        "authenticated": True,
        "key_id": auth.key_id,
        "key_prefix": auth.key_prefix,
        "is_admin": auth.is_admin,
        "is_emergency": auth.is_emergency,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@auth_info_router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "dataforge",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auth_configured": {
            "rotation_admin_token_configured": bool(ROTATION_ADMIN_TOKEN),
            "emergency_ops_key_configured": bool(EMERGENCY_OPS_KEY),
        },
    }

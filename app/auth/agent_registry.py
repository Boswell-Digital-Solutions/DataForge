"""Scoped service authority for the ForgeAgents-owned global agent registry."""
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.auth import validate_api_key

bearer = HTTPBearer(auto_error=False)


def require_agent_registry(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Agent registry service key required")
    key = validate_api_key(credentials.credentials)
    if key is None:
        raise HTTPException(401, "Invalid agent registry service key")
    metadata = key.metadata or {}
    scope = "agents:read" if request.method == "GET" else "agents:write"
    scopes = metadata.get("scopes")
    if (
        metadata.get("service_name") != "forgeagents"
        or not isinstance(scopes, list)
        or scope not in scopes
    ):
        raise HTTPException(
            403, "ForgeAgents service identity and registry scope required"
        )
    return key.id

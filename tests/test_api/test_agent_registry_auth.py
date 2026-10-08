"""The registry denies anonymous and unrelated service keys before persistence."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from app.auth import agent_registry as auth
from app.api.agents_registry_router import router


def request(method):
    return Request(
        {"type": "http", "method": method, "path": "/api/v1/agents", "headers": []}
    )


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_missing_key_rejected(method):
    with pytest.raises(HTTPException) as error:
        auth.require_agent_registry(request(method), None)
    assert error.value.status_code == 401


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"service_name": "other", "scopes": ["agents:write"]},
        {"service_name": "forgeagents", "scopes": ["agents:read"]},
    ],
)
def test_wrong_service_or_scope_rejected(metadata, monkeypatch):
    monkeypatch.setattr(
        auth,
        "validate_api_key",
        lambda _: SimpleNamespace(metadata=metadata, id="test"),
    )
    with pytest.raises(HTTPException) as error:
        auth.require_agent_registry(
            request("POST"),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="synthetic"),
        )
    assert error.value.status_code == 403


def test_scoped_service_allowed(monkeypatch):
    monkeypatch.setattr(
        auth,
        "validate_api_key",
        lambda _: SimpleNamespace(
            metadata={"service_name": "forgeagents", "scopes": ["agents:write"]},
            id="test",
        ),
    )
    assert (
        auth.require_agent_registry(
            request("POST"),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="synthetic"),
        )
        == "test"
    )


def test_all_registry_routes_enforce_the_dependency():
    for route in router.routes:
        assert any(
            dependency.call is auth.require_agent_registry
            for dependency in route.dependant.dependencies
        )

"""End-to-end proofs for active identity and the retired content boundary."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def e2e_client() -> TestClient:
    """Exercise the application database configured by the test environment."""
    return TestClient(app)


@pytest.mark.e2e
def test_identity_flow_reaches_authenticated_profile(e2e_client: TestClient) -> None:
    suffix = uuid4().hex
    username = f"onboarding-{suffix}"
    email = f"onboarding-{suffix}@example.test"
    password = "SecurePass123!"

    registration = e2e_client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert registration.status_code == 200

    login = e2e_client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200

    profile = e2e_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == username


@pytest.mark.e2e
def test_authorforge_content_workflow_stops_at_retired_boundary(
    e2e_client: TestClient,
) -> None:
    canary = f"PRIVATE-AUTHORFORGE-CONTENT-{uuid4().hex}"
    response = e2e_client.post(
        "/api/projects",
        json={
            "name": "must-not-persist",
            "manuscript": canary,
        },
    )

    assert response.status_code == 410
    assert "authorforge_content_local_only" in response.text
    assert canary not in response.text

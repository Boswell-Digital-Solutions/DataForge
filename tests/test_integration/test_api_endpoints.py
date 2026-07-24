"""Integration tests for active auth and the retired content boundary."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Exercise the application database configured by the test environment."""
    return TestClient(app)


def _identity(prefix: str) -> tuple[str, str]:
    suffix = uuid4().hex
    return f"{prefix}-{suffix}", f"{prefix}-{suffix}@example.test"


@pytest.mark.integration
class TestAuthEndpoints:
    """Prove the migrated Actions database supports active auth flows."""

    def test_user_registration_and_login(self, client: TestClient) -> None:
        username, email = _identity("registration")
        password = "SecurePass123!"

        registration = client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        assert registration.status_code == 200
        assert registration.json()["email"] == email

        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200
        assert "access_token" in login.json()

    def test_login_with_invalid_credentials(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login",
            json={"username": f"missing-{uuid4().hex}", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_token_refresh(self, client: TestClient) -> None:
        username, email = _identity("refresh")
        password = "SecurePass123!"
        registration = client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        assert registration.status_code == 200

        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        refresh = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert refresh.status_code == 200
        assert "access_token" in refresh.json()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/projects"),
        ("POST", "/api/projects"),
        ("PUT", "/api/projects/retired"),
        ("PATCH", "/api/projects/retired/chapters/one"),
        ("DELETE", "/api/projects/retired"),
    ],
)
def test_retired_content_api_fails_closed_without_echo(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    """Never restore the retired AuthorForge cloud-content API."""
    canary = f"PRIVATE-MANUSCRIPT-{uuid4().hex}"
    response = client.request(method, path, json={"content": canary})

    assert response.status_code == 410
    assert "authorforge_content_local_only" in response.text
    assert canary not in response.text

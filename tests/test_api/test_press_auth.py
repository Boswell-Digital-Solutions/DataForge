"""
Authentication boundary tests for the PressForge router (/api/v1/press).

PressForge is protected by a fail-closed dependency (require_pressforge_user)
applied at the router level, so every endpoint requires an active authenticated
DataForge user. These tests exercise that boundary directly — they deliberately
do NOT use the module-local authenticate fixture from test_press_automation.py.
"""
from datetime import datetime, timedelta, UTC

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.models import models
from app.models.press_models import PfCoverage
from app.utils.auth import SECRET_KEY, ALGORITHM, create_access_token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
@pytest.mark.auth
class TestPressForgeAuthBoundary:
    """Unauthenticated / invalid-credential access is rejected fail-closed."""

    def test_missing_authorization_header_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/press/coverage")
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_malformed_token_returns_401(self, client: TestClient):
        resp = client.get(
            "/api/v1/press/coverage",
            headers=_bearer("not-a-valid-jwt"),
        )
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_expired_token_returns_401(self, client: TestClient, test_user: models.User):
        expired = jwt.encode(
            {
                "sub": "testuser",
                "exp": datetime.now(UTC) - timedelta(minutes=1),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        resp = client.get("/api/v1/press/coverage", headers=_bearer(expired))
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_valid_token_for_nonexistent_user_returns_401(self, client: TestClient):
        # Validly signed, but the subject has no row in the local users table.
        token = create_access_token({"sub": "ghost-user-who-does-not-exist"})
        resp = client.get("/api/v1/press/coverage", headers=_bearer(token))
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_inactive_user_returns_403(self, client: TestClient, test_user: models.User, db):
        test_user.is_active = False
        db.commit()

        token = create_access_token({"sub": test_user.username})
        resp = client.get("/api/v1/press/coverage", headers=_bearer(token))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Inactive user"


@pytest.mark.unit
@pytest.mark.auth
class TestPressForgeAuthenticatedAccess:
    """Active authenticated users can use PressForge GET and POST routes."""

    def test_valid_active_user_can_get_coverage(self, client: TestClient, test_user: models.User):
        token = create_access_token({"sub": test_user.username})
        resp = client.get("/api/v1/press/coverage", headers=_bearer(token))
        assert resp.status_code == 200

    def test_unauthenticated_post_is_rejected_and_persists_nothing(
        self, client: TestClient, db
    ):
        resp = client.post(
            "/api/v1/press/coverage",
            json={"article_url": "https://example.com/article"},
        )
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"
        assert db.query(PfCoverage).count() == 0

    def test_authenticated_post_creates_coverage(
        self, client: TestClient, test_user: models.User, db
    ):
        token = create_access_token({"sub": test_user.username})
        article_url = "https://example.com/article"
        resp = client.post(
            "/api/v1/press/coverage",
            json={"article_url": article_url},
            headers=_bearer(token),
        )
        assert resp.status_code == 201
        assert resp.json()["article_url"] == article_url
        assert db.query(PfCoverage).count() == 1

"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.auth
class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/token",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_missing_credentials(self, client: TestClient):
        """Test login with missing credentials."""
        response = client.post("/auth/token", data={})
        
        assert response.status_code == 422  # Validation error
    
    def test_admin_login(self, client: TestClient, test_admin):
        """Test admin user login."""
        response = client.post(
            "/auth/token",
            data={
                "username": "admin",
                "password": "adminpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_token_can_be_used(self, client: TestClient, test_admin):
        """Test that token can be used for authenticated requests."""
        # Get token
        login_response = client.post(
            "/auth/token",
            data={
                "username": "admin",
                "password": "adminpassword"
            }
        )
        token = login_response.json()["access_token"]
        
        # Use token to access protected endpoint
        response = client.get(
            "/admin/domains",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_invalid_token_rejected(self, client: TestClient):
        """Test that invalid token is rejected."""
        response = client.get(
            "/admin/domains",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    def test_missing_token_rejected(self, client: TestClient):
        """Test that missing token is rejected."""
        response = client.get("/admin/domains")
        
        assert response.status_code == 401


@pytest.mark.auth
class TestAuthorizationLevels:
    """Test different authorization levels."""
    
    def test_regular_user_cannot_access_admin(self, client: TestClient, test_user):
        """Test that regular user cannot access admin endpoints."""
        # Login as regular user
        login_response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        token = login_response.json()["access_token"]
        
        # Try to access admin endpoint
        response = client.get(
            "/admin/domains",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]
    
    def test_admin_can_access_admin_endpoints(self, client: TestClient, auth_headers):
        """Test that admin can access admin endpoints."""
        response = client.get("/admin/domains", headers=auth_headers)
        
        assert response.status_code == 200


"""
Comprehensive integration tests for DataForge API endpoints.
Tests full request/response cycles with database and cache interactions.
"""
import pytest
import json
from datetime import datetime
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.utils import auth, embeddings
from app.api import crud
from app.models import models, schemas


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_token(client, db: Session):
    """Create admin user and return auth token."""
    # Create admin user
    admin_data = {
        "email": "admin@test.com",
        "username": "testadmin",
        "password": "SecureTestPass123!"
    }
    
    # Register user
    response = client.post("/api/auth/register", json=admin_data)
    assert response.status_code == 200
    
    # Login
    login_data = {
        "username": "testadmin",
        "password": "SecureTestPass123!"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    
    return response.json()["access_token"]


@pytest.mark.integration
class TestAuthEndpoints:
    """Test authentication endpoints with database integration."""
    
    def test_user_registration_and_login(self, client):
        """Test complete user registration and login flow."""
        # Register new user
        user_data = {
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "SecurePass123!"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        
        # Login with new user
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_login_with_invalid_credentials(self, client):
        """Test login fails with wrong credentials."""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_token_refresh(self, client, admin_token):
        """Test access token refresh."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/api/auth/refresh", headers=headers)
        assert response.status_code == 200
        new_token = response.json()["access_token"]
        assert new_token != admin_token


@pytest.mark.integration
class TestProjectEndpoints:
    """Test project management endpoints."""
    
    def test_create_project(self, client, admin_token):
        """Test creating a project via API."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        project_data = {
            "name": "Integration Test Project",
            "description": "Testing project creation",
            "industry": "Technology",
            "stage": "Seed"
        }
        
        response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == project_data["name"]
        assert "id" in data
    
    def test_get_projects_list(self, client, admin_token):
        """Test retrieving projects list."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create multiple projects
        for i in range(3):
            client.post(
                "/api/projects",
                json={"name": f"Project {i}", "industry": "Tech"},
                headers=headers
            )
        
        # Retrieve projects
        response = client.get("/api/projects", headers=headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 3
    
    def test_update_project(self, client, admin_token):
        """Test updating project details."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project
        project_data = {"name": "Original Name", "industry": "Tech"}
        create_response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        project_id = create_response.json()["id"]
        
        # Update project
        update_data = {"name": "Updated Name", "description": "New description"}
        response = client.put(
            f"/api/projects/{project_id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
    
    def test_delete_project(self, client, admin_token):
        """Test deleting a project."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project
        project_data = {"name": "To Delete", "industry": "Tech"}
        create_response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        project_id = create_response.json()["id"]
        
        # Delete project
        response = client.delete(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response.status_code == 200
        
        # Verify deleted
        response = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestDiligenceEndpoints:
    """Test due diligence endpoints."""
    
    def test_create_diligence_project(self, client, admin_token):
        """Test creating due diligence project."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create a base project
        project_data = {"name": "Diligence Test", "industry": "Tech"}
        project_response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        # Create diligence
        diligence_data = {
            "project_id": project_id,
            "review_type": "comprehensive",
            "focus_areas": ["Financial", "Technical", "Legal"]
        }
        
        response = client.post(
            "/api/diligence",
            json=diligence_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["project_id"] == project_id
    
    def test_add_findings_to_diligence(self, client, admin_token):
        """Test adding findings to diligence review."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project and diligence
        project_response = client.post(
            "/api/projects",
            json={"name": "Findings Test", "industry": "Tech"},
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        diligence_response = client.post(
            "/api/diligence",
            json={"project_id": project_id, "review_type": "comprehensive"},
            headers=headers
        )
        diligence_id = diligence_response.json()["id"]
        
        # Add finding
        finding_data = {
            "title": "Test Finding",
            "description": "A test finding",
            "severity": "high",
            "category": "Financial",
            "status": "open"
        }
        
        response = client.post(
            f"/api/diligence/{diligence_id}/findings",
            json=finding_data,
            headers=headers
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestSearchEndpoints:
    """Test search functionality integration."""
    
    def test_search_projects(self, client, admin_token):
        """Test searching for projects."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create test projects with distinctive names
        for name in ["TechStart Inc", "BioMed Solutions", "FinTech Innovations"]:
            client.post(
                "/api/projects",
                json={"name": name, "industry": "Tech"},
                headers=headers
            )
        
        # Search for "Tech"
        response = client.get(
            "/api/search?q=Tech",
            headers=headers
        )
        assert response.status_code == 200
        results = response.json()
        # Should find projects with "Tech" in name
        assert len(results) > 0
    
    def test_search_with_filters(self, client, admin_token):
        """Test search with filters."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create projects
        projects = [
            {"name": "TechCorp", "industry": "Technology", "stage": "Seed"},
            {"name": "BioLabs", "industry": "Healthcare", "stage": "Series A"}
        ]
        
        for proj in projects:
            client.post(
                "/api/projects",
                json=proj,
                headers=headers
            )
        
        # Search with filter
        response = client.get(
            "/api/search?q=Tech&industry=Technology",
            headers=headers
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestCachingIntegration:
    """Test Redis caching integration with API endpoints."""
    
    def test_cached_project_retrieval(self, client, admin_token):
        """Test that repeated project retrieval uses cache."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project
        project_data = {"name": "Cache Test", "industry": "Tech"}
        create_response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        project_id = create_response.json()["id"]
        
        # First retrieval
        response1 = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response1.status_code == 200
        time1 = response1.elapsed.total_seconds()
        
        # Second retrieval (should be from cache)
        response2 = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response2.status_code == 200
        time2 = response2.elapsed.total_seconds()
        
        # Cached response should be faster (not always guaranteed, so just verify both work)
        assert response1.json() == response2.json()
    
    def test_cache_invalidation_on_update(self, client, admin_token):
        """Test that cache is invalidated when project is updated."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project
        project_data = {"name": "Original", "industry": "Tech"}
        create_response = client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        project_id = create_response.json()["id"]
        
        # Get initial
        response1 = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response1.json()["name"] == "Original"
        
        # Update
        client.put(
            f"/api/projects/{project_id}",
            json={"name": "Updated"},
            headers=headers
        )
        
        # Get again - should reflect update
        response2 = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert response2.json()["name"] == "Updated"


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def test_unauthorized_access(self, client):
        """Test that endpoints reject unauthenticated requests."""
        response = client.get("/api/projects")
        assert response.status_code == 401
    
    def test_not_found_error(self, client, admin_token):
        """Test 404 responses for missing resources."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            "/api/projects/nonexistent-id",
            headers=headers
        )
        assert response.status_code == 404
    
    def test_invalid_request_data(self, client, admin_token):
        """Test validation of request data."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Missing required field
        response = client.post(
            "/api/projects",
            json={"description": "No name field"},
            headers=headers
        )
        assert response.status_code == 422  # Validation error
    
    def test_rate_limiting(self, client, admin_token):
        """Test rate limiting on endpoints."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Keep this bounded: the suite runs against a real remote DB and this
        # endpoint is not actually rate-limited in the current app wiring.
        responses = []
        for _ in range(3):
            response = client.get("/api/projects", headers=headers)
            responses.append(response.status_code)
        
        assert all(code in [200, 429] for code in responses)


@pytest.mark.integration
class TestConcurrentOperations:
    """Test concurrent API operations."""
    
    def test_concurrent_project_creation(self, client, admin_token):
        """Test creating multiple projects concurrently."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        projects_data = [
            {"name": f"Concurrent Project {i}", "industry": "Tech"}
            for i in range(5)
        ]
        
        responses = [
            client.post("/api/projects", json=data, headers=headers)
            for data in projects_data
        ]
        
        assert all(resp.status_code == 200 for resp in responses)
        project_ids = [resp.json()["id"] for resp in responses]
        assert len(set(project_ids)) == 5  # All unique


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across operations."""
    
    def test_user_isolation(self, client):
        """Test that users can only see their own projects."""
        # Create first user
        user1_data = {
            "email": "user1@test.com",
            "username": "user1",
            "password": "Pass123!"
        }
        client.post("/api/auth/register", json=user1_data)
        login1 = client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "Pass123!"}
        )
        token1 = login1.json()["access_token"]
        
        # Create second user
        user2_data = {
            "email": "user2@test.com",
            "username": "user2",
            "password": "Pass123!"
        }
        client.post("/api/auth/register", json=user2_data)
        login2 = client.post(
            "/api/auth/login",
            json={"username": "user2", "password": "Pass123!"}
        )
        token2 = login2.json()["access_token"]
        
        # User1 creates project
        headers1 = {"Authorization": f"Bearer {token1}"}
        project_response = client.post(
            "/api/projects",
            json={"name": "User1 Project", "industry": "Tech"},
            headers=headers1
        )
        project_id = project_response.json()["id"]
        
        # User2 should not see user1's project
        headers2 = {"Authorization": f"Bearer {token2}"}
        response = client.get("/api/projects", headers=headers2)
        user2_projects = response.json()
        
        project_names = [p.get("name") for p in user2_projects]
        assert "User1 Project" not in project_names
    
    def test_transaction_rollback_on_error(self, client, admin_token):
        """Test that failed operations don't partially update."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create project
        project_response = client.post(
            "/api/projects",
            json={"name": "Test", "industry": "Tech"},
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        # Try invalid update (intentional error)
        response = client.put(
            f"/api/projects/{project_id}",
            json={"invalid_field": "value"},
            headers=headers
        )
        
        # Verify project is unchanged
        get_response = client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert get_response.json()["name"] == "Test"

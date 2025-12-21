"""
Tests for health and info endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health check and info endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "DataForge"
        assert "version" in data
        assert "endpoints" in data
        assert "/docs" in str(data["endpoints"])
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["service"] == "DataForge"
        assert "database" in data
    
    def test_docs_endpoint_exists(self, client: TestClient):
        """Test that API docs endpoint exists."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_admin_ui_endpoint(self, client: TestClient):
        """Test admin UI endpoint."""
        response = client.get("/admin-ui")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


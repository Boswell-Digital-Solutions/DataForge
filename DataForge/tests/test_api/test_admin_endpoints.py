"""
Tests for admin API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.admin
class TestDomainEndpoints:
    """Test domain management endpoints."""
    
    def test_create_domain(self, client: TestClient, auth_headers):
        """Test creating a domain."""
        response = client.post(
            "/admin/domains",
            headers=auth_headers,
            json={
                "id": "new_domain",
                "label": "New Domain",
                "description": "A new test domain"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "new_domain"
        assert data["label"] == "New Domain"
    
    def test_create_domain_without_auth(self, client: TestClient):
        """Test that creating domain requires authentication."""
        response = client.post(
            "/admin/domains",
            json={
                "id": "new_domain",
                "label": "New Domain"
            }
        )
        
        assert response.status_code == 401
    
    def test_list_domains(self, client: TestClient, auth_headers, test_domain):
        """Test listing domains."""
        response = client.get("/admin/domains", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(d["id"] == "test_domain" for d in data)
    
    def test_create_domain_with_parent(self, client: TestClient, auth_headers, test_domain):
        """Test creating a domain with parent."""
        response = client.post(
            "/admin/domains",
            headers=auth_headers,
            json={
                "id": "child_domain",
                "label": "Child Domain",
                "parent_id": test_domain.id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == test_domain.id
    
    def test_create_duplicate_domain(self, client: TestClient, auth_headers, test_domain):
        """Test that duplicate domain IDs are rejected."""
        response = client.post(
            "/admin/domains",
            headers=auth_headers,
            json={
                "id": test_domain.id,
                "label": "Duplicate"
            }
        )
        
        assert response.status_code == 400


@pytest.mark.admin
class TestDocumentEndpoints:
    """Test document management endpoints."""
    
    def test_list_documents_empty(self, client: TestClient, auth_headers):
        """Test listing documents when none exist."""
        response = client.get("/admin/documents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_documents_with_filter(self, client: TestClient, auth_headers, test_domain):
        """Test listing documents with domain filter."""
        response = client.get(
            f"/admin/documents?domain_id={test_domain.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_list_documents_without_auth(self, client: TestClient):
        """Test that listing documents requires authentication."""
        response = client.get("/admin/documents")
        
        assert response.status_code == 401


@pytest.mark.admin
class TestTagEndpoints:
    """Test tag management endpoints."""
    
    def test_list_tags(self, client: TestClient, auth_headers, test_tag):
        """Test listing tags."""
        response = client.get("/admin/tags", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(t["name"] == "test-tag" for t in data)
    
    def test_list_tags_without_auth(self, client: TestClient):
        """Test that listing tags requires authentication."""
        response = client.get("/admin/tags")
        
        assert response.status_code == 401


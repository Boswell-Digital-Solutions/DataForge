"""
Tests for search API endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.mark.search
class TestSearchEndpoints:
    """Test search API endpoints."""
    
    @patch('app.api.search.generate_embedding')
    def test_search_endpoint_exists(self, mock_embed, client: TestClient, mock_embedding):
        """Test that search endpoint exists and accepts requests."""
        mock_embed.return_value = mock_embedding
        
        response = client.post(
            "/api/search",
            json={
                "query": "test query",
                "limit": 5
            }
        )
        
        # Should not return 404
        assert response.status_code != 404
    
    @patch('app.api.search.generate_embedding')
    def test_search_with_query(self, mock_embed, client: TestClient, mock_embedding):
        """Test search with basic query."""
        mock_embed.return_value = mock_embedding
        
        response = client.post(
            "/api/search",
            json={
                "query": "character development",
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "total_results" in data
        assert "chunks" in data
        assert data["query"] == "character development"
    
    @patch('app.api.search.generate_embedding')
    def test_search_with_domain_filter(self, mock_embed, client: TestClient, test_domain, mock_embedding):
        """Test search with domain filter."""
        mock_embed.return_value = mock_embedding
        
        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "domain_id": test_domain.id,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.api.search.generate_embedding')
    def test_search_with_tags(self, mock_embed, client: TestClient, mock_embedding):
        """Test search with tag filters."""
        mock_embed.return_value = mock_embedding
        
        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "tags": ["test-tag"],
                "limit": 5
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.api.search.generate_embedding')
    def test_search_with_similarity_threshold(self, mock_embed, client: TestClient, mock_embedding):
        """Test search with custom similarity threshold."""
        mock_embed.return_value = mock_embedding
        
        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "similarity_threshold": 0.8,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
    
    def test_search_missing_query(self, client: TestClient):
        """Test that search requires a query."""
        response = client.post(
            "/api/search",
            json={"limit": 5}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_search_empty_query(self, client: TestClient):
        """Test search with empty query."""
        response = client.post(
            "/api/search",
            json={"query": "", "limit": 5}
        )
        
        assert response.status_code == 422  # Should fail validation
    
    @patch('app.api.search.generate_embedding')
    def test_search_limit_validation(self, mock_embed, client: TestClient, mock_embedding):
        """Test that search limit is validated."""
        mock_embed.return_value = mock_embedding
        
        # Test limit too high
        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 1000}
        )
        
        # Should either reject or cap the limit
        assert response.status_code in [200, 422]
    
    @patch('app.api.search.generate_embedding')
    def test_search_no_auth_required(self, mock_embed, client: TestClient, mock_embedding):
        """Test that search doesn't require authentication."""
        mock_embed.return_value = mock_embedding
        
        # No auth headers
        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 5}
        )
        
        # Should work without auth
        assert response.status_code == 200


@pytest.mark.search
class TestStatsEndpoint:
    """Test statistics endpoint."""
    
    def test_stats_endpoint(self, client: TestClient):
        """Test getting statistics."""
        response = client.get("/api/search/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_domains" in data
        assert "total_documents" in data
        assert "total_chunks" in data
        assert "total_tags" in data
    
    def test_stats_no_auth_required(self, client: TestClient):
        """Test that stats doesn't require authentication."""
        response = client.get("/api/search/stats")
        
        assert response.status_code == 200
    
    def test_stats_returns_correct_counts(self, client: TestClient, test_domain, test_tag):
        """Test that stats returns correct counts."""
        response = client.get("/api/search/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_domains"] >= 1
        assert data["total_tags"] >= 1


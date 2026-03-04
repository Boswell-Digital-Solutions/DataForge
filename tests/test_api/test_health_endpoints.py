"""Tests for health and info endpoints."""

from __future__ import annotations

import httpx
import pytest

from app.main import app


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health check and info endpoints without booting full lifespan."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "DataForge"
        assert "version" in data
        assert "endpoints" in data
        assert "/docs" in str(data["endpoints"])

    @pytest.mark.asyncio
    async def test_health_check(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "DataForge"
        assert "database" not in data

    @pytest.mark.asyncio
    async def test_docs_endpoint_exists(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/docs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_ui_endpoint(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin-ui")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

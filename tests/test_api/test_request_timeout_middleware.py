"""Tests for request-timeout protection middleware."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.middleware.request_timeout import RequestTimeoutMiddleware


def build_app(timeout_seconds: float) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=timeout_seconds)

    @app.get("/slow")
    async def slow() -> dict[str, str]:
        await asyncio.sleep(0.05)
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
async def test_request_timeout_returns_504() -> None:
    transport = httpx.ASGITransport(app=build_app(timeout_seconds=0.01))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/slow")

    assert response.status_code == 504
    assert response.json()["detail"]["error"] == "REQUEST_TIMEOUT"


@pytest.mark.asyncio
async def test_request_timeout_allows_fast_health_check() -> None:
    transport = httpx.ASGITransport(app=build_app(timeout_seconds=0.01))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

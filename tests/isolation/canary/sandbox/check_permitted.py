"""What the runner must permit: the in-process ASGI app, in-memory SQLite, local programs.

These canaries build a tiny FastAPI app of their own. They never import the DataForge `app` package.
"""

import asyncio
import subprocess
import sys

import pytest

pytestmark = pytest.mark.isolation_canary


def make_app():
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_testclient_runs_in_process_without_a_violation():
    from fastapi.testclient import TestClient

    with TestClient(make_app()) as client:
        assert client.get("/ping").json() == {"ok": True}


def test_asgi_transport_runs_in_process_without_a_violation():
    import httpx

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()), base_url="http://asgi.test") as client:
            return (await client.get("/ping")).json()

    assert asyncio.run(go()) == {"ok": True}


def test_in_memory_sqlite_and_the_pgvector_import_work():
    import sqlalchemy as sa
    from pgvector.sqlalchemy import Vector  # noqa: F401

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT 1")).scalar() == 1


def test_listed_programs_run():
    assert "git version" in subprocess.run(["git", "--version"], capture_output=True, text=True).stdout
    assert subprocess.run(["bash", "-c", "exit 0"]).returncode == 0
    assert subprocess.run([sys.executable, "-c", "pass"]).returncode == 0


def test_the_application_package_was_not_imported_by_the_canaries():
    assert "app" not in sys.modules

"""Startup regression tests for DataForge lifespan behavior."""

from __future__ import annotations

import pytest

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_continues_when_pgvector_init_fails(monkeypatch):
    """Transient pgvector startup failures should degrade readiness, not kill boot."""

    security_events: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setenv("DATAFORGE_SKIP_STARTUP_DB_INIT", "false")
    monkeypatch.setattr("app.main.validate_config", lambda: None)
    monkeypatch.setattr("app.main.get_embedding_provider", lambda: (None, None))
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    def fail_connect():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.main.engine.connect", fail_connect)
    monkeypatch.setattr(
        "app.main.log_security_event",
        lambda *args, **kwargs: security_events.append((args, kwargs)),
    )

    async with lifespan(app):
        assert app.state.pgvector_startup_ok is False
        assert app.state.pgvector_startup_error == (
            "Failed to enable pgvector extension after 3 retries"
        )

    assert len(security_events) == 1
    assert security_events[0][0][1] == "EXTENSION_INIT_FAILURE"

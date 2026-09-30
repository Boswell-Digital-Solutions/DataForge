"""Typed BDS persistence rules and service scope enforcement."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import bds_sessions_router as api
from app.models.bds_session_models import BdsSession


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    BdsSession.__table__.create(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def body(**changes):
    record = {
        "session_kind": "execution",
        "session_id": "exec_abc123",
        "final_status": "COMPLETED",
        "completed_at": "2026-09-30T12:00:00Z",
        "session_data": {
            "id": "exec_abc123",
            "status": "COMPLETED",
            "owner_key_id": "smith-key-id",
        },
    }
    record.update(changes)
    return api.FinalizedSessionIn.model_validate(record)


def test_scoped_service_auth(monkeypatch):
    metadata = {"service_name": "forge-agents", "scopes": ["bds:sessions:write"]}
    monkeypatch.setattr(
        api,
        "validate_api_key",
        lambda token: SimpleNamespace(metadata=metadata) if token == "good" else None,
    )
    auth = api.write_scope
    with pytest.raises(HTTPException) as missing:
        auth(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as invalid:
        auth(HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad"))
    assert invalid.value.status_code == 401
    auth(HTTPAuthorizationCredentials(scheme="Bearer", credentials="good"))
    with pytest.raises(HTTPException) as read_denied:
        api.read_scope(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="good")
        )
    assert read_denied.value.status_code == 403
    metadata["service_name"] = "forge-smithy"
    with pytest.raises(HTTPException) as wrong_service:
        auth(HTTPAuthorizationCredentials(scheme="Bearer", credentials="good"))
    assert wrong_service.value.status_code == 403


def test_terminal_idempotency_and_bounded_reads(session):
    response = Response()
    created = api.persist_session(body(), response, session)
    assert response.status_code == 201
    assert created.session_data["owner_key_id"] == "smith-key-id"
    repeat = Response()
    assert api.persist_session(body(), repeat, session).session_id == "exec_abc123"
    assert repeat.status_code == 200
    changed = body(
        session_data={
            "id": "exec_abc123",
            "status": "COMPLETED",
            "owner_key_id": "other",
        }
    )
    with pytest.raises(HTTPException) as conflict:
        api.persist_session(changed, Response(), session)
    assert conflict.value.status_code == 409
    with pytest.raises(HTTPException) as mismatch:
        api.persist_session(
            body(session_data={"id": "wrong", "status": "COMPLETED"}),
            Response(),
            session,
        )
    assert mismatch.value.status_code == 422
    with pytest.raises(ValueError):
        body(final_status="RUNNING")
    assert (
        api.get_session("execution", "exec_abc123", session).session_data[
            "owner_key_id"
        ]
        == "smith-key-id"
    )
    assert len(api.list_sessions("execution", 200, session)) == 1
    with pytest.raises(HTTPException) as missing:
        api.get_session("execution", "missing", session)
    assert missing.value.status_code == 404

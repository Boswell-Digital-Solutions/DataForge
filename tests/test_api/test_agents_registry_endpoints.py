"""Unit-style tests for the async-safe ForgeAgents registry handlers."""

from __future__ import annotations

from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from pgvector.sqlalchemy import Vector

from app.api.agents_registry_router import (
    create_or_update_agent,
    delete_agent,
    get_agent,
    list_agents,
    update_agent,
    update_agent_status,
)
from app.models import models as _models  # noqa: F401 - register SQLAlchemy models
from app.models.agent_registry_schemas import AgentCreate, AgentUpdate
from app.models.models import AgentRegistry


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(TSVECTOR, "sqlite")
def _compile_tsvector_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


def make_agent_payload(agent_id: str, *, name: str, agent_type: str = "researcher") -> dict:
    return {
        "id": agent_id,
        "name": name,
        "agent_type": agent_type,
        "status": "idle",
        "user_id": "user-1",
        "agent_data": {
            "id": agent_id,
            "name": name,
            "agent_type": agent_type,
            "status": "idle",
            "memory_config": {"enabled": True},
            "policy_config": {"mode": "deterministic"},
        },
    }


def make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AgentRegistry.__table__.create(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session_local()


def test_agents_registry_crud_round_trip() -> None:
    db = make_session()
    try:
        create_response = create_or_update_agent(
            AgentCreate.model_validate(make_agent_payload("agent-1", name="Atlas")),
            db=db,
        )
        assert create_response.status_code == 201
        assert create_response.body.decode() == '{"id":"agent-1","created":true,"message":"Agent created successfully"}'

        list_response = list_agents(
            agent_type=None,
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=db,
        )
        assert list_response.status_code == 200
        assert '"total":1' in list_response.body.decode()
        assert '"agent_data":{"id":"agent-1"' in list_response.body.decode()

        get_response = get_agent("agent-1", db=db)
        assert get_response.status_code == 200
        assert '"name":"Atlas"' in get_response.body.decode()

        update_response = update_agent(
            "agent-1",
            AgentUpdate.model_validate({"status": "executing"}),
            db=db,
        )
        assert update_response.status_code == 200
        assert '"status":"executing"' in update_response.body.decode()

        status_response = update_agent_status("agent-1", status="completed", db=db)
        assert status_response.status_code == 200
        assert '"status":"completed"' in status_response.body.decode()

        delete_response = delete_agent("agent-1", db=db)
        assert delete_response.status_code == 204

        try:
            get_agent("agent-1", db=db)
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 404
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected agent lookup to fail after deletion")
    finally:
        db.close()


def test_agents_registry_filtering() -> None:
    db = make_session()
    try:
        create_or_update_agent(
            AgentCreate.model_validate(make_agent_payload("agent-1", name="Atlas", agent_type="researcher")),
            db=db,
        )
        create_or_update_agent(
            AgentCreate.model_validate(make_agent_payload("agent-2", name="Borealis", agent_type="writer")),
            db=db,
        )

        response = list_agents(
            agent_type="writer",
            status=None,
            user_id=None,
            limit=100,
            offset=0,
            db=db,
        )

        assert response.status_code == 200
        body = response.body.decode()
        assert '"total":1' in body
        assert '"id":"agent-2"' in body
        assert '"id":"agent-1"' not in body
    finally:
        db.close()

"""
DataForge - ForgeAgents Registry Router

Handles persistence of agent definitions from ForgeAgents.
DataForge is the source of truth; ForgeAgents loads agents from here on startup.

Design Principles:
- DataForge owns all durable state (ForgeAgents is stateless beyond a run)
- Simple CRUD with idempotent upsert
- Indexed fields for fast queries, JSONB for full agent definition
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent_registry_schemas import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    PersistAgentResponse,
)
from app.models.models import AgentRegistry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Agent Registry"],
)


def _build_agent_query(
    db: Session,
    *,
    agent_type: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
):
    query = db.query(AgentRegistry)
    if agent_type:
        query = query.filter(AgentRegistry.agent_type == agent_type)
    if status:
        query = query.filter(AgentRegistry.status == status)
    if user_id:
        query = query.filter(AgentRegistry.user_id == user_id)
    return query


def _json_response(model, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=model.model_dump(mode="json"))


def _handle_integrity_error(exc: IntegrityError, *, name: str | None) -> None:
    if "unique" in str(exc).lower() and "name" in str(exc).lower():
        raise HTTPException(
            status_code=409,
            detail=f"Agent with name '{name}' already exists",
        ) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "",
    status_code=201,
    response_model=PersistAgentResponse,
    summary="Create or update an agent",
    description="""
    Persist an agent definition to DataForge.

    If an agent with the same ID exists, it will be updated (upsert).
    Name uniqueness is enforced - will return 409 if name conflicts with another agent.
    """,
)
def create_or_update_agent(
    request: AgentCreate,
    db: Session = Depends(get_db),
):
    try:
        existing = db.query(AgentRegistry).filter(AgentRegistry.id == request.id).first()
        if existing:
            existing.name = request.name
            existing.agent_type = request.agent_type
            existing.status = request.status
            existing.user_id = request.user_id
            existing.agent_data = request.agent_data
            db.commit()
            db.refresh(existing)

            logger.info(
                "agent_registry_upsert_complete",
                extra={"agent_id": request.id, "agent_name": request.name, "agent_created": False},
            )
            return _json_response(
                PersistAgentResponse(
                    id=request.id,
                    created=False,
                    message="Agent updated successfully",
                )
            )

        agent = AgentRegistry(
            id=request.id,
            name=request.name,
            agent_type=request.agent_type,
            status=request.status,
            user_id=request.user_id,
            agent_data=request.agent_data,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        logger.info(
            "agent_registry_upsert_complete",
            extra={"agent_id": request.id, "agent_name": request.name, "agent_created": True},
        )
        return _json_response(
            PersistAgentResponse(
                id=request.id,
                created=True,
                message="Agent created successfully",
            ),
            status_code=201,
        )
    except IntegrityError as exc:
        db.rollback()
        _handle_integrity_error(exc, name=request.name)


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
    description="Retrieve all registered agents with optional filtering.",
)
def list_agents(
    agent_type: str | None = Query(default=None, description="Filter by agent type"),
    status: str | None = Query(default=None, description="Filter by status"),
    user_id: str | None = Query(default=None, description="Filter by owner user ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    filters = {
        "agent_type": agent_type,
        "status": status,
        "user_id": user_id,
        "limit": limit,
        "offset": offset,
    }
    logger.info("agents_fetch_start", extra=filters)

    count_start = time.perf_counter()
    logger.info("agents_db_count_start", extra=filters)
    total = (
        _build_agent_query(db, agent_type=agent_type, status=status, user_id=user_id)
        .with_entities(func.count(AgentRegistry.id))
        .scalar()
        or 0
    )
    logger.info(
        "agents_db_count_complete",
        extra={**filters, "total": total, "duration_ms": int((time.perf_counter() - count_start) * 1000)},
    )

    query_start = time.perf_counter()
    logger.info("agents_db_query_start", extra=filters)
    agents = (
        _build_agent_query(db, agent_type=agent_type, status=status, user_id=user_id)
        .order_by(AgentRegistry.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    logger.info(
        "agents_db_query_complete",
        extra={
            **filters,
            "row_count": len(agents),
            "duration_ms": int((time.perf_counter() - query_start) * 1000),
        },
    )

    serialize_start = time.perf_counter()
    response_model = AgentListResponse(
        agents=[AgentResponse.model_validate(agent) for agent in agents],
        total=total,
        limit=limit,
        offset=offset,
    )
    response = _json_response(response_model)
    logger.info(
        "agents_serialize_complete",
        extra={
            **filters,
            "row_count": len(agents),
            "duration_ms": int((time.perf_counter() - serialize_start) * 1000),
        },
    )
    logger.info(
        "agents_fetch_complete",
        extra={
            **filters,
            "total": total,
            "row_count": len(response_model.agents),
            "duration_ms": int((time.perf_counter() - start) * 1000),
        },
    )
    return response


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description="Retrieve a specific agent by its ID.",
)
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
):
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return _json_response(AgentResponse.model_validate(agent))


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Partially update an agent's fields.",
)
def update_agent(
    agent_id: str,
    update: AgentUpdate,
    db: Session = Depends(get_db),
):
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    try:
        if update.name is not None:
            agent.name = update.name
        if update.status is not None:
            agent.status = update.status
        if update.agent_data is not None:
            agent.agent_data = update.agent_data

        db.commit()
        db.refresh(agent)

        logger.info("agent_registry_update_complete", extra={"agent_id": agent_id})
        return _json_response(AgentResponse.model_validate(agent))
    except IntegrityError as exc:
        db.rollback()
        _handle_integrity_error(exc, name=update.name)


@router.delete(
    "/{agent_id}",
    status_code=204,
    summary="Delete agent",
    description="Remove an agent from the registry.",
)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
):
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    db.delete(agent)
    db.commit()

    logger.info("agent_registry_delete_complete", extra={"agent_id": agent_id})
    return Response(status_code=204)


@router.patch(
    "/{agent_id}/status",
    response_model=AgentResponse,
    summary="Update agent status",
    description="Quick endpoint to update just the agent's status.",
)
def update_agent_status(
    agent_id: str,
    status: str = Query(..., description="New status"),
    db: Session = Depends(get_db),
):
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent.status = status
    db.commit()
    db.refresh(agent)

    logger.info("agent_registry_status_complete", extra={"agent_id": agent_id, "status": status})
    return _json_response(AgentResponse.model_validate(agent))

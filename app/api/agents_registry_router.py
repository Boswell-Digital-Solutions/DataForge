"""
DataForge - ForgeAgents Registry Router

Handles persistence of agent definitions from ForgeAgents.
DataForge is the source of truth; ForgeAgents loads agents from here on startup.

Design Principles:
- DataForge owns all durable state (ForgeAgents is stateless beyond a run)
- Simple CRUD with idempotent upsert
- Indexed fields for fast queries, JSONB for full agent definition
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.models import AgentRegistry
from app.models.agent_registry_schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    PersistAgentResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Agent Registry"],
)


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.post(
    "",
    status_code=201,
    response_model=PersistAgentResponse,
    summary="Create or update an agent",
    description="""
    Persist an agent definition to DataForge.

    If an agent with the same ID exists, it will be updated (upsert).
    Name uniqueness is enforced - will return 409 if name conflicts with another agent.
    """
)
async def create_or_update_agent(
    request: AgentCreate,
    db: Session = Depends(get_db)
):
    """Create or update an agent definition."""
    try:
        # Check for existing agent by ID
        existing = db.query(AgentRegistry).filter(
            AgentRegistry.id == request.id
        ).first()

        if existing:
            # Update existing agent
            existing.name = request.name
            existing.agent_type = request.agent_type
            existing.status = request.status
            existing.user_id = request.user_id
            existing.agent_data = request.agent_data
            db.commit()
            db.refresh(existing)

            logger.info(f"Updated agent {request.id} ({request.name})")
            return PersistAgentResponse(
                id=request.id,
                created=False,
                message="Agent updated successfully"
            )
        else:
            # Create new agent
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

            logger.info(f"Created agent {request.id} ({request.name})")
            return PersistAgentResponse(
                id=request.id,
                created=True,
                message="Agent created successfully"
            )

    except IntegrityError as e:
        db.rollback()
        if "unique" in str(e).lower() and "name" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Agent with name '{request.name}' already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
    description="Retrieve all registered agents with optional filtering."
)
async def list_agents(
    agent_type: str | None = Query(default=None, description="Filter by agent type"),
    status: str | None = Query(default=None, description="Filter by status"),
    user_id: str | None = Query(default=None, description="Filter by owner user ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """List all registered agents."""
    query = db.query(AgentRegistry)

    # Apply filters
    if agent_type:
        query = query.filter(AgentRegistry.agent_type == agent_type)
    if status:
        query = query.filter(AgentRegistry.status == status)
    if user_id:
        query = query.filter(AgentRegistry.user_id == user_id)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    agents = query.order_by(AgentRegistry.created_at.desc()).offset(offset).limit(limit).all()

    return AgentListResponse(
        agents=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description="Retrieve a specific agent by its ID."
)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific agent by ID."""
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return AgentResponse.model_validate(agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Partially update an agent's fields."
)
async def update_agent(
    agent_id: str,
    update: AgentUpdate,
    db: Session = Depends(get_db)
):
    """Update an agent's fields."""
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

        logger.info(f"Updated agent {agent_id}")
        return AgentResponse.model_validate(agent)

    except IntegrityError as e:
        db.rollback()
        if "unique" in str(e).lower() and "name" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Agent with name '{update.name}' already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{agent_id}",
    status_code=204,
    summary="Delete agent",
    description="Remove an agent from the registry."
)
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Delete an agent from the registry."""
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    db.delete(agent)
    db.commit()

    logger.info(f"Deleted agent {agent_id}")
    return None


@router.patch(
    "/{agent_id}/status",
    response_model=AgentResponse,
    summary="Update agent status",
    description="Quick endpoint to update just the agent's status."
)
async def update_agent_status(
    agent_id: str,
    status: str = Query(..., description="New status"),
    db: Session = Depends(get_db)
):
    """Update an agent's status."""
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent.status = status
    db.commit()
    db.refresh(agent)

    logger.debug(f"Updated agent {agent_id} status to {status}")
    return AgentResponse.model_validate(agent)

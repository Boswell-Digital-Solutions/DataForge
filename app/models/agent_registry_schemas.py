"""Pydantic schemas for ForgeAgents agent registry API.

These schemas define the request/response models for the /api/v1/agents
endpoints that handle agent persistence from ForgeAgents.
"""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Vocabulary Types
# =============================================================================

AgentTypeType = Literal["researcher", "analyst", "writer", "coder", "orchestrator", "ecosystem"]
AgentStatusType = Literal["idle", "executing", "completed", "failed", "cancelled"]


# =============================================================================
# Request Schemas
# =============================================================================

class AgentCreate(BaseModel):
    """Schema for creating/updating an agent."""

    id: str = Field(..., max_length=36, description="Agent UUID")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name (unique)")
    agent_type: AgentTypeType = Field(..., description="Type of agent")
    status: AgentStatusType = Field(default="idle", description="Current status")
    user_id: str | None = Field(default=None, max_length=36, description="Owner user ID")
    agent_data: dict[str, Any] = Field(..., description="Full agent definition as JSON")


class AgentUpdate(BaseModel):
    """Schema for partial agent update."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: AgentStatusType | None = Field(default=None)
    agent_data: dict[str, Any] | None = Field(default=None)


# =============================================================================
# Response Schemas
# =============================================================================

class AgentResponse(BaseModel):
    """Response schema for a single agent."""

    id: str
    name: str
    agent_type: str
    status: str
    user_id: str | None
    agent_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Response schema for listing agents."""

    agents: list[AgentResponse]
    total: int
    limit: int
    offset: int


class PersistAgentResponse(BaseModel):
    """Response for agent create/update operations."""

    id: str
    created: bool  # True if new, False if updated
    message: str

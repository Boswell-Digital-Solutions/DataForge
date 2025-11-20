"""Pydantic models for VibeForge API - matching Rust types exactly."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# Token Usage Models
# ============================================================================

class TokenUsageModel(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_tokens": 150,
                "completion_tokens": 320,
                "total_tokens": 470,
            }
        }


# ============================================================================
# Context Block Models
# ============================================================================

class ContextBlockModel(BaseModel):
    """A context block for prompt construction."""
    id: str
    title: str
    content: str
    kind: str = Field(..., description="system | design | project | code | workflow")
    priority: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ctx-001",
                "title": "Code Style Guidelines",
                "content": "Always use type hints...",
                "kind": "code",
                "priority": 1,
            }
        }


# ============================================================================
# Run Status Enum
# ============================================================================

class RunStatusEnum(str, Enum):
    """Status of a model run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


# ============================================================================
# Model Run Models
# ============================================================================

class CreateRunRequest(BaseModel):
    """Request to create a new model run."""
    model: str = Field(..., description="claude-3-opus, gpt-4, ollama:mistral, etc.")
    prompt: str
    active_contexts: List[ContextBlockModel] = []
    data_profile_id: Optional[str] = None
    eval_profile_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "model": "claude-3-opus-20240229",
                "prompt": "Analyze this code for performance issues",
                "active_contexts": [
                    {
                        "id": "ctx-001",
                        "title": "Code Review Guidelines",
                        "content": "Focus on...",
                        "kind": "code",
                        "priority": 1,
                    }
                ],
                "data_profile_id": None,
                "eval_profile_id": None,
            }
        }


class ModelRunModel(BaseModel):
    """A complete model run record."""
    id: str
    model: str
    prompt: str
    status: RunStatusEnum
    output: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[TokenUsageModel] = None
    created_at: str  # ISO 8601
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    active_contexts: List[ContextBlockModel] = []
    data_profile_id: Optional[str] = None
    eval_profile_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "run-abc123",
                "model": "claude-3-opus-20240229",
                "prompt": "Analyze this code",
                "status": "complete",
                "output": "The code is efficient...",
                "tokens_used": {
                    "prompt_tokens": 150,
                    "completion_tokens": 320,
                    "total_tokens": 470,
                },
                "created_at": "2025-11-18T10:00:00Z",
                "started_at": "2025-11-18T10:00:05Z",
                "completed_at": "2025-11-18T10:00:15Z",
                "duration_ms": 10000,
                "active_contexts": [],
                "data_profile_id": None,
                "eval_profile_id": None,
            }
        }


class RunHistoryResponse(BaseModel):
    """Response for listing run history."""
    total: int
    limit: int
    offset: int
    items: List[ModelRunModel]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 42,
                "limit": 10,
                "offset": 0,
                "items": [],
            }
        }

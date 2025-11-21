# VibeForge Ecosystem Integration Architecture

**Date**: November 20, 2025  
**Scope**: VibeForge ↔ DataForge ↔ NeuroForge integration  
**Phase**: Phase 1 - Integration Skeleton (MVP)  
**Status**: Design & Implementation Plan

---

## Project Context

VibeForge is the **central UI workbench** for the entire Forge ecosystem:

- **DataForge** (Knowledge Engine) - Context ingestion, semantic search, run logging
- **NeuroForge** (LLM Router) - Prompt execution, multi-model routing, champion/challenger comparison

This document defines the integration contracts and implementation roadmap.

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    VibeForge (Frontend)                         │
│                    SvelteKit Workbench                          │
├──────────────────────┬──────────────────────┬──────────────────┤
│   Left Column:       │   Center Column:     │   Right Column:  │
│   Context Selector   │   Prompt Composer   │   Output Viewer  │
│   (search, attach)   │   (editor, models)  │   (results, diff)│
└──────────────────────┴──────────────────────┴──────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    VibeForge Backend API
                    (FastAPI + Pydantic)
                                  │
        ┌─────────────────────────┼──────────────────────┐
        │                         │                      │
        ▼                         ▼                      ▼
    DataForge API            NeuroForge API       VibeForge Storage
  (Knowledge Engine)         (LLM Router)          (JSON→Postgres)
  • Contexts                 • Models              • Runs
  • Semantic Search          • Prompt Execution   • History
  • Run Logging              • Multi-Model Routing
```

### Data Flow

```
USER ACTION: Compose & Run Prompt

1. Frontend loads contexts from DataForge
   GET /dataforge/workspaces/{ws}/contexts

2. User selects context chunks + models
   UI updates from NeuroForge /models

3. User clicks "Run via NeuroForge"
   Frontend sends to VibeForge Backend:
   POST /v1/vibeforge/run
   {
     workspace_id,
     prompt,
     system,
     context_chunks: [{context_id, chunk_id}],
     models: ["nf:claude-3.5", "nf:gpt-5.1"],
     settings: {temperature, max_tokens}
   }

4. VibeForge Backend:
   a) Fetch context chunks from DataForge
      GET /dataforge/contexts/{ctx}/chunks/{chunk}

   b) Call NeuroForge to execute prompt
      POST /neuroforge/prompt/run
      {
        models,
        prompt,
        contexts: [...full text...]
      }

   c) Log run to DataForge
      POST /dataforge/runs
      {
        workspace_id,
        prompt,
        models,
        outputs,
        context_ids
      }

   d) Store locally in VibeForge
      {runs.json or Postgres}

5. Return aggregated response to frontend
   {
     run_id,
     responses: [
       {model, output, tokens, latency},
       ...
     ]
   }

6. Frontend displays results with tabs per model
```

---

## API Contracts

### DataForge Integration

**Base URL**: `https://dataforge.internal/api/v1` (configurable)

#### 1. List Context Sources

```
GET /workspaces/{workspace_id}/contexts
Response:
{
  "contexts": [
    {
      "id": "ctx_001",
      "name": "API Documentation",
      "source": "github",
      "description": "OpenAI API docs",
      "created_at": "2025-11-20T10:00:00Z",
      "chunk_count": 42
    }
  ]
}
```

#### 2. Semantic Search Contexts

```
POST /workspaces/{workspace_id}/contexts/search
Request:
{
  "query": "authentication token handling",
  "top_k": 10,
  "context_ids": ["ctx_001", "ctx_002"]  # optional filter
}
Response:
{
  "results": [
    {
      "context_id": "ctx_001",
      "chunk_id": "ch_001",
      "score": 0.92,
      "text": "Bearer token format is: Bearer <token>...",
      "source": "api_docs"
    }
  ]
}
```

#### 3. Get Context Chunk

```
GET /contexts/{context_id}/chunks/{chunk_id}
Response:
{
  "id": "ch_001",
  "context_id": "ctx_001",
  "text": "Full chunk text...",
  "metadata": {
    "source": "github_raw",
    "line_range": [100, 150],
    "file": "docs/auth.md"
  }
}
```

#### 4. Log Run

```
POST /runs
Request:
{
  "workspace_id": "vf_ws_01",
  "session_id": "vf_sess_abc",
  "prompt": "User prompt text",
  "system": "System prompt text",
  "models": ["nf:claude-3.5", "nf:gpt-5.1"],
  "contexts": [
    {
      "context_id": "ctx_001",
      "chunk_id": "ch_001",
      "text": "Context text..."
    }
  ],
  "outputs": [
    {
      "model": "nf:claude-3.5",
      "output_id": "nf_out_001",
      "text": "Model output...",
      "tokens": {
        "input": 1200,
        "output": 600,
        "total": 1800
      },
      "latency_ms": 900
    }
  ]
}
Response:
{
  "run_id": "df_run_001",
  "workspace_id": "vf_ws_01",
  "created_at": "2025-11-20T10:05:00Z"
}
```

#### 5. Get Run History

```
GET /workspaces/{workspace_id}/runs?limit=50&model=<optional>&offset=0
Response:
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "runs": [
    {
      "run_id": "df_run_001",
      "created_at": "2025-11-20T10:05:00Z",
      "prompt": "User prompt",
      "models": ["nf:claude-3.5"],
      "context_count": 2,
      "summary": "Generated API usage example"
    }
  ]
}
```

---

### NeuroForge Integration

**Base URL**: `https://neuroforge.internal/api/v1` (configurable)

#### 1. List Available Models

```
GET /models?client=vibeforge
Response:
{
  "models": [
    {
      "id": "nf:claude-3.5-sonnet",
      "name": "Claude 3.5 Sonnet",
      "provider": "anthropic",
      "champion": true,
      "challenger": false,
      "max_tokens": 200000,
      "cost_per_mtok": 3.0
    },
    {
      "id": "nf:gpt-5.1",
      "name": "GPT-5.1",
      "provider": "openai",
      "champion": true,
      "challenger": false,
      "max_tokens": 128000,
      "cost_per_mtok": 15.0
    },
    {
      "id": "nf:claude-3-haiku",
      "name": "Claude 3 Haiku",
      "provider": "anthropic",
      "champion": false,
      "challenger": true,
      "max_tokens": 200000,
      "cost_per_mtok": 0.25
    }
  ],
  "default_model": "nf:claude-3.5-sonnet"
}
```

#### 2. Run Prompt

```
POST /prompt/run
Request:
{
  "workspace_id": "vf_ws_01",
  "session_id": "vf_sess_abc",
  "models": ["nf:claude-3.5-sonnet", "nf:gpt-5.1"],
  "prompt": "User message text",
  "system": "You are a helpful assistant",
  "contexts": [
    {
      "source": "dataforge",
      "context_id": "ctx_001",
      "chunk_id": "ch_001",
      "text": "Context chunk 1 text..."
    },
    {
      "source": "dataforge",
      "context_id": "ctx_001",
      "chunk_id": "ch_002",
      "text": "Context chunk 2 text..."
    }
  ],
  "settings": {
    "temperature": 0.4,
    "max_tokens": 800,
    "top_p": 0.9
  }
}

Response:
{
  "run_id": "nf_run_001",
  "workspace_id": "vf_ws_01",
  "session_id": "vf_sess_abc",
  "responses": [
    {
      "model": "nf:claude-3.5-sonnet",
      "output_id": "nf_out_001",
      "text": "Model response text...",
      "usage": {
        "input_tokens": 1200,
        "output_tokens": 600,
        "total_tokens": 1800
      },
      "latency_ms": 900,
      "finish_reason": "stop"
    },
    {
      "model": "nf:gpt-5.1",
      "output_id": "nf_out_002",
      "text": "Alternative model response...",
      "usage": {
        "input_tokens": 1250,
        "output_tokens": 550,
        "total_tokens": 1800
      },
      "latency_ms": 1200,
      "finish_reason": "stop"
    }
  ],
  "total_tokens": 3600,
  "total_cost": 0.065
}
```

#### 3. Send Feedback (Phase 2)

```
POST /prompt/feedback
Request:
{
  "run_id": "nf_run_001",
  "output_id": "nf_out_001",
  "feedback": {
    "rating": "thumbs_up",
    "tags": ["accurate", "helpful"],
    "notes": "Good explanation",
    "preferred_model": "nf:claude-3.5-sonnet"
  }
}
Response:
{
  "feedback_id": "fb_001",
  "recorded_at": "2025-11-20T10:06:00Z"
}
```

---

## Backend Implementation (VibeForge)

### New Models (`app/models/forge_integration_models.py`)

```python
"""Integration models for DataForge and NeuroForge."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# DataForge Models
# ============================================================================

class ContextSource(BaseModel):
    """Context source from DataForge."""
    id: str
    name: str
    source: str
    description: str
    created_at: datetime
    chunk_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ctx_001",
                "name": "API Documentation",
                "source": "github",
                "description": "OpenAI API docs",
                "created_at": "2025-11-20T10:00:00Z",
                "chunk_count": 42
            }
        }


class ContextChunk(BaseModel):
    """A text chunk from a context."""
    id: str
    context_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ch_001",
                "context_id": "ctx_001",
                "text": "Bearer token format is...",
                "metadata": {"source": "github_raw", "line_range": [100, 150]}
            }
        }


class SearchResult(BaseModel):
    """Result from semantic search."""
    context_id: str
    chunk_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    text: str
    source: str

    class Config:
        json_schema_extra = {
            "example": {
                "context_id": "ctx_001",
                "chunk_id": "ch_001",
                "score": 0.92,
                "text": "Bearer token format...",
                "source": "api_docs"
            }
        }


# ============================================================================
# NeuroForge Models
# ============================================================================

class Model(BaseModel):
    """Available LLM model from NeuroForge."""
    id: str
    name: str
    provider: str
    champion: bool
    challenger: bool
    max_tokens: int
    cost_per_mtok: float

    class Config:
        json_schema_extra = {
            "example": {
                "id": "nf:claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "champion": True,
                "challenger": False,
                "max_tokens": 200000,
                "cost_per_mtok": 3.0
            }
        }


class ModelResponse(BaseModel):
    """Response from a single model."""
    model: str
    output_id: str
    text: str
    usage: Dict[str, int]  # {"input_tokens": X, "output_tokens": Y, "total_tokens": Z}
    latency_ms: int
    finish_reason: str = "stop"

    class Config:
        json_schema_extra = {
            "example": {
                "model": "nf:claude-3.5-sonnet",
                "output_id": "nf_out_001",
                "text": "Model response text...",
                "usage": {"input_tokens": 1200, "output_tokens": 600, "total_tokens": 1800},
                "latency_ms": 900,
                "finish_reason": "stop"
            }
        }


class PromptRunResponse(BaseModel):
    """Response from NeuroForge /prompt/run."""
    run_id: str
    workspace_id: str
    session_id: str
    responses: List[ModelResponse]
    total_tokens: int
    total_cost: float

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "nf_run_001",
                "workspace_id": "vf_ws_01",
                "session_id": "vf_sess_abc",
                "responses": [
                    {
                        "model": "nf:claude-3.5-sonnet",
                        "output_id": "nf_out_001",
                        "text": "Response text...",
                        "usage": {"input_tokens": 1200, "output_tokens": 600, "total_tokens": 1800},
                        "latency_ms": 900,
                        "finish_reason": "stop"
                    }
                ],
                "total_tokens": 3600,
                "total_cost": 0.065
            }
        }


# ============================================================================
# VibeForge Integrated Run Model
# ============================================================================

class IntegratedRunRequest(BaseModel):
    """Request to create an integrated run (DF + NF)."""
    workspace_id: str
    session_id: str
    prompt: str
    system: Optional[str] = None
    models: List[str] = Field(default=["nf:claude-3.5-sonnet"])
    context_ids: List[str] = Field(default=[])  # Will fetch chunks from DF
    settings: Optional[Dict[str, Any]] = Field(
        default={"temperature": 0.4, "max_tokens": 800}
    )

    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "vf_ws_01",
                "session_id": "vf_sess_abc",
                "prompt": "How do I authenticate with the API?",
                "system": "You are a helpful API documentation assistant",
                "models": ["nf:claude-3.5-sonnet", "nf:gpt-5.1"],
                "context_ids": ["ctx_001"],
                "settings": {"temperature": 0.4, "max_tokens": 800}
            }
        }


class IntegratedRunResponse(BaseModel):
    """Aggregated response with context + model outputs."""
    run_id: str
    neuroforge_run_id: str
    workspace_id: str
    session_id: str
    prompt: str
    models: List[str]
    contexts_used: List[Dict[str, Any]]
    responses: List[ModelResponse]
    total_tokens: int
    total_cost: float
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "vf_run_001",
                "neuroforge_run_id": "nf_run_001",
                "workspace_id": "vf_ws_01",
                "session_id": "vf_sess_abc",
                "prompt": "How do I authenticate?",
                "models": ["nf:claude-3.5-sonnet"],
                "contexts_used": [
                    {"context_id": "ctx_001", "chunk_id": "ch_001"}
                ],
                "responses": [
                    {
                        "model": "nf:claude-3.5-sonnet",
                        "output_id": "nf_out_001",
                        "text": "You can authenticate using...",
                        "usage": {"input_tokens": 1200, "output_tokens": 600, "total_tokens": 1800},
                        "latency_ms": 900,
                        "finish_reason": "stop"
                    }
                ],
                "total_tokens": 1800,
                "total_cost": 0.0054,
                "created_at": "2025-11-20T10:05:00Z"
            }
        }
```

---

### New Services (`app/services/forge_integration_service.py`)

```python
"""Integration services for DataForge and NeuroForge."""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
DATAFORGE_BASE_URL = os.getenv("DATAFORGE_API_BASE", "https://dataforge.internal/api/v1")
NEUROFORGE_BASE_URL = os.getenv("NEUROFORGE_API_BASE", "https://neuroforge.internal/api/v1")
DATAFORGE_API_KEY = os.getenv("DATAFORGE_API_KEY", "df-dev-key")
NEUROFORGE_API_KEY = os.getenv("NEUROFORGE_API_KEY", "nf-dev-key")


class DataForgeService:
    """Service for DataForge integration."""

    def __init__(self):
        self.base_url = DATAFORGE_BASE_URL
        self.api_key = DATAFORGE_API_KEY

    async def list_contexts(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List available contexts for a workspace."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/workspaces/{workspace_id}/contexts",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("contexts", [])
        except httpx.HTTPError as e:
            logger.error(f"DataForge list_contexts error: {e}")
            raise

    async def search_contexts(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 10,
        context_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search over contexts."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/workspaces/{workspace_id}/contexts/search",
                    json={
                        "query": query,
                        "top_k": top_k,
                        "context_ids": context_ids or []
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
        except httpx.HTTPError as e:
            logger.error(f"DataForge search_contexts error: {e}")
            raise

    async def get_chunk(self, context_id: str, chunk_id: str) -> Dict[str, Any]:
        """Get full text of a specific context chunk."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/contexts/{context_id}/chunks/{chunk_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"DataForge get_chunk error: {e}")
            raise

    async def log_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log a run to DataForge."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/runs",
                    json=run_data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"DataForge log_run error: {e}")
            raise

    async def get_run_history(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get run history from DataForge."""
        try:
            params = {"limit": limit, "offset": offset}
            if model:
                params["model"] = model

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/workspaces/{workspace_id}/runs",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"DataForge get_run_history error: {e}")
            raise


class NeuroForgeService:
    """Service for NeuroForge integration."""

    def __init__(self):
        self.base_url = NEUROFORGE_BASE_URL
        self.api_key = NEUROFORGE_API_KEY

    async def list_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from NeuroForge."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models?client=vibeforge",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except httpx.HTTPError as e:
            logger.error(f"NeuroForge list_models error: {e}")
            raise

    async def run_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a prompt via NeuroForge."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/prompt/run",
                    json=prompt_data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0  # LLM calls can take a while
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error("NeuroForge run_prompt timeout")
            raise
        except httpx.HTTPError as e:
            logger.error(f"NeuroForge run_prompt error: {e}")
            raise

    async def send_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send feedback to NeuroForge (Phase 2)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/prompt/feedback",
                    json=feedback_data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"NeuroForge send_feedback error: {e}")
            raise


# Singleton instances
_dataforge_service: Optional[DataForgeService] = None
_neuroforge_service: Optional[NeuroForgeService] = None


def get_dataforge_service() -> DataForgeService:
    """Get or create DataForge service instance."""
    global _dataforge_service
    if _dataforge_service is None:
        _dataforge_service = DataForgeService()
    return _dataforge_service


def get_neuroforge_service() -> NeuroForgeService:
    """Get or create NeuroForge service instance."""
    global _neuroforge_service
    if _neuroforge_service is None:
        _neuroforge_service = NeuroForgeService()
    return _neuroforge_service
```

---

### Updated DataForge Router (`app/routers/dataforge.py`)

```python
"""DataForge integration router."""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from app.services.forge_integration_service import get_dataforge_service
from app.models.forge_integration_models import (
    ContextSource,
    SearchResult,
    ContextChunk
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/dataforge", tags=["DataForge Integration"])


@router.get("/workspaces/{workspace_id}/contexts", response_model=List[ContextSource])
async def list_contexts(workspace_id: str):
    """
    List available context sources for a workspace.

    Fetches from DataForge service.
    """
    try:
        service = get_dataforge_service()
        contexts = await service.list_contexts(workspace_id)
        return [ContextSource(**ctx) for ctx in contexts]
    except Exception as e:
        logger.error(f"Error listing contexts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list contexts")


@router.post("/workspaces/{workspace_id}/contexts/search", response_model=List[SearchResult])
async def search_contexts(
    workspace_id: str,
    query: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(10, ge=1, le=50),
    context_ids: Optional[List[str]] = Query(None)
):
    """
    Perform semantic search over contexts.

    Queries DataForge with debounced results.
    """
    try:
        service = get_dataforge_service()
        results = await service.search_contexts(
            workspace_id=workspace_id,
            query=query,
            top_k=top_k,
            context_ids=context_ids
        )
        return [SearchResult(**result) for result in results]
    except Exception as e:
        logger.error(f"Error searching contexts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search contexts")


@router.get("/contexts/{context_id}/chunks/{chunk_id}", response_model=ContextChunk)
async def get_chunk(context_id: str, chunk_id: str):
    """
    Retrieve full text of a specific context chunk.

    Used when user selects a chunk for inclusion in prompt.
    """
    try:
        service = get_dataforge_service()
        chunk = await service.get_chunk(context_id, chunk_id)
        return ContextChunk(**chunk)
    except Exception as e:
        logger.error(f"Error getting chunk: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve context chunk")


@router.get("/workspaces/{workspace_id}/runs")
async def get_run_history(
    workspace_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    model: Optional[str] = Query(None)
):
    """
    Get run history from DataForge.

    Used for history panel in UI.
    """
    try:
        service = get_dataforge_service()
        history = await service.get_run_history(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            model=model
        )
        return history
    except Exception as e:
        logger.error(f"Error getting run history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve run history")
```

---

### Updated NeuroForge Router (`app/routers/neuroforge.py`)

```python
"""NeuroForge integration router."""

from fastapi import APIRouter, HTTPException
from typing import List
import logging

from app.services.forge_integration_service import get_neuroforge_service
from app.models.forge_integration_models import Model, PromptRunResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/neuroforge", tags=["NeuroForge Integration"])


@router.get("/models", response_model=List[Model])
async def list_models():
    """
    Fetch available models and routing info from NeuroForge.

    Used to populate model dropdown in UI.
    """
    try:
        service = get_neuroforge_service()
        models = await service.list_models()
        return [Model(**model) for model in models]
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.post("/prompt/run", response_model=PromptRunResponse)
async def run_prompt(payload: dict):
    """
    Execute a prompt via NeuroForge.

    This endpoint receives the prompt + contexts and:
    1. Calls NeuroForge to execute via specified models
    2. Logs the run to DataForge
    3. Returns aggregated response
    """
    try:
        service = get_neuroforge_service()
        nf_response = await service.run_prompt(payload)
        return PromptRunResponse(**nf_response)
    except Exception as e:
        logger.error(f"Error running prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute prompt")
```

---

## Frontend Implementation (Phase 1 Skeleton)

### API Client - DataForge (`src/lib/api/dataforge.ts`)

```typescript
import type { Context, SearchResult, Run } from "$lib/types/dataforge";

const API_BASE =
  import.meta.env.VITE_DATAFORGE_API_BASE ||
  "http://localhost:8000/v1/dataforge";
const API_KEY = import.meta.env.VITE_DATAFORGE_API_KEY || "";

const headers = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${API_KEY}`,
};

export async function listContexts(workspaceId: string): Promise<Context[]> {
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/contexts`, {
    method: "GET",
    headers,
  });

  if (!res.ok) {
    throw new Error(`Failed to list contexts: ${res.statusText}`);
  }

  return res.json();
}

export async function searchContexts(
  workspaceId: string,
  query: string,
  topK: number = 10,
  contextIds?: string[]
): Promise<SearchResult[]> {
  const res = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/contexts/search?query=${encodeURIComponent(
      query
    )}&top_k=${topK}`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        context_ids: contextIds || [],
      }),
    }
  );

  if (!res.ok) {
    throw new Error(`Failed to search contexts: ${res.statusText}`);
  }

  return res.json();
}

export async function getChunk(
  contextId: string,
  chunkId: string
): Promise<string> {
  const res = await fetch(
    `${API_BASE}/contexts/${contextId}/chunks/${chunkId}`,
    {
      method: "GET",
      headers,
    }
  );

  if (!res.ok) {
    throw new Error(`Failed to get context chunk: ${res.statusText}`);
  }

  const data = await res.json();
  return data.text;
}

export async function getRunHistory(
  workspaceId: string,
  limit: number = 50,
  offset: number = 0,
  model?: string
): Promise<{ total: number; runs: Run[] }> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (model) {
    params.append("model", model);
  }

  const res = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/runs?${params}`,
    {
      method: "GET",
      headers,
    }
  );

  if (!res.ok) {
    throw new Error(`Failed to get run history: ${res.statusText}`);
  }

  return res.json();
}
```

### API Client - NeuroForge (`src/lib/api/neuroforge.ts`)

```typescript
import type { Model, PromptRunResponse } from "$lib/types/neuroforge";

const API_BASE =
  import.meta.env.VITE_NEUROFORGE_API_BASE ||
  "http://localhost:8000/v1/neuroforge";
const API_KEY = import.meta.env.VITE_NEUROFORGE_API_KEY || "";

const headers = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${API_KEY}`,
};

export async function listModels(): Promise<Model[]> {
  const res = await fetch(`${API_BASE}/models`, {
    method: "GET",
    headers,
  });

  if (!res.ok) {
    throw new Error(`Failed to list models: ${res.statusText}`);
  }

  return res.json();
}

export async function runPrompt(payload: {
  workspace_id: string;
  session_id: string;
  prompt: string;
  system?: string;
  models: string[];
  contexts: Array<{
    source: string;
    context_id: string;
    chunk_id: string;
    text: string;
  }>;
  settings?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
  };
}): Promise<PromptRunResponse> {
  const res = await fetch(`${API_BASE}/prompt/run`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to run prompt: ${res.statusText}`);
  }

  return res.json();
}

export async function sendFeedback(feedback: {
  run_id: string;
  output_id: string;
  rating: "thumbs_up" | "thumbs_down";
  tags?: string[];
  notes?: string;
  preferred_model?: string;
}) {
  const res = await fetch(`${API_BASE}/prompt/feedback`, {
    method: "POST",
    headers,
    body: JSON.stringify(feedback),
  });

  if (!res.ok) {
    throw new Error(`Failed to send feedback: ${res.statusText}`);
  }

  return res.json();
}
```

### Types (`src/lib/types/index.ts`)

```typescript
// DataForge Types
export interface Context {
  id: string;
  name: string;
  source: string;
  description: string;
  created_at: string;
  chunk_count: number;
}

export interface SearchResult {
  context_id: string;
  chunk_id: string;
  score: number;
  text: string;
  source: string;
}

export interface Run {
  run_id: string;
  created_at: string;
  prompt: string;
  models: string[];
  context_count: number;
  summary: string;
}

// NeuroForge Types
export interface Model {
  id: string;
  name: string;
  provider: string;
  champion: boolean;
  challenger: boolean;
  max_tokens: number;
  cost_per_mtok: number;
}

export interface ModelResponse {
  model: string;
  output_id: string;
  text: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  latency_ms: number;
  finish_reason: string;
}

export interface PromptRunResponse {
  run_id: string;
  neuroforge_run_id: string;
  workspace_id: string;
  session_id: string;
  prompt: string;
  models: string[];
  contexts_used: Array<{ context_id: string; chunk_id: string }>;
  responses: ModelResponse[];
  total_tokens: number;
  total_cost: number;
  created_at: string;
}

// Workbench State
export interface WorkbenchState {
  workspaceId: string;
  sessionId: string;

  // Left Column: Contexts
  availableContexts: Context[];
  selectedContextIds: string[];
  selectedChunks: Array<{ context_id: string; chunk_id: string; text: string }>;
  searchQuery: string;
  searchResults: SearchResult[];
  isSearching: boolean;

  // Center Column: Prompt
  systemPrompt: string;
  userPrompt: string;
  selectedModels: string[];
  isRunning: boolean;
  temperature: number;
  maxTokens: number;

  // Right Column: Results
  lastRun: PromptRunResponse | null;
  selectedOutputIndex: number;
  compareMode: "tabs" | "grid" | "split";
}
```

### Store (`src/lib/stores/workbench.ts`)

```typescript
import { writable, derived } from "svelte/store";
import type { WorkbenchState, Model } from "$lib/types";

export const workbenchState = writable<WorkbenchState>({
  workspaceId: "vf_ws_01",
  sessionId: "vf_sess_" + Date.now(),

  availableContexts: [],
  selectedContextIds: [],
  selectedChunks: [],
  searchQuery: "",
  searchResults: [],
  isSearching: false,

  systemPrompt: "You are a helpful assistant.",
  userPrompt: "",
  selectedModels: ["nf:claude-3.5-sonnet"],
  isRunning: false,
  temperature: 0.4,
  maxTokens: 800,

  lastRun: null,
  selectedOutputIndex: 0,
  compareMode: "tabs",
});

export const models = writable<Model[]>([]);

export const selectedChunksSummary = derived(workbenchState, ($state) => {
  return $state.selectedChunks
    .map((c) => `${c.context_id}:${c.chunk_id}`)
    .join(", ");
});

export const tokenEstimate = derived(workbenchState, ($state) => {
  const systemTokens = Math.ceil($state.systemPrompt.length / 4);
  const promptTokens = Math.ceil($state.userPrompt.length / 4);
  const contextTokens = $state.selectedChunks.reduce(
    (sum, chunk) => sum + Math.ceil(chunk.text.length / 4),
    0
  );
  return systemTokens + promptTokens + contextTokens;
});
```

### Workbench Component Skeleton (`src/lib/components/Workbench.svelte`)

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { workbenchState, models, tokenEstimate } from '$lib/stores/workbench';
  import * as dataforgeAPI from '$lib/api/dataforge';
  import * as neuroforgeAPI from '$lib/api/neuroforge';
  import ContextSelector from './ContextSelector.svelte';
  import PromptComposer from './PromptComposer.svelte';
  import OutputViewer from './OutputViewer.svelte';

  let loading = false;
  let error: string | null = null;

  onMount(async () => {
    try {
      // Load available contexts and models on mount
      const [contexts, availableModels] = await Promise.all([
        dataforgeAPI.listContexts($workbenchState.workspaceId),
        neuroforgeAPI.listModels()
      ]);

      workbenchState.update((state) => ({
        ...state,
        availableContexts: contexts
      }));

      models.set(availableModels);
    } catch (err) {
      error = `Failed to initialize workbench: ${err}`;
    }
  });

  async function handleRunPrompt() {
    if (!$workbenchState.userPrompt.trim()) {
      error = 'Please enter a prompt';
      return;
    }

    if ($workbenchState.selectedModels.length === 0) {
      error = 'Please select at least one model';
      return;
    }

    loading = true;
    error = null;

    try {
      // Execute prompt via NeuroForge
      const response = await neuroforgeAPI.runPrompt({
        workspace_id: $workbenchState.workspaceId,
        session_id: $workbenchState.sessionId,
        prompt: $workbenchState.userPrompt,
        system: $workbenchState.systemPrompt,
        models: $workbenchState.selectedModels,
        contexts: $workbenchState.selectedChunks.map((chunk) => ({
          source: 'dataforge',
          context_id: chunk.context_id,
          chunk_id: chunk.chunk_id,
          text: chunk.text
        })),
        settings: {
          temperature: $workbenchState.temperature,
          max_tokens: $workbenchState.maxTokens
        }
      });

      // Store result
      workbenchState.update((state) => ({
        ...state,
        lastRun: response,
        selectedOutputIndex: 0
      }));

      // Log run to DataForge (async, fire-and-forget for now)
      // Phase 2: Add proper logging
    } catch (err) {
      error = `Failed to run prompt: ${err}`;
    } finally {
      loading = false;
    }
  }

  function toggleContext(contextId: string) {
    workbenchState.update((state) => {
      const index = state.selectedContextIds.indexOf(contextId);
      const newIds =
        index > -1
          ? state.selectedContextIds.filter((_, i) => i !== index)
          : [...state.selectedContextIds, contextId];
      return { ...state, selectedContextIds: newIds };
    });
  }

  function toggleModel(modelId: string) {
    workbenchState.update((state) => {
      const index = state.selectedModels.indexOf(modelId);
      const newModels =
        index > -1
          ? state.selectedModels.filter((_, i) => i !== index)
          : [...state.selectedModels, modelId];
      return { ...state, selectedModels: newModels };
    });
  }
</script>

<div class="workbench">
  <!-- Left Column: Context Selector -->
  <aside class="left-column">
    <ContextSelector
      contexts={$workbenchState.availableContexts}
      selectedContextIds={$workbenchState.selectedContextIds}
      selectedChunks={$workbenchState.selectedChunks}
      isSearching={$workbenchState.isSearching}
      {toggleContext}
    />
  </aside>

  <!-- Center Column: Prompt Composer -->
  <main class="center-column">
    <PromptComposer
      systemPrompt={$workbenchState.systemPrompt}
      userPrompt={$workbenchState.userPrompt}
      selectedModels={$workbenchState.selectedModels}
      availableModels={$models}
      temperature={$workbenchState.temperature}
      maxTokens={$workbenchState.maxTokens}
      tokenEstimate={$tokenEstimate}
      isRunning={loading}
      on:updateSystemPrompt={(e) =>
        workbenchState.update((s) => ({ ...s, systemPrompt: e.detail }))}
      on:updateUserPrompt={(e) =>
        workbenchState.update((s) => ({ ...s, userPrompt: e.detail }))}
      on:toggleModel={toggleModel}
      on:updateTemperature={(e) =>
        workbenchState.update((s) => ({ ...s, temperature: e.detail }))}
      on:updateMaxTokens={(e) =>
        workbenchState.update((s) => ({ ...s, maxTokens: e.detail }))}
      on:run={handleRunPrompt}
    />
    {#if error}
      <div class="error">{error}</div>
    {/if}
  </main>

  <!-- Right Column: Output Viewer -->
  <aside class="right-column">
    {#if $workbenchState.lastRun}
      <OutputViewer run={$workbenchState.lastRun} compareMode={$workbenchState.compareMode} />
    {:else if loading}
      <div class="loading">Running prompt...</div>
    {:else}
      <div class="placeholder">Run a prompt to see results</div>
    {/if}
  </aside>
</div>

<style>
  .workbench {
    display: grid;
    grid-template-columns: 1fr 2fr 1fr;
    gap: 1rem;
    height: 100vh;
    padding: 1rem;
  }

  .left-column,
  .right-column {
    overflow-y: auto;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 1rem;
  }

  .center-column {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-y: auto;
  }

  .error {
    background-color: #fee2e2;
    border: 1px solid #fecaca;
    color: #991b1b;
    padding: 0.75rem;
    border-radius: 0.375rem;
  }

  .loading,
  .placeholder {
    text-align: center;
    color: #6b7280;
    padding: 2rem;
  }

  @media (max-width: 1440px) {
    .workbench {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: auto 1fr;
    }

    .right-column {
      grid-column: 1 / -1;
    }
  }
</style>
```

---

## Environment Configuration

### `.env.example` (Updated)

```dotenv
# VibeForge Backend
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=false

# DataForge Integration
DATAFORGE_API_BASE=http://localhost:8001/api/v1
DATAFORGE_API_KEY=df-dev-key

# NeuroForge Integration
NEUROFORGE_API_BASE=http://localhost:8002/api/v1
NEUROFORGE_API_KEY=nf-dev-key

# Frontend (.env.local for SvelteKit)
VITE_DATAFORGE_API_BASE=http://localhost:8000/v1/dataforge
VITE_DATAFORGE_API_KEY=df-dev-key
VITE_NEUROFORGE_API_BASE=http://localhost:8000/v1/neuroforge
VITE_NEUROFORGE_API_KEY=nf-dev-key
```

---

## Phase 1 Checklist (Integration Skeleton)

- [ ] **Backend Models** - Create forge_integration_models.py with DF/NF types
- [ ] **Backend Services** - Create forge_integration_service.py with API clients
- [ ] **DataForge Router** - Implement /v1/dataforge endpoints (proxy to DF)
- [ ] **NeuroForge Router** - Implement /v1/neuroforge endpoints (proxy to NF)
- [ ] **Frontend Types** - Create TS types for all API contracts
- [ ] **Frontend API Clients** - Create dataforge.ts and neuroforge.ts modules
- [ ] **Workbench Store** - Create Svelte store for workbench state
- [ ] **Workbench Component** - Create main layout with 3 columns
- [ ] **Left Column** - ContextSelector component with search stub
- [ ] **Center Column** - PromptComposer with model dropdown
- [ ] **Right Column** - OutputViewer with tab switcher
- [ ] **Mock Data** - Add fallback responses for development
- [ ] **Integration Testing** - Test full flow with mock services

---

## Phase 2 Roadmap (Live Integration)

- [ ] **Debounced Search** - Add 300ms debounce to context search
- [ ] **Context Hydration** - Fetch full chunk text when user selects
- [ ] **Run Logging** - Log successful runs to DataForge after execution
- [ ] **History Panel** - Add collapsible panel to load past runs
- [ ] **Replay in Editor** - Allow user to re-run a previous prompt
- [ ] **Error Handling** - Proper error UI for failed API calls
- [ ] **Loading States** - Visual feedback during async operations

---

## Phase 3 Roadmap (Advanced Features)

- [ ] **Champion/Challenger** - Highlight champion model, show diff with challengers
- [ ] **Multi-Model Diff** - Side-by-side comparison with highlighting
- [ ] **Feedback Loop** - Send thumbs up/down to NeuroForge
- [ ] **Cost Tracking** - Show token usage + cost per response
- [ ] **Export Results** - Download runs as JSON/CSV/Markdown
- [ ] **Advanced Filtering** - Filter history by model, cost, quality
- [ ] **Prompt Templates** - Save and load prompt snippets

---

## Next Steps

1. **Implement Backend** - Add models, services, and router endpoints
2. **Test Integration** - Use Postman/curl to verify DF/NF contracts
3. **Implement Frontend** - Create Svelte components and API clients
4. **Integration Test** - End-to-end test with mock services
5. **Documentation** - Update API docs with new endpoints
6. **Deployment** - Package and deploy integrated system

---

**Architecture Document Created**: November 20, 2025  
**Phase 1 Status**: Ready for Implementation  
**Estimated Phase 1 Duration**: 1-2 weeks

"""VibeForge API router - Production endpoints for model runs."""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone
import time

from app.models.vibeforge_models import (
    CreateRunRequest,
    ModelRunModel,
    RunHistoryResponse,
    ContextBlockModel,
    TokenUsageModel,
)
from app.services.llm_service import get_llm_service
from app.repositories.runs_file import get_runs_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/vibeforge", tags=["VibeForge"])

# Global service instances
llm_service = get_llm_service()
runs_repo = get_runs_repo()


# ============================================================================
# Run Endpoints
# ============================================================================


@router.post("/run", response_model=ModelRunModel, status_code=201)
async def create_run(request: CreateRunRequest):
    """
    Create and execute a new model run.

    This endpoint:
    1. Creates a run record in pending state
    2. Calls Rust layer to build the final prompt and initial run
    3. Calls the LLM with the built prompt
    4. Updates the run with output and token counts
    5. Persists to JSON store

    Returns:
        The completed run record
    """
    try:
        logger.info(f"Creating run for model {request.model} with prompt length {len(request.prompt)}")

        # Step 1: Create initial run record in repository
        active_contexts_dicts = [
            {
                "id": ctx.id,
                "title": ctx.title,
                "content": ctx.content,
                "kind": ctx.kind,
                "priority": ctx.priority,
            }
            for ctx in request.active_contexts
        ]

        run = runs_repo.create_run(
            model=request.model,
            prompt=request.prompt,
            status="pending",
            active_contexts=active_contexts_dicts,
            data_profile_id=request.data_profile_id,
            eval_profile_id=request.eval_profile_id,
        )

        run_id = run["id"]
        logger.info(f"Created pending run {run_id}")

        # Step 2: Update to running state
        runs_repo.update_run(run_id, status="running", started_at=datetime.utcnow().isoformat() + "Z")

        # Step 3: Call LLM (in a real system, this might be async/queued)
        try:
            logger.info(f"Calling LLM {request.model}")
            start_time = time.time()

            llm_response = await llm_service.call_llm(
                model=request.model,
                prompt=request.prompt,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"LLM response received: {len(llm_response.content)} chars, "
                f"{llm_response.completion_tokens} completion tokens"
            )

            # Step 4: Update run with results
            completed_at = datetime.utcnow().isoformat() + "Z"
            runs_repo.update_run(
                run_id,
                status="complete",
                output=llm_response.content,
                tokens_used={
                    "prompt_tokens": llm_response.prompt_tokens,
                    "completion_tokens": llm_response.completion_tokens,
                    "total_tokens": llm_response.total_tokens,
                },
                completed_at=completed_at,
                duration_ms=elapsed_ms,
            )

            logger.info(f"Run {run_id} completed successfully")

        except Exception as e:
            logger.error(f"Error executing run {run_id}: {e}")
            error_msg = str(e)
            runs_repo.update_run(
                run_id,
                status="error",
                error=error_msg,
                completed_at=datetime.utcnow().isoformat() + "Z",
            )
            # Return the error state to client
            run = runs_repo.get_run(run_id)

        # Step 5: Return complete run
        final_run = runs_repo.get_run(run_id)
        if not final_run:
            raise HTTPException(status_code=500, detail="Run not found after creation")

        # Convert to Pydantic model
        tokens_used = None
        if final_run.get("tokens_used"):
            tokens_used = TokenUsageModel(**final_run["tokens_used"])

        return ModelRunModel(
            id=final_run["id"],
            model=final_run["model"],
            prompt=final_run["prompt"],
            status=final_run["status"],
            output=final_run.get("output"),
            error=final_run.get("error"),
            tokens_used=tokens_used,
            created_at=final_run["created_at"],
            started_at=final_run.get("started_at"),
            completed_at=final_run.get("completed_at"),
            duration_ms=final_run.get("duration_ms"),
            active_contexts=request.active_contexts,
            data_profile_id=request.data_profile_id,
            eval_profile_id=request.eval_profile_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in create_run: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/run/{run_id}", response_model=ModelRunModel)
async def get_run(run_id: str):
    """Retrieve a run by ID."""
    try:
        run = runs_repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        tokens_used = None
        if run.get("tokens_used"):
            tokens_used = TokenUsageModel(**run["tokens_used"])

        # Reconstruct contexts from saved data
        active_contexts = [
            ContextBlockModel(
                id=ctx.get("id", ""),
                title=ctx.get("title", ""),
                content=ctx.get("content", ""),
                kind=ctx.get("kind", "code"),
                priority=ctx.get("priority", 0),
            )
            for ctx in run.get("active_contexts", [])
        ]

        return ModelRunModel(
            id=run["id"],
            model=run["model"],
            prompt=run["prompt"],
            status=run["status"],
            output=run.get("output"),
            error=run.get("error"),
            tokens_used=tokens_used,
            created_at=run["created_at"],
            started_at=run.get("started_at"),
            completed_at=run.get("completed_at"),
            duration_ms=run.get("duration_ms"),
            active_contexts=active_contexts,
            data_profile_id=run.get("data_profile_id"),
            eval_profile_id=run.get("eval_profile_id"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=RunHistoryResponse)
async def get_history(
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
    model: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Retrieve run history with optional filters.

    Supports filtering by model, status, and pagination.
    """
    try:
        result = runs_repo.list_runs(
            limit=limit,
            offset=offset,
            model=model,
            status=status,
        )

        items = []
        for run in result["items"]:
            tokens_used = None
            if run.get("tokens_used"):
                tokens_used = TokenUsageModel(**run["tokens_used"])

            active_contexts = [
                ContextBlockModel(
                    id=ctx.get("id", ""),
                    title=ctx.get("title", ""),
                    content=ctx.get("content", ""),
                    kind=ctx.get("kind", "code"),
                    priority=ctx.get("priority", 0),
                )
                for ctx in run.get("active_contexts", [])
            ]

            items.append(
                ModelRunModel(
                    id=run["id"],
                    model=run["model"],
                    prompt=run["prompt"],
                    status=run["status"],
                    output=run.get("output"),
                    error=run.get("error"),
                    tokens_used=tokens_used,
                    created_at=run["created_at"],
                    started_at=run.get("started_at"),
                    completed_at=run.get("completed_at"),
                    duration_ms=run.get("duration_ms"),
                    active_contexts=active_contexts,
                    data_profile_id=run.get("data_profile_id"),
                    eval_profile_id=run.get("eval_profile_id"),
                )
            )

        return RunHistoryResponse(
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
            items=items,
        )

    except Exception as e:
        logger.exception(f"Error retrieving history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Context Endpoints (Stub for future implementation)
# ============================================================================
# Context management to be implemented with dedicated context repository


@router.get("/health", tags=["System"])
async def health():
    """Health check for VibeForge API."""
    return {"status": "ok", "service": "vibeforge"}


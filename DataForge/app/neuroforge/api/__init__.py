"""
NeuroForge API Routes

Main endpoints for inference, pipelines, and evaluation.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from app.neuroforge.models import InferenceRequest, InferenceResult
from app.neuroforge.services import (
    run_inference,
    get_dataforge_client,
)
from app.neuroforge.cache import get_context_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@router.post("/")
async def submit_inference(request: InferenceRequest) -> dict:
    """
    Submit inference request to the pipeline.
    
    Triggers full 5-stage pipeline with DataForge integration:
    1. Context Builder: Fetch from DataForge
    2. Prompt Engine: Build prompt
    3. Model Router: Select model
    4. Evaluator: Score output
    5. Post Processor: Log provenance
    
    Request:
        domain: "literary" | "trading" | "generic"
        task_type: "analysis" | "generation" | "summary"
        user_query: The actual user query/prompt
        max_tokens: Maximum output tokens
        model_override: Optional specific model to use
    
    Response:
        inference_id: Unique ID for this run
        request_id: Your request ID
        status: "success" | "partial" | "failed"
        output: Final answer text
        model_id: Which model was used
        latency_ms: Total inference time
        evaluation_scores: Quality scores
    """
    try:
        dataforge_client = get_dataforge_client()
        result = await run_inference(request, dataforge_client)
        return result.model_dump()
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Inference failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.get("/history")
async def get_inference_history(
    domain: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    Get recent inference history.
    
    Query params:
        domain: Filter by domain (optional)
        limit: Max results (default 50, max 500)
    
    Response: List of InferenceResult objects
    """
    # Stub - replace with database queries
    return {"inferences": [], "total": 0}


@router.get("/cache/metrics")
async def get_cache_metrics() -> dict:
    """
    Get context cache metrics.
    
    Response:
        hits: Cache hits
        misses: Cache misses
        hit_rate_percent: Hit percentage
        evictions: LRU evictions
        current_size: Items in cache
        max_size: Maximum size
    """
    cache = get_context_cache()
    return await cache.get_metrics()


@router.post("/cache/clear")
async def clear_cache() -> dict:
    """Clear the context cache."""
    cache = get_context_cache()
    await cache.clear()
    return {"status": "cleared"}


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    try:
        client = get_dataforge_client()
        return {
            "status": "healthy",
            "dataforge_circuit_state": client.circuit_breaker.state.value,
        }
    except Exception as e:
        logger.warning(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }

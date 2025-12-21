"""
Inference Pipeline Integration

Main orchestration that wires together all stages with DataForge integration.

Complete 5-stage pipeline:
1. ContextBuilder: Fetch context from DataForge
2. PromptEngine: Build prompt with context
3. ModelRouter: Select model based on request
4. Evaluator: Score output quality
5. PostProcessor: Log provenance to DataForge

This module provides:
- run_inference(): Main entry point
- Pipeline coordination
- Error handling and logging
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from app.neuroforge.models import (
    InferenceRequest,
    InferenceResult,
    BuiltContext,
    ModelDecision,
    EvaluationScore,
)
from app.neuroforge.services import (
    DataForgeClient,
    get_dataforge_client,
)
from app.neuroforge.services.context_builder import build_context_for_request
from app.neuroforge.services.post_processor import post_process_and_log_provenance

logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Stub Implementations (Replace with real implementations)
# ============================================================================

async def _prompt_engine_build(
    context: BuiltContext,
    request: InferenceRequest,
) -> str:
    """
    Build final prompt from context and user query.
    
    Stage 2: PromptEngine
    
    This is a stub - replace with actual prompt template logic.
    """
    system_prompt = "You are a helpful assistant."
    
    context_text = "\n\n".join(context.text_blocks)
    
    prompt = (
        f"{system_prompt}\n\n"
        f"## Context\n{context_text}\n\n"
        f"## User Query\n{request.user_query}"
    )
    
    return prompt


async def _model_router_select(
    request: InferenceRequest,
    context: BuiltContext,
) -> ModelDecision:
    """
    Route request to appropriate model.
    
    Stage 3: ModelRouter
    
    This is a stub - replace with actual routing logic based on:
    - domain
    - task_type
    - model availability
    - latency/cost constraints
    """
    # Simple routing: use override if provided, else default by domain
    model_id = request.model_override or f"model-{request.domain}-default"
    
    return ModelDecision(
        selected_model_id=model_id,
        confidence=0.95,
        ensemble_models=None,
        reasoning="Default routing based on domain",
    )


async def _evaluator_score(
    output: str,
    request: InferenceRequest,
    context: BuiltContext,
) -> list[EvaluationScore]:
    """
    Evaluate output quality.
    
    Stage 4: Evaluator
    
    This is a stub - replace with actual evaluation logic using:
    - LLM rubrics
    - Metric calculations
    - Consistency checks
    """
    # Stub implementation
    return [
        EvaluationScore(
            metric="quality",
            score=0.85,
            reasoning="Sample evaluation",
        )
    ]


# ============================================================================
# Main Pipeline Orchestration
# ============================================================================

async def run_inference(
    request: InferenceRequest,
    dataforge_client: Optional[DataForgeClient] = None,
) -> InferenceResult:
    """
    Execute complete inference pipeline with DataForge integration.
    
    Pipeline stages:
    1. Build context from DataForge
    2. Build prompt with context
    3. Route to selected model
    4. (Simulate) model inference
    5. Evaluate result
    6. Post-process and log provenance
    
    Args:
        request: InferenceRequest
        dataforge_client: Optional DataForgeClient (uses singleton if None)
    
    Returns:
        InferenceResult with final answer and metadata
    
    Raises:
        ValueError: If context unavailable
        Exception: From any pipeline stage
    """
    if dataforge_client is None:
        dataforge_client = get_dataforge_client()
    
    # Ensure request has ID
    if not request.request_id:
        request.request_id = str(uuid.uuid4())
    
    inference_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Starting inference: id={inference_id}, request_id={request.request_id}, domain={request.domain}")
    
    try:
        # ====== Stage 1: Context Builder ======
        logger.debug(f"Stage 1: Building context...")
        context = await build_context_for_request(request, dataforge_client)
        logger.debug(f"Context ready: pack_id={context.context_pack_id}, snippets={len(context.text_blocks)}")
        
        # ====== Stage 2: Prompt Engine ======
        logger.debug(f"Stage 2: Building prompt...")
        prompt = await _prompt_engine_build(context, request)
        logger.debug(f"Prompt built: {len(prompt)} chars")
        
        # ====== Stage 3: Model Router ======
        logger.debug(f"Stage 3: Routing to model...")
        model_decision = await _model_router_select(request, context)
        logger.debug(f"Model selected: {model_decision.selected_model_id}")
        
        # ====== Stage 4: (Simulated) Model Inference ======
        logger.debug(f"Stage 4: Running model inference...")
        # Stub - replace with actual LLM call
        model_output = f"[Output from {model_decision.selected_model_id}] {request.user_query[:50]}..."
        tokens_in = len(prompt.split())
        tokens_out = len(model_output.split())
        
        # ====== Stage 5: Evaluator ======
        logger.debug(f"Stage 5: Evaluating result...")
        evaluation_scores = await _evaluator_score(model_output, request, context)
        logger.debug(f"Evaluation complete: scores={len(evaluation_scores)}")
        
        # Build result
        latency_ms = int((time.time() - start_time) * 1000)
        result = InferenceResult(
            inference_id=inference_id,
            request_id=request.request_id,
            status="success",
            output=model_output,
            model_id=model_decision.selected_model_id,
            latency_ms=latency_ms,
            tokens_used=tokens_in + tokens_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            evaluation_scores=evaluation_scores,
            model_decision=model_decision,
            metadata={
                "domain": request.domain,
                "task_type": request.task_type,
                "pipeline_version": "1.0",
            },
            context_pack_id=context.context_pack_id,
        )
        
        # ====== Stage 6: Post-Process & Log Provenance ======
        logger.debug(f"Stage 6: Post-processing and logging provenance...")
        result = await post_process_and_log_provenance(
            result,
            context_pack_id=context.context_pack_id,
            dataforge_client=dataforge_client,
        )
        
        logger.info(
            f"Inference complete: id={inference_id}, model={result.model_id}, "
            f"latency={result.latency_ms}ms, status={result.status}"
        )
        
        return result
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Inference failed: id={inference_id}, {type(e).__name__}: {e}", exc_info=True)
        
        # Return error result (still logs to DataForge via post_processor)
        result = InferenceResult(
            inference_id=inference_id,
            request_id=request.request_id,
            status="failed",
            output=f"Error: {str(e)}",
            model_id="error",
            latency_ms=latency_ms,
            tokens_used=0,
            metadata={
                "error_type": type(e).__name__,
                "domain": request.domain,
            },
            context_pack_id=request.context_pack_id,
        )
        
        # Log error result (best-effort)
        try:
            await post_process_and_log_provenance(
                result,
                context_pack_id=request.context_pack_id,
                dataforge_client=dataforge_client,
            )
        except Exception as log_error:
            logger.warning(f"Failed to log error provenance: {log_error}")
        
        raise


async def get_inference_status(inference_id: str) -> Optional[str]:
    """
    Get status of inference by ID.
    
    Stub - replace with database lookup.
    """
    return None

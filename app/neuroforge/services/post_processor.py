"""
Post Processor

Final pipeline stage that logs provenance back to DataForge.

Pipeline Stage 5: Post-process and log
- Run formatting/normalization logic
- Build provenance payload
- Log to DataForge (fire-and-forget)
- Return final result
"""
import logging
from typing import Optional
from datetime import datetime

from app.neuroforge.models import InferenceResult, BuiltContext
from app.neuroforge.services import (
    DataForgeClient,
    DataForgeProvenancePayload,
    get_dataforge_client,
)

logger = logging.getLogger(__name__)


async def post_process_and_log_provenance(
    result: InferenceResult,
    *,
    context_pack_id: Optional[str] = None,
    dataforge_client: Optional[DataForgeClient] = None,
) -> InferenceResult:
    """
    Post-process inference result and log provenance to DataForge.
    
    Operations:
    1. Run formatting/normalization on output text
    2. Build provenance payload with all relevant metadata
    3. Send to DataForge (non-blocking, errors logged but not fatal)
    4. Return processed result
    
    Provenance includes:
    - context_pack_id (from BuiltContext or parameter)
    - request_id (from result)
    - final answer text
    - model_id and latency
    - tokens_in/out
    - router decision metadata
    
    Args:
        result: InferenceResult to post-process
        context_pack_id: Optional override for context_pack_id (uses result.context_pack_id if None)
        dataforge_client: Optional DataForgeClient (uses singleton if None)
    
    Returns:
        Post-processed InferenceResult (unmodified for now, but available for formatting later)
    """
    if dataforge_client is None:
        dataforge_client = get_dataforge_client()
    
    # Step 1: Format/normalize output (placeholder for future enhancements)
    processed_output = result.output.strip()
    result.output = processed_output
    
    # Step 2: Determine context_pack_id
    pack_id = context_pack_id or result.context_pack_id or "unknown"
    
    # Step 3: Build provenance payload
    extra_metadata = {
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "inference_id": result.inference_id,
        "domain": result.metadata.get("domain"),
        "task_type": result.metadata.get("task_type"),
    }
    
    # Add router decision if available
    if result.model_decision:
        extra_metadata["router_decision"] = {
            "selected_model": result.model_decision.selected_model_id,
            "confidence": result.model_decision.confidence,
            "ensemble": result.model_decision.ensemble_models,
            "reasoning": result.model_decision.reasoning,
        }
    
    # Add evaluation scores if available
    if result.evaluation_scores:
        extra_metadata["evaluation_scores"] = [
            {
                "metric": score.metric,
                "score": score.score,
                "reasoning": score.reasoning,
            }
            for score in result.evaluation_scores
        ]
    
    provenance_payload = DataForgeProvenancePayload(
        context_pack_id=pack_id,
        request_id=result.request_id,
        answer=result.output,
        model_name=result.model_id,
        latency_ms=result.latency_ms,
        extra=extra_metadata,
    )
    
    # Step 4: Log to DataForge (fire-and-forget)
    logger.debug(f"Logging provenance: {result.request_id} → {pack_id}")
    await dataforge_client.log_provenance(
        provenance_payload,
        request_id=result.request_id
    )
    
    return result


async def format_output(text: str) -> str:
    """
    Format/normalize inference output.
    
    Can be extended for:
    - Markdown cleanup
    - Citation formatting
    - Token limit enforcement
    - Sensitivity redaction
    
    Args:
        text: Raw output from model
    
    Returns:
        Formatted output
    """
    # Basic normalization
    text = text.strip()
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


def build_provenance_summary(result: InferenceResult, context: Optional[BuiltContext]) -> dict:
    """
    Build a summary of provenance data for logging/metrics.
    
    Useful for analytics and debugging.
    
    Args:
        result: InferenceResult
        context: Optional BuiltContext
    
    Returns:
        Summary dict with key metrics
    """
    return {
        "request_id": result.request_id,
        "model_id": result.model_id,
        "latency_ms": result.latency_ms,
        "tokens_used": result.tokens_used,
        "context_snippets": len(context.text_blocks) if context else 0,
        "status": result.status,
        "evaluation_score": (
            result.evaluation_scores[0].score
            if result.evaluation_scores else None
        ),
    }

"""
NeuroForge Services

Initialization and exports for NeuroForge services.
"""

from app.neuroforge.services.dataforge_client import (
    DataForgeClient,
    DataForgeContextRequest,
    DataForgeContextPack,
    DataForgeProvenancePayload,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    get_dataforge_client,
    initialize_dataforge_client,
    shutdown_dataforge_client,
)
from app.neuroforge.services.context_builder import (
    build_context_for_request,
    prefetch_context,
    clear_context_cache,
)
from app.neuroforge.services.post_processor import (
    post_process_and_log_provenance,
    format_output,
    build_provenance_summary,
)
from app.neuroforge.services.inference_pipeline import (
    run_inference,
    get_inference_status,
)

__all__ = [
    # DataForge Client
    "DataForgeClient",
    "DataForgeContextRequest",
    "DataForgeContextPack",
    "DataForgeProvenancePayload",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerState",
    "get_dataforge_client",
    "initialize_dataforge_client",
    "shutdown_dataforge_client",
    # Context Builder
    "build_context_for_request",
    "prefetch_context",
    "clear_context_cache",
    # Post Processor
    "post_process_and_log_provenance",
    "format_output",
    "build_provenance_summary",
    # Pipeline
    "run_inference",
    "get_inference_status",
]

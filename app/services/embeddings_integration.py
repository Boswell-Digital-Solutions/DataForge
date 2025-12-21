"""
Integration module for using Resilient Embedding Service in DataForge API.

This module provides helper functions to gradually migrate to the resilient service
while maintaining backward compatibility with existing code.

Usage:
    In API routers, use:
        from app.services.embeddings_integration import get_embedding_with_resilience
        embedding = await get_embedding_with_resilience(text)
"""

import logging
from typing import List, Dict, Any

from app.utils.resilient_embeddings import get_resilient_embedding_service

logger = logging.getLogger(__name__)


async def get_embedding_with_resilience(text: str) -> List[float]:
    """
    Generate embedding with circuit breaker protection and automatic fallback.

    This is a drop-in replacement for generate_embedding() that adds:
    - Circuit breaker protection for each provider
    - Automatic fallback between providers
    - Health monitoring and metrics

    Args:
        text: Text to generate embedding for

    Returns:
        Embedding vector (list of floats)

    Raises:
        Exception: If all providers are unavailable
    """
    service = get_resilient_embedding_service()
    return await service.generate_embedding(text)


async def get_embeddings_batch_with_resilience(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts with resilience.

    This is a drop-in replacement for generate_embeddings_batch() that adds:
    - Circuit breaker protection for each provider
    - Automatic fallback between providers
    - Batch-level metrics

    Args:
        texts: List of texts to generate embeddings for

    Returns:
        List of embedding vectors

    Raises:
        Exception: If all providers are unavailable
    """
    service = get_resilient_embedding_service()
    return await service.generate_embeddings_batch(texts)


def get_embedding_service_health() -> Dict[str, Any]:
    """
    Get health status of all embedding providers.

    Returns dict with:
    - Circuit states (closed/open/half-open) for each provider
    - Metrics (success rate, latency) for each provider
    - Overall recommendations

    Usage in health check endpoint:
        @app.get("/health/embeddings")
        def embedding_health():
            service = get_resilient_embedding_service()
            return service.get_provider_health()
    """
    service = get_resilient_embedding_service()
    return service.get_provider_health()


def reset_embedding_circuit_breaker(provider: str) -> bool:
    """
    Manually reset a provider's circuit breaker.

    This should only be called after manual intervention to restore
    a failed provider (e.g., after upgrading provider service).

    Args:
        provider: Provider name (voyage, openai, cohere)

    Returns:
        True if reset successful, False if provider not found

    Usage in admin endpoint:
        @app.post("/admin/embeddings/reset")
        def reset_breaker(provider: str):
            success = reset_embedding_circuit_breaker(provider)
            return {"success": success}
    """
    service = get_resilient_embedding_service()
    return service.reset_circuit_breaker(provider)

"""
Context Builder

Orchestrates context retrieval from DataForge with local caching.

Pipeline Stage 0: Prepare context for inference
- Compute cache key from request
- Check LRU cache
- Fetch from DataForge if miss
- Cache result with TTL
- Handle circuit breaker failures gracefully
"""
import hashlib
import logging
from typing import Optional
from datetime import datetime, UTC

from app.neuroforge.models import InferenceRequest, BuiltContext
from app.neuroforge.services import (
    DataForgeClient,
    DataForgeContextRequest,
    CircuitBreakerOpenError,
    get_dataforge_client,
)
from app.neuroforge.cache import get_context_cache
from app.neuroforge.config import get_settings

logger = logging.getLogger(__name__)


def _compute_cache_key(request: InferenceRequest) -> str:
    """
    Compute stable cache key from request.
    
    Key includes domain, task type, and query hash to avoid spurious cache hits.
    """
    key_parts = f"{request.domain}:{request.task_type}:{request.user_query}"
    query_hash = hashlib.sha256(key_parts.encode()).hexdigest()[:16]
    return f"ctx:{request.domain}:{request.task_type}:{query_hash}"


async def build_context_for_request(
    request: InferenceRequest,
    dataforge_client: Optional[DataForgeClient] = None,
) -> BuiltContext:
    """
    Build context for inference request.
    
    Retrieval sequence:
    1. Compute cache key
    2. Check LRU cache
    3. Fetch from DataForge (with retries + circuit breaker)
    4. Map response to BuiltContext
    5. Store in cache with TTL
    6. Return to pipeline
    
    Failure handling:
    - On DataForge circuit open: attempt cached fallback, then raise
    - On network timeout: retries happen in DataForgeClient
    - On 4xx errors: raised immediately (no retry)
    
    Args:
        request: InferenceRequest
        dataforge_client: Optional DataForgeClient (uses singleton if None)
    
    Returns:
        BuiltContext ready for PromptEngine
    
    Raises:
        ValueError: If context unavailable and no fallback exists
        CircuitBreakerOpenError: If DataForge unavailable and cache miss
    """
    settings = get_settings()
    if dataforge_client is None:
        dataforge_client = get_dataforge_client()
    
    cache = get_context_cache()
    cache_key = _compute_cache_key(request)
    
    # Step 1: Check cache
    logger.debug(f"Context builder: checking cache for key={cache_key}")
    cached_context = await cache.get(cache_key)
    if cached_context:
        logger.info(f"Context cache hit: {cache_key}")
        return cached_context
    
    # Step 2: Cache miss - try DataForge
    logger.debug(f"Context cache miss: {cache_key}, fetching from DataForge")
    
    try:
        # Build DataForge request
        df_request = DataForgeContextRequest(
            project_id=request.metadata.get("project_id", "default"),
            query=request.user_query,
            domain=request.domain,
            max_tokens=request.max_tokens,
            filters=request.metadata.get("filters")
        )
        
        # Fetch from DataForge
        context_pack = await dataforge_client.fetch_context_pack(
            df_request,
            request_id=request.request_id
        )
        logger.info(f"Context fetched from DataForge: pack_id={context_pack.id}, snippets={len(context_pack.snippets)}")
        
        # Map to BuiltContext
        text_blocks = [s.text for s in context_pack.snippets]
        built_context = BuiltContext(
            context_pack_id=context_pack.id,
            text_blocks=text_blocks,
            metadata={
                "source_ids": [s.source_id for s in context_pack.snippets],
                "dataforge_metadata": context_pack.metadata.model_dump(),
                "snippet_count": len(context_pack.snippets),
            },
            source="dataforge",
            cached_at=datetime.now(UTC),
            ttl_seconds=settings.dataforge_cache_ttl,
        )
        
        # Step 3: Cache result
        if settings.dataforge_cache_enabled:
            await cache.put(cache_key, built_context)
            logger.debug(f"Context cached with TTL {settings.dataforge_cache_ttl}s: {cache_key}")
        
        return built_context
    
    except CircuitBreakerOpenError as e:
        logger.error(f"DataForge circuit breaker open: {e}")
        # Try to use any cached entry (even expired) as fallback
        if cache_key in cache._cache:
            logger.warning(f"Falling back to expired cache entry: {cache_key}")
            return cache._cache[cache_key]
        raise ValueError(f"DataForge unavailable and no cached context for {cache_key}")
    
    except Exception as e:
        logger.error(f"Failed to fetch context from DataForge: {type(e).__name__}: {e}")
        raise


async def prefetch_context(
    requests: list[InferenceRequest],
    dataforge_client: Optional[DataForgeClient] = None,
) -> dict[str, Optional[BuiltContext]]:
    """
    Prefetch context for multiple requests (batch optimization).
    
    Useful for evaluation runs or batch inference.
    
    Args:
        requests: List of InferenceRequests
        dataforge_client: Optional DataForgeClient
    
    Returns:
        Dict mapping request.request_id -> BuiltContext or None on error
    """
    results = {}
    for request in requests:
        try:
            context = await build_context_for_request(request, dataforge_client)
            results[request.request_id] = context
        except Exception as e:
            logger.warning(f"Failed to prefetch context for {request.request_id}: {e}")
            results[request.request_id] = None
    
    return results


async def clear_context_cache() -> None:
    """Clear the entire context cache (useful for testing/reset)."""
    cache = get_context_cache()
    await cache.clear()
    logger.info("Context cache cleared")

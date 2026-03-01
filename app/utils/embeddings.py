"""
Embedding utilities — routes all embedding requests through NeuroForge.

Law 2 Compliance: All AI operations route through NeuroForge.
NeuroForge provides POST /api/v1/embed for text embeddings.

This module maintains the same public API (generate_embedding,
generate_embeddings_batch, chunk_text) so all callers work unchanged.
"""

import json
import logging
import os
from typing import List

import httpx
from fastapi import HTTPException

from app.config import EMBEDDING_MODEL, EMBEDDING_RESULTS_CACHE_TTL, MAX_EMBEDDING_INPUT_LENGTH
from app.utils.cache_governance import build_embed_cache_key, redis_set_with_ttl_sync

logger = logging.getLogger(__name__)

# NeuroForge endpoint
NEUROFORGE_URL = os.getenv("NEUROFORGE_URL", "http://127.0.0.1:8000")
NEUROFORGE_EMBED_ENDPOINT = f"{NEUROFORGE_URL}/api/v1/embed"

# Max texts per NeuroForge request
NEUROFORGE_BATCH_LIMIT = 100

# Redis cache for embeddings (lazy-initialized)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_redis_client = None


def get_redis_for_embeddings():
    """Get Redis client for embedding caching."""
    global _redis_client

    if not REDIS_AVAILABLE:
        return None

    if _redis_client is None:
        try:
            from app.config import REDIS_URL
            if REDIS_URL:
                _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                _redis_client.ping()
                logger.debug("Redis client initialized for embeddings")
        except Exception as e:
            logger.debug(f"Redis init for embeddings failed: {e}")

    return _redis_client


def get_embedding_cache_key(text: str, provider: str = "neuroforge") -> str:
    """Generate a cache key for an embedding."""
    model_name = provider if provider != "neuroforge" else EMBEDDING_MODEL
    return build_embed_cache_key(model_name, text)


def get_cached_embedding(text: str):
    """Get embedding from cache if available."""
    try:
        client = get_redis_for_embeddings()
        if not client:
            return None

        cache_key = get_embedding_cache_key(text)
        cached = client.get(cache_key)
        if cached:
            logger.debug(f"Embedding cache hit: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        logger.debug(f"Embedding cache get error: {e}")

    return None


def cache_embedding(text: str, embedding: List[float]) -> bool:
    """Cache an embedding with an explicit TTL."""
    try:
        client = get_redis_for_embeddings()
        if not client:
            return False

        cache_key = get_embedding_cache_key(text)
        redis_set_with_ttl_sync(
            client,
            cache_key,
            json.dumps(embedding),
            EMBEDDING_RESULTS_CACHE_TTL,
        )
        logger.debug(f"Embedding cached: {cache_key}")
        return True
    except Exception as e:
        logger.debug(f"Embedding cache set error: {e}")

    return False


async def _call_neuroforge_embed(texts: List[str], model: str | None = None) -> List[List[float]]:
    """Call NeuroForge /api/v1/embed endpoint.

    Args:
        texts: List of texts to embed
        model: Optional model override

    Returns:
        List of embedding vectors

    Raises:
        HTTPException: If NeuroForge is unavailable or returns error
    """
    payload = {"texts": texts}
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(NEUROFORGE_EMBED_ENDPOINT, json=payload)
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"NeuroForge unavailable at {NEUROFORGE_URL}. Ensure NeuroForge is running on port 8000."
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="NeuroForge embedding request timed out (60s)."
            )

    if response.status_code != 200:
        detail = response.text[:500] if response.text else "Unknown error"
        raise HTTPException(
            status_code=502,
            detail=f"NeuroForge embed error (HTTP {response.status_code}): {detail}"
        )

    data = response.json()
    return data["embeddings"]


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text via NeuroForge.
    Results are cached for 1 hour.

    Args:
        text: Text to generate embedding for

    Returns:
        List of floats representing the embedding vector

    Raises:
        HTTPException: If embedding generation fails
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(text) > MAX_EMBEDDING_INPUT_LENGTH:
        logger.warning(f"Input text length {len(text)} exceeds max {MAX_EMBEDDING_INPUT_LENGTH}, truncating")
        text = text[:MAX_EMBEDDING_INPUT_LENGTH]

    # Check cache first
    cached_embedding = get_cached_embedding(text)
    if cached_embedding:
        return cached_embedding

    try:
        embeddings = await _call_neuroforge_embed([text])
        embedding = embeddings[0]

        # Cache the result
        cache_embedding(text, embedding)

        return embedding

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embedding via NeuroForge: {str(e)}"
        )


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch via NeuroForge.
    More efficient than calling generate_embedding multiple times.
    Results are cached individually for 1 hour.

    Args:
        texts: List of texts to generate embeddings for

    Returns:
        List of embedding vectors

    Raises:
        HTTPException: If embedding generation fails
    """
    if not texts:
        return []

    # Validate and truncate inputs
    validated_texts = []
    for i, text in enumerate(texts):
        if not text or not text.strip():
            logger.warning(f"Empty text at index {i}, using placeholder")
            validated_texts.append(".")
        elif len(text) > MAX_EMBEDDING_INPUT_LENGTH:
            logger.warning(f"Text at index {i} length {len(text)} exceeds max, truncating")
            validated_texts.append(text[:MAX_EMBEDDING_INPUT_LENGTH])
        else:
            validated_texts.append(text)

    try:
        embeddings: List[List[float]] = []
        texts_to_generate: List[int] = []

        # Check cache for each text
        for i, text in enumerate(validated_texts):
            cached = get_cached_embedding(text)
            if cached:
                embeddings.append(cached)
            else:
                embeddings.append([])
                texts_to_generate.append(i)

        # If all cached, return early
        if not texts_to_generate:
            logger.debug(f"All {len(validated_texts)} embeddings from cache")
            return embeddings

        # Generate missing embeddings in batches (NeuroForge limit: 100 per request)
        texts_batch = [validated_texts[i] for i in texts_to_generate]
        logger.debug(f"Generating {len(texts_batch)} embeddings via NeuroForge from {len(validated_texts)} total")

        all_generated: List[List[float]] = []
        for batch_start in range(0, len(texts_batch), NEUROFORGE_BATCH_LIMIT):
            batch = texts_batch[batch_start:batch_start + NEUROFORGE_BATCH_LIMIT]
            batch_embeddings = await _call_neuroforge_embed(batch)
            all_generated.extend(batch_embeddings)

        # Insert generated embeddings into result and cache them
        for i, gen_idx in enumerate(texts_to_generate):
            embedding = all_generated[i]
            embeddings[gen_idx] = embedding
            cache_embedding(validated_texts[gen_idx], embedding)

        return embeddings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings via NeuroForge: {str(e)}"
        )


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence or paragraph boundary
        if end < len(text):
            for delimiter in ['\n\n', '\n', '. ', '! ', '? ']:
                last_delim = text[start:end].rfind(delimiter)
                if last_delim != -1:
                    end = start + last_delim + len(delimiter)
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks

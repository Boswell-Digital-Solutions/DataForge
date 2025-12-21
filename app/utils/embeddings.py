import os
from typing import List
import logging
import hashlib
import json
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

from app.config import (
    MAX_EMBEDDING_INPUT_LENGTH,
    EMBEDDING_MODEL,
    VOYAGE_API_KEY,
    OPENAI_API_KEY,
    COHERE_API_KEY
)

logger = logging.getLogger(__name__)

# Redis cache for embeddings (lazy-initialized)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_redis_client: any = None  # type: ignore


def get_redis_for_embeddings() -> any:  # type: ignore
    """Get Redis client for embedding caching."""
    global _redis_client
    
    if not REDIS_AVAILABLE:
        return None
    
    if _redis_client is None:
        try:
            from app.config import REDIS_URL
            if REDIS_URL:
                _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                _redis_client.ping()  # type: ignore
                logger.debug("Redis client initialized for embeddings")
        except Exception as e:
            logger.debug(f"Redis init for embeddings failed: {e}")
    
    return _redis_client


def get_embedding_cache_key(text: str, provider: str = "default") -> str:
    """Generate a cache key for an embedding."""
    # Hash to keep keys reasonable length
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"embedding:{provider}:{text_hash}"


def get_cached_embedding(text: str) -> any:  # type: ignore
    """Get embedding from cache if available."""
    try:
        client = get_redis_for_embeddings()
        if not client:
            return None
        
        cache_key = get_embedding_cache_key(text)
        cached = client.get(cache_key)  # type: ignore
        if cached:
            logger.debug(f"Embedding cache hit: {cache_key}")
            return json.loads(cached)  # type: ignore
    except Exception as e:
        logger.debug(f"Embedding cache get error: {e}")
    
    return None


def cache_embedding(text: str, embedding: List[float]) -> bool:
    """Cache an embedding for 1 hour."""
    try:
        client = get_redis_for_embeddings()
        if not client:
            return False
        
        cache_key = get_embedding_cache_key(text)
        client.setex(cache_key, 3600, json.dumps(embedding))  # type: ignore
        logger.debug(f"Embedding cached: {cache_key}")
        return True
    except Exception as e:
        logger.debug(f"Embedding cache set error: {e}")
    
    return False


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using configured provider.
    Results are cached for 1 hour.

    Priority: Voyage AI (Anthropic-owned) > OpenAI > Cohere
    Voyage AI is recommended for use with Anthropic's ecosystem.

    Args:
        text: Text to generate embedding for

    Returns:
        List of floats representing the embedding vector

    Raises:
        HTTPException: If embedding generation fails
    """
    # Validate and truncate input
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(text) > MAX_EMBEDDING_INPUT_LENGTH:
        logger.warning(f"Input text length {len(text)} exceeds max {MAX_EMBEDDING_INPUT_LENGTH}, truncating")
        text = text[:MAX_EMBEDDING_INPUT_LENGTH]

    # Check cache first
    cached_embedding = get_cached_embedding(text)
    if cached_embedding:
        return cached_embedding  # type: ignore

    try:
        embedding = None
        
        # Option 1: Voyage AI (Recommended - Anthropic-owned)
        if VOYAGE_API_KEY:
            import voyageai

            vo = voyageai.Client(api_key=VOYAGE_API_KEY)
            result = vo.embed(
                [text],
                model=EMBEDDING_MODEL,
                input_type="document"
            )
            embedding = result.embeddings[0]  # type: ignore

        # Option 2: OpenAI
        elif OPENAI_API_KEY:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            embedding = response.data[0].embedding  # type: ignore

        # Option 3: Cohere
        elif COHERE_API_KEY:
            import cohere

            co = cohere.Client(COHERE_API_KEY)
            response = co.embed(
                texts=[text],
                model="embed-english-v3.0",
                input_type="search_document"
            )
            embedding = response.embeddings[0]  # type: ignore

        else:
            raise HTTPException(
                status_code=500,
                detail="No embedding provider configured. Please set VOYAGE_API_KEY, OPENAI_API_KEY, or COHERE_API_KEY."
            )

        # Cache the result
        if embedding:
            cache_embedding(text, embedding)
        
        return embedding  # type: ignore

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embedding: {str(e)}"
        )


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.
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
            validated_texts.append(".")  # Use placeholder for empty texts
        elif len(text) > MAX_EMBEDDING_INPUT_LENGTH:
            logger.warning(f"Text at index {i} length {len(text)} exceeds max, truncating")
            validated_texts.append(text[:MAX_EMBEDDING_INPUT_LENGTH])
        else:
            validated_texts.append(text)

    try:
        embeddings: List[List[float]] = []
        texts_to_generate: List[int] = []  # Indices of texts not in cache
        
        # Check cache for each text
        for i, text in enumerate(validated_texts):
            cached = get_cached_embedding(text)
            if cached:
                embeddings.append(cached)  # type: ignore
            else:
                embeddings.append([])  # Placeholder
                texts_to_generate.append(i)
        
        # If all cached, return early
        if not texts_to_generate:
            logger.debug(f"All {len(validated_texts)} embeddings from cache")
            return embeddings
        
        # Generate missing embeddings in batch
        texts_batch = [validated_texts[i] for i in texts_to_generate]
        logger.debug(f"Generating {len(texts_batch)} embeddings from {len(validated_texts)} total")
        
        generated = []
        
        # Option 1: Voyage AI (Recommended - Anthropic-owned)
        if VOYAGE_API_KEY:
            import voyageai

            vo = voyageai.Client(api_key=VOYAGE_API_KEY)
            result = vo.embed(
                texts_batch,
                model=EMBEDDING_MODEL,
                input_type="document"
            )
            generated = result.embeddings  # type: ignore

        # Option 2: OpenAI
        elif OPENAI_API_KEY:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.embeddings.create(
                input=texts_batch,
                model="text-embedding-ada-002"
            )
            generated = [item.embedding for item in response.data]  # type: ignore

        # Option 3: Cohere
        elif COHERE_API_KEY:
            import cohere

            co = cohere.Client(COHERE_API_KEY)
            response = co.embed(
                texts=texts_batch,
                model="embed-english-v3.0",
                input_type="search_document"
            )
            generated = response.embeddings  # type: ignore

        else:
            raise HTTPException(
                status_code=500,
                detail="No embedding provider configured. Please set VOYAGE_API_KEY, OPENAI_API_KEY, or COHERE_API_KEY."
            )

        # Insert generated embeddings into result and cache them
        for i, gen_idx in enumerate(texts_to_generate):
            embedding = generated[i]
            embeddings[gen_idx] = embedding
            cache_embedding(validated_texts[gen_idx], embedding)
        
        return embeddings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}"
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
            # Look for sentence endings
            for delimiter in ['\n\n', '\n', '. ', '! ', '? ']:
                last_delim = text[start:end].rfind(delimiter)
                if last_delim != -1:
                    end = start + last_delim + len(delimiter)
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks

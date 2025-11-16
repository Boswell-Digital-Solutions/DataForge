import os
from typing import List
import logging
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

from app.config import (
    MAX_EMBEDDING_INPUT_LENGTH,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    VOYAGE_API_KEY,
    COHERE_API_KEY
)

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using configured provider.

    By default, uses OpenAI's text-embedding-ada-002 model.
    Uncomment alternative providers as needed.

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

    try:
        # Option 1: OpenAI (Default - Recommended)
        if OPENAI_API_KEY:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL
            )
            return response.data[0].embedding
        else:
            raise HTTPException(
                status_code=500,
                detail="No embedding provider configured. Please set OPENAI_API_KEY."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embedding: {str(e)}"
        )

    # Option 2: Voyage AI
    # import voyageai
    # vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    # result = vo.embed([text], model="voyage-large-2", input_type="document")
    # return result.embeddings[0]

    # Option 3: Cohere
    # import cohere
    # co = cohere.Client(os.getenv("COHERE_API_KEY"))
    # response = co.embed(texts=[text], model="embed-english-v3.0", input_type="search_document")
    # return response.embeddings[0]

    # Option 4: Local model (sentence-transformers)
    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('all-MiniLM-L6-v2')
    # embedding = model.encode(text)
    # return embedding.tolist()

async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.
    More efficient than calling generate_embedding multiple times.

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
        # Option 1: OpenAI (Default)
        if OPENAI_API_KEY:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.embeddings.create(
                input=validated_texts,
                model=EMBEDDING_MODEL
            )
            return [item.embedding for item in response.data]
        else:
            raise HTTPException(
                status_code=500,
                detail="No embedding provider configured. Please set OPENAI_API_KEY."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}"
        )

    # For other providers, implement batch processing similarly

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

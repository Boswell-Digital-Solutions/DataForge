from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
import logging
from app.models import models, schemas
from app.utils.embeddings import generate_embedding
from app.config import MAX_SEARCH_LIMIT

logger = logging.getLogger(__name__)

async def semantic_search(
    db: Session,
    query: str,
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> schemas.SearchResponse:
    """
    Perform semantic search using vector similarity.

    Args:
        db: Database session
        query: Search query text
        domain_id: Optional domain filter
        tags: Optional tag filters
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score (0-1)

    Returns:
        SearchResponse with ranked results
    """
    # Validate and cap limit
    if limit > MAX_SEARCH_LIMIT:
        logger.warning(f"Search limit {limit} exceeds maximum {MAX_SEARCH_LIMIT}, capping to max")
        limit = MAX_SEARCH_LIMIT

    # Generate embedding for the query
    query_embedding = await generate_embedding(query)

    # Build the base query with proper pgvector cosine distance
    # cosine_distance returns 0-2, where 0 is identical and 2 is opposite
    # We convert to similarity score (1 - distance) so higher is better
    similarity = (1 - models.Chunk.embedding.cosine_distance(query_embedding)).label("similarity")

    query_obj = (
        db.query(
            models.Chunk,
            models.Document,
            similarity
        )
        .join(models.Document, models.Chunk.document_id == models.Document.id)
        .options(joinedload(models.Document.tags))  # Fix N+1 query
        .filter(models.Document.is_published == True)
    )

    # Apply filters
    if domain_id:
        query_obj = query_obj.filter(models.Document.domain_id == domain_id)

    if tags:
        # Filter by tags
        query_obj = query_obj.join(models.Document.tags).filter(
            models.Tag.name.in_(tags)
        )

    # Apply similarity threshold and order by similarity
    results = (
        query_obj
        .filter(similarity >= similarity_threshold)
        .order_by(similarity.desc())
        .limit(limit)
        .all()
    )

    # Format results
    search_results = []
    for chunk, document, sim_score in results:
        search_results.append(
            schemas.SearchResult(
                id=chunk.id,
                content=chunk.content,
                similarity_score=float(sim_score),
                document_id=document.id,
                document_title=document.title,
                document_domain_id=document.domain_id,
                document_tags=[tag.name for tag in document.tags]
            )
        )

    return schemas.SearchResponse(
        query=query,
        total_results=len(search_results),
        chunks=search_results
    )

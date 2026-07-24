from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Tuple
import logging
import time
import uuid
from fastapi import HTTPException
from app.models import models, schemas
from app.telemetry_client import telemetry
from app.utils.embeddings import generate_embedding
from app.config import MAX_SEARCH_LIMIT

logger = logging.getLogger(__name__)


def _is_postgres_backend(db: Session) -> bool:
    bind = db.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _fallback_search(
    db: Session,
    query: str,
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> schemas.SearchResponse:
    """
    Graceful fallback for non-PostgreSQL test backends.

    SQLite test fixtures do not support pgvector or PostgreSQL full-text search
    operators, so fall back to a simple text match query that preserves the
    response shape and filtering behavior.
    """
    pattern = f"%{query.lower()}%"

    query_obj = (
        db.query(models.Chunk, models.Document)
        .join(models.Document, models.Chunk.document_id == models.Document.id)
        .options(joinedload(models.Document.tags))
        .filter(models.Document.is_published.is_(True))
        .filter(
            or_(
                func.lower(models.Chunk.content).like(pattern),
                func.lower(models.Document.title).like(pattern),
                func.lower(models.Document.content).like(pattern),
            )
        )
    )

    if domain_id:
        query_obj = query_obj.filter(models.Document.domain_id == domain_id)

    if tags:
        query_obj = query_obj.join(models.Document.tags).filter(models.Tag.name.in_(tags))

    results = query_obj.limit(limit).all()

    search_results = [
        schemas.SearchResult(
            id=chunk.id,
            content=chunk.content,
            similarity_score=1.0,
            document_id=document.id,
            document_title=document.title,
            document_domain_id=document.domain_id,
            document_tags=[tag.name for tag in document.tags],
        )
        for chunk, document in results
    ]

    return schemas.SearchResponse(
        query=query,
        total_results=len(search_results),
        chunks=search_results,
    )

async def semantic_search(
    db: Session,
    query: str,
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
    similarity_threshold: float = 0.7,
    correlation_id: Optional[uuid.UUID] = None
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
        correlation_id: Optional correlation ID for distributed tracing

    Returns:
        SearchResponse with ranked results
    """
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = uuid.uuid4()

    start_time = time.time()

    try:
        # Validate and cap limit
        if limit > MAX_SEARCH_LIMIT:
            logger.warning(f"Search limit {limit} exceeds maximum {MAX_SEARCH_LIMIT}, capping to max")
            limit = MAX_SEARCH_LIMIT

        if not _is_postgres_backend(db):
            logger.info("Using fallback semantic search for non-PostgreSQL backend")
            response = _fallback_search(
                db=db,
                query=query,
                domain_id=domain_id,
                tags=tags,
                limit=limit,
            )
            await telemetry.emit_search(
                search_kind="semantic",
                succeeded=True,
                correlation_id=correlation_id,
                metrics={
                    "duration_ms": (time.time() - start_time) * 1000,
                    "results_count": response.total_results,
                },
            )
            return response

        # Generate embedding for the query
        embedding_start = time.time()
        query_embedding = await generate_embedding(query)
        embedding_duration_ms = (time.time() - embedding_start) * 1000

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
            .filter(models.Document.is_published.is_(True))
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
        db_query_start = time.time()
        results = (
            query_obj
            .filter(similarity >= similarity_threshold)
            .order_by(similarity.desc())
            .limit(limit)
            .all()
        )
        db_query_duration_ms = (time.time() - db_query_start) * 1000

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

        # Calculate total duration
        total_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="semantic",
            succeeded=True,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": total_duration_ms,
                "embedding_duration_ms": embedding_duration_ms,
                "db_query_duration_ms": db_query_duration_ms,
                "results_count": len(search_results),
                "avg_similarity": sum(r.similarity_score for r in search_results) / len(search_results) if search_results else 0,
            },
        )

        logger.info(f"Search completed: {len(search_results)} results in {total_duration_ms:.2f}ms [correlation_id={correlation_id}]")

        return schemas.SearchResponse(
            query=query,
            total_results=len(search_results),
            chunks=search_results
        )

    except Exception as e:
        # Calculate duration even on error
        error_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="semantic",
            succeeded=False,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": error_duration_ms,
            },
        )

        logger.error(f"Search failed: {e} [correlation_id={correlation_id}]")
        raise


async def keyword_search(
    db: Session,
    query: str,
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
    min_rank: float = 0.01,
    correlation_id: Optional[uuid.UUID] = None
) -> schemas.SearchResponse:
    """
    Perform keyword search using PostgreSQL full-text search with BM25-style ranking.

    Args:
        db: Database session
        query: Search query text
        domain_id: Optional domain filter
        tags: Optional tag filters
        limit: Maximum number of results
        min_rank: Minimum ts_rank score (filters out very weak matches)
        correlation_id: Optional correlation ID for distributed tracing

    Returns:
        SearchResponse with ranked results
    """
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = uuid.uuid4()

    start_time = time.time()

    try:
        # Validate and cap limit
        if limit > MAX_SEARCH_LIMIT:
            logger.warning(f"Search limit {limit} exceeds maximum {MAX_SEARCH_LIMIT}, capping to max")
            limit = MAX_SEARCH_LIMIT

        if not _is_postgres_backend(db):
            logger.info("Using fallback keyword search for non-PostgreSQL backend")
            response = _fallback_search(
                db=db,
                query=query,
                domain_id=domain_id,
                tags=tags,
                limit=limit,
            )
            await telemetry.emit_search(
                search_kind="keyword",
                succeeded=True,
                correlation_id=correlation_id,
                metrics={
                    "duration_ms": (time.time() - start_time) * 1000,
                    "results_count": response.total_results,
                },
            )
            return response

        # Create search query for PostgreSQL full-text search
        # websearch_to_tsquery handles "quoted phrases" and AND/OR operators
        tsquery = func.websearch_to_tsquery('english', query)

        # Use ts_rank_cd for BM25-style ranking with document length normalization
        # Normalization flag 1 divides by document length (similar to BM25)
        rank = func.ts_rank_cd(models.Chunk.search_vector, tsquery, 1).label("rank")

        # Build the base query
        query_obj = (
            db.query(
                models.Chunk,
                models.Document,
                rank
            )
            .join(models.Document, models.Chunk.document_id == models.Document.id)
            .options(joinedload(models.Document.tags))  # Fix N+1 query
            .filter(models.Document.is_published.is_(True))
            .filter(models.Chunk.search_vector.op('@@')(tsquery))  # Full-text match
        )

        # Apply filters
        if domain_id:
            query_obj = query_obj.filter(models.Document.domain_id == domain_id)

        if tags:
            query_obj = query_obj.join(models.Document.tags).filter(
                models.Tag.name.in_(tags)
            )

        # Execute query with rank threshold
        db_query_start = time.time()
        results = (
            query_obj
            .filter(rank >= min_rank)
            .order_by(rank.desc())
            .limit(limit)
            .all()
        )
        db_query_duration_ms = (time.time() - db_query_start) * 1000

        # Format results
        search_results = []
        for chunk, document, rank_score in results:
            search_results.append(
                schemas.SearchResult(
                    id=chunk.id,
                    content=chunk.content,
                    similarity_score=float(rank_score),  # Use rank as score
                    document_id=document.id,
                    document_title=document.title,
                    document_domain_id=document.domain_id,
                    document_tags=[tag.name for tag in document.tags]
                )
            )

        # Calculate total duration
        total_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="keyword",
            succeeded=True,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": total_duration_ms,
                "db_query_duration_ms": db_query_duration_ms,
                "results_count": len(search_results),
                "avg_rank": sum(r.similarity_score for r in search_results) / len(search_results) if search_results else 0,
            },
        )

        logger.info(f"Keyword search completed: {len(search_results)} results in {total_duration_ms:.2f}ms [correlation_id={correlation_id}]")

        return schemas.SearchResponse(
            query=query,
            total_results=len(search_results),
            chunks=search_results
        )

    except Exception as e:
        error_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="keyword",
            succeeded=False,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": error_duration_ms,
            },
        )

        logger.error(f"Keyword search failed: {e} [correlation_id={correlation_id}]")
        raise


def _reciprocal_rank_fusion(
    results_list: List[List[Tuple[int, float]]],
    k: int = 60
) -> List[Tuple[int, float]]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion (RRF).

    RRF formula: score(chunk) = sum(1 / (k + rank_i)) for each list i
    where rank_i is the position of chunk in list i (1-indexed)

    Args:
        results_list: List of ranked result lists, each containing (chunk_id, score) tuples
        k: Constant to reduce impact of high rankings (default 60, from RRF paper)

    Returns:
        Combined ranked list of (chunk_id, rrf_score) tuples
    """
    # Calculate RRF scores
    rrf_scores: Dict[int, float] = {}

    for results in results_list:
        for rank, (chunk_id, _) in enumerate(results, start=1):
            # RRF formula: 1 / (k + rank)
            rrf_score = 1.0 / (k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + rrf_score

    # Sort by RRF score (descending)
    ranked_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    return ranked_results


async def hybrid_search(
    db: Session,
    query: str,
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
    similarity_threshold: float = 0.7,
    min_rank: float = 0.01,
    correlation_id: Optional[uuid.UUID] = None
) -> schemas.SearchResponse:
    """
    Perform hybrid search combining semantic (vector) and keyword (BM25) search.

    Uses Reciprocal Rank Fusion (RRF) to combine results from both search methods,
    providing better recall and relevance than either method alone.

    Args:
        db: Database session
        query: Search query text
        domain_id: Optional domain filter
        tags: Optional tag filters
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score for semantic search
        min_rank: Minimum ts_rank score for keyword search
        correlation_id: Optional correlation ID for distributed tracing

    Returns:
        SearchResponse with RRF-ranked results
    """
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = uuid.uuid4()

    start_time = time.time()

    try:
        # Validate and cap limit
        if limit > MAX_SEARCH_LIMIT:
            logger.warning(f"Search limit {limit} exceeds maximum {MAX_SEARCH_LIMIT}, capping to max")
            limit = MAX_SEARCH_LIMIT

        if not _is_postgres_backend(db):
            logger.info("Using fallback hybrid search for non-PostgreSQL backend")
            response = _fallback_search(
                db=db,
                query=query,
                domain_id=domain_id,
                tags=tags,
                limit=limit,
            )
            await telemetry.emit_search(
                search_kind="hybrid",
                succeeded=True,
                correlation_id=correlation_id,
                metrics={
                    "duration_ms": (time.time() - start_time) * 1000,
                    "results_count": response.total_results,
                },
            )
            return response

        # Fetch more results from each method to ensure good coverage for RRF
        fetch_limit = limit * 3  # Fetch 3x limit from each method

        # Perform semantic search
        semantic_start = time.time()
        try:
            semantic_response = await semantic_search(
                db=db,
                query=query,
                domain_id=domain_id,
                tags=tags,
                limit=fetch_limit,
                similarity_threshold=similarity_threshold,
                correlation_id=correlation_id
            )
        except HTTPException as exc:
            if exc.status_code not in {502, 503, 504}:
                raise
            logger.warning(
                "Hybrid search degrading to fallback search because semantic search is unavailable: %s",
                exc.detail,
            )
            response = _fallback_search(
                db=db,
                query=query,
                domain_id=domain_id,
                tags=tags,
                limit=limit,
            )
            await telemetry.emit_search(
                search_kind="hybrid",
                succeeded=True,
                correlation_id=correlation_id,
                metrics={
                    "duration_ms": (time.time() - start_time) * 1000,
                    "results_count": response.total_results,
                },
            )
            return response
        semantic_duration_ms = (time.time() - semantic_start) * 1000

        # Perform keyword search
        keyword_start = time.time()
        keyword_response = await keyword_search(
            db=db,
            query=query,
            domain_id=domain_id,
            tags=tags,
            limit=fetch_limit,
            min_rank=min_rank,
            correlation_id=correlation_id
        )
        keyword_duration_ms = (time.time() - keyword_start) * 1000

        # Prepare ranked lists for RRF
        semantic_list = [(r.id, r.similarity_score) for r in semantic_response.chunks]
        keyword_list = [(r.id, r.similarity_score) for r in keyword_response.chunks]

        # Apply Reciprocal Rank Fusion
        rrf_start = time.time()
        rrf_results = _reciprocal_rank_fusion([semantic_list, keyword_list])
        rrf_duration_ms = (time.time() - rrf_start) * 1000

        # Get top-k results after RRF
        top_chunk_ids = [chunk_id for chunk_id, _ in rrf_results[:limit]]

        # Fetch full chunk details in order
        if top_chunk_ids:
            # Create a mapping of chunk_id to RRF score
            rrf_score_map = {chunk_id: score for chunk_id, score in rrf_results[:limit]}

            # Fetch chunks with document info
            chunks_query = (
                db.query(models.Chunk, models.Document)
                .join(models.Document, models.Chunk.document_id == models.Document.id)
                .options(joinedload(models.Document.tags))
                .filter(models.Chunk.id.in_(top_chunk_ids))
                .all()
            )

            # Create a mapping of chunk_id to (chunk, document)
            chunk_map = {chunk.id: (chunk, document) for chunk, document in chunks_query}

            # Build results in RRF order
            search_results = []
            for chunk_id in top_chunk_ids:
                if chunk_id in chunk_map:
                    chunk, document = chunk_map[chunk_id]
                    search_results.append(
                        schemas.SearchResult(
                            id=chunk.id,
                            content=chunk.content,
                            similarity_score=rrf_score_map[chunk_id],  # Use RRF score
                            document_id=document.id,
                            document_title=document.title,
                            document_domain_id=document.domain_id,
                            document_tags=[tag.name for tag in document.tags]
                        )
                    )
        else:
            search_results = []

        # Calculate total duration
        total_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="hybrid",
            succeeded=True,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": total_duration_ms,
                "semantic_duration_ms": semantic_duration_ms,
                "keyword_duration_ms": keyword_duration_ms,
                "rrf_duration_ms": rrf_duration_ms,
                "results_count": len(search_results),
                "semantic_results": len(semantic_list),
                "keyword_results": len(keyword_list),
                "avg_rrf_score": sum(r.similarity_score for r in search_results) / len(search_results) if search_results else 0,
            },
        )

        logger.info(
            f"Hybrid search completed: {len(search_results)} results in {total_duration_ms:.2f}ms "
            f"(semantic: {len(semantic_list)}, keyword: {len(keyword_list)}) [correlation_id={correlation_id}]"
        )

        return schemas.SearchResponse(
            query=query,
            total_results=len(search_results),
            chunks=search_results
        )

    except Exception as e:
        error_duration_ms = (time.time() - start_time) * 1000

        await telemetry.emit_search(
            search_kind="hybrid",
            succeeded=False,
            correlation_id=correlation_id,
            metrics={
                "duration_ms": error_duration_ms,
            },
        )

        logger.error(f"Hybrid search failed: {e} [correlation_id={correlation_id}]")
        raise

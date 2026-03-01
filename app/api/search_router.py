from fastapi import APIRouter, Depends, Request, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from app.database import get_db
from app.models import schemas
from app.api import search, crud
from app.utils.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/search", tags=["search"])


def search_rate_limit(request: Request):
    """Rate limit for search endpoint: 20 requests per minute"""
    return check_rate_limit(request, max_requests=20, window_seconds=60)


def stats_rate_limit(request: Request):
    """Rate limit for stats endpoint: 10 requests per minute"""
    return check_rate_limit(request, max_requests=10, window_seconds=60)


@router.post("/semantic", response_model=schemas.SearchResponse)
async def semantic_search_endpoint(
    search_request: schemas.SearchRequest,
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(search_rate_limit),
    x_correlation_id: Optional[str] = Header(None)
):
    """
    Semantic search endpoint using vector similarity.

    Search the knowledge base using semantic similarity (embeddings).
    No authentication required.

    Rate limit: 20 requests per minute per IP address.

    Headers:
        X-Correlation-ID: Optional correlation ID for distributed tracing
    """
    # Use provided correlation ID or generate new one
    correlation_id = None
    if x_correlation_id:
        try:
            correlation_id = uuid.UUID(x_correlation_id)
        except ValueError:
            # Invalid UUID format, generate new one
            correlation_id = uuid.uuid4()
    else:
        correlation_id = uuid.uuid4()

    return await search.semantic_search(
        db=db,
        query=search_request.query,
        domain_id=search_request.domain_id,
        tags=search_request.tags,
        limit=search_request.limit,
        similarity_threshold=search_request.similarity_threshold,
        correlation_id=correlation_id
    )


@router.post("/keyword", response_model=schemas.SearchResponse)
async def keyword_search_endpoint(
    search_request: schemas.SearchRequest,
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(search_rate_limit),
    x_correlation_id: Optional[str] = Header(None)
):
    """
    Keyword search endpoint using PostgreSQL full-text search.

    Search the knowledge base using BM25-style keyword matching.
    No authentication required.

    Rate limit: 20 requests per minute per IP address.

    Headers:
        X-Correlation-ID: Optional correlation ID for distributed tracing
    """
    # Use provided correlation ID or generate new one
    correlation_id = None
    if x_correlation_id:
        try:
            correlation_id = uuid.UUID(x_correlation_id)
        except ValueError:
            # Invalid UUID format, generate new one
            correlation_id = uuid.uuid4()
    else:
        correlation_id = uuid.uuid4()

    return await search.keyword_search(
        db=db,
        query=search_request.query,
        domain_id=search_request.domain_id,
        tags=search_request.tags,
        limit=search_request.limit,
        min_rank=0.01,  # Default minimum rank threshold
        correlation_id=correlation_id
    )


@router.post("/hybrid", response_model=schemas.SearchResponse)
@router.post("", response_model=schemas.SearchResponse)  # Default endpoint
async def hybrid_search_endpoint(
    search_request: schemas.SearchRequest,
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(search_rate_limit),
    x_correlation_id: Optional[str] = Header(None)
):
    """
    Hybrid search endpoint combining semantic and keyword search.

    Search the knowledge base using both semantic (vector) and keyword (BM25) search,
    then combines results using Reciprocal Rank Fusion (RRF) for optimal relevance.
    This is the recommended default search method.

    No authentication required.

    Rate limit: 20 requests per minute per IP address.

    Headers:
        X-Correlation-ID: Optional correlation ID for distributed tracing
    """
    # Use provided correlation ID or generate new one
    correlation_id = None
    if x_correlation_id:
        try:
            correlation_id = uuid.UUID(x_correlation_id)
        except ValueError:
            # Invalid UUID format, generate new one
            correlation_id = uuid.uuid4()
    else:
        correlation_id = uuid.uuid4()

    return await search.hybrid_search(
        db=db,
        query=search_request.query,
        domain_id=search_request.domain_id,
        tags=search_request.tags,
        limit=search_request.limit,
        similarity_threshold=search_request.similarity_threshold,
        min_rank=0.01,  # Default minimum rank threshold
        correlation_id=correlation_id
    )


@router.get("", response_model=schemas.SearchResponse)
async def hybrid_search_legacy_get(
    q: Optional[str] = Query(None, alias="q"),
    query: Optional[str] = Query(None),
    domain_id: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    limit: int = 5,
    similarity_threshold: float = 0.7,
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(search_rate_limit),
    x_correlation_id: Optional[str] = Header(None),
):
    """Legacy compatibility GET endpoint for hybrid search."""
    search_query = q or query
    if not search_query:
        search_query = ""

    correlation_id = None
    if x_correlation_id:
        try:
            correlation_id = uuid.UUID(x_correlation_id)
        except ValueError:
            correlation_id = uuid.uuid4()
    else:
        correlation_id = uuid.uuid4()

    return await search.hybrid_search(
        db=db,
        query=search_query,
        domain_id=domain_id,
        tags=tags,
        limit=limit,
        similarity_threshold=similarity_threshold,
        min_rank=0.01,
        correlation_id=correlation_id,
    )


@router.get("/stats", response_model=schemas.Stats)
def get_search_stats(
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(stats_rate_limit)
):
    """
    Get knowledge base statistics.
    No authentication required.

    Rate limit: 10 requests per minute per IP address.
    """
    return crud.get_stats(db)

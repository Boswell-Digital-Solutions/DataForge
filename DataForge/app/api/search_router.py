from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
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


@router.post("", response_model=schemas.SearchResponse)
async def search_knowledge_base(
    search_request: schemas.SearchRequest,
    db: Session = Depends(get_db),
    request: Request = None,
    rate_limit: None = Depends(search_rate_limit),
    x_correlation_id: Optional[str] = Header(None)
):
    """
    Public semantic search endpoint.

    Search the knowledge base using semantic similarity.
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

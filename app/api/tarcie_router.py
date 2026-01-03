"""
Tarcie ingest endpoint.

POST /ingest/tarcie - Receives batch events from Tarcie flush.

No enrichment. No analysis. Just persist.
SMITH does downstream processing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tarcie_schemas import (
    TarcieIngestRequest,
    TarcieIngestResponse,
)
from app.services.tarcie_service import TarcieService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ingest/tarcie",
    tags=["Tarcie Ingest"],
)


@router.post(
    "",
    response_model=TarcieIngestResponse,
    status_code=201,
    summary="Ingest Tarcie events",
    description="Receives batch of friction notes and markers from Tarcie. Append-only storage.",
)
async def ingest_events(
    request: TarcieIngestRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> TarcieIngestResponse:
    """
    Ingest events from Tarcie.

    Accepts batch payloads from Tarcie's background flusher.
    Idempotent: duplicate event IDs are skipped.
    """
    # Log incoming request
    client_host = http_request.client.host if http_request.client else "unknown"
    logger.info(
        "tarcie_ingest_request",
        extra={
            "source": request.source,
            "event_count": len(request.events),
            "client_host": client_host,
        },
    )

    # Validate source
    if request.source != "tarcie":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: expected 'tarcie', got '{request.source}'",
        )

    try:
        service = TarcieService(db)
        result = service.ingest_batch(request)
        return result

    except Exception as e:
        logger.exception("tarcie_ingest_failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Ingest failed: {str(e)}",
        )


@router.get(
    "/health",
    summary="Tarcie ingest health check",
    description="Returns OK if the ingest endpoint is operational.",
)
async def health() -> dict:
    """Health check for Tarcie ingest endpoint."""
    return {"status": "ok", "endpoint": "tarcie_ingest"}

"""
NeuroForge API Router

Endpoints for inference logging, routing decisions, and transparency.
Service-to-service — no user auth required.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.neuroforge_schemas import (
    InferenceCreate,
    InferenceResponse,
    InferenceListResponse,
    InferenceStats,
    RoutingDecisionCreate,
    RoutingDecisionResponse,
    RoutingDecisionListResponse,
)
from app.api import neuroforge_crud as crud

router = APIRouter(prefix="/api/neuroforge", tags=["neuroforge"])


@router.post("/inferences", response_model=InferenceResponse, status_code=status.HTTP_201_CREATED)
def create_inference(
    data: InferenceCreate,
    db: Session = Depends(get_db),
):
    """Log a new AI inference record."""
    return crud.create_inference(db, data)


@router.get("/inferences", response_model=InferenceListResponse)
def list_inferences(
    domain: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    inference_status: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List inferences with optional filters."""
    items, total = crud.list_inferences(
        db,
        domain=domain,
        task_type=task_type,
        model_id=model_id,
        status=inference_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return InferenceListResponse(items=items, total=total)


@router.get("/inferences/{inference_id}", response_model=InferenceResponse)
def get_inference(
    inference_id: str,
    db: Session = Depends(get_db),
):
    """Get a single inference record."""
    row = crud.get_inference(db, inference_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inference not found")
    return row


@router.get("/stats", response_model=InferenceStats)
def get_inference_stats(
    domain: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregate inference statistics."""
    return crud.get_inference_stats(db, domain=domain, date_from=date_from, date_to=date_to)


# ── Routing Decisions ──────────────────────────────────────


@router.post("/routing-decisions", response_model=RoutingDecisionResponse, status_code=status.HTTP_201_CREATED)
def create_routing_decision(
    data: RoutingDecisionCreate,
    db: Session = Depends(get_db),
):
    """Log a routing decision from NeuroForge."""
    return crud.create_routing_decision(db, data)


@router.get("/routing-decisions", response_model=RoutingDecisionListResponse)
def list_routing_decisions(
    task_type: Optional[str] = Query(None),
    selected_provider: Optional[str] = Query(None),
    selected_tier: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List routing decisions with optional filters."""
    items, total = crud.list_routing_decisions(
        db,
        task_type=task_type,
        selected_provider=selected_provider,
        selected_tier=selected_tier,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return RoutingDecisionListResponse(items=items, total=total)

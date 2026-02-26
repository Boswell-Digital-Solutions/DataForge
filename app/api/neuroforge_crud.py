"""
CRUD operations for NeuroForge inference tracking and routing decisions.

Service-to-service endpoints — no user-ownership checks needed.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, and_
from typing import Optional, Tuple, List, Dict
from datetime import datetime

from app.models.neuroforge_models import Inference, RoutingDecision
from app.models.neuroforge_schemas import InferenceCreate, RoutingDecisionCreate


def create_inference(db: Session, data: InferenceCreate) -> Inference:
    """Insert a new inference record."""
    row = Inference(
        inference_id=data.inference_id,
        domain=data.domain,
        task_type=data.task_type,
        context_pack_id=data.context_pack_id,
        user_query=data.user_query[:10000],
        model_id=data.model_id,
        model_provider=data.model_provider,
        output=(data.output or "")[:16000],
        tokens_used=data.tokens_used,
        evaluation_score=data.evaluation_score,
        evaluation_passed=data.evaluation_passed,
        evaluation_details=data.evaluation_details,
        latency_ms=data.latency_ms,
        status=data.status,
        error_message=data.error_message,
        completed_at=datetime.utcnow() if data.status == "completed" else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_inference(db: Session, inference_id: str) -> Optional[Inference]:
    """Get a single inference by ID."""
    return db.query(Inference).filter(Inference.inference_id == inference_id).first()


def list_inferences(
    db: Session,
    domain: Optional[str] = None,
    task_type: Optional[str] = None,
    model_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Inference], int]:
    """List inferences with optional filters. Returns (items, total_count)."""
    query = db.query(Inference)

    if domain:
        query = query.filter(Inference.domain == domain)
    if task_type:
        query = query.filter(Inference.task_type == task_type)
    if model_id:
        query = query.filter(Inference.model_id == model_id)
    if status:
        query = query.filter(Inference.status == status)
    if date_from:
        query = query.filter(Inference.created_at >= date_from)
    if date_to:
        query = query.filter(Inference.created_at <= date_to)

    total = query.count()
    items = query.order_by(Inference.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def get_inference_stats(
    db: Session,
    domain: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict:
    """Get aggregate inference statistics."""
    query = db.query(Inference)

    if domain:
        query = query.filter(Inference.domain == domain)
    if date_from:
        query = query.filter(Inference.created_at >= date_from)
    if date_to:
        query = query.filter(Inference.created_at <= date_to)

    # Aggregates
    total = query.count()
    tokens_sum = query.with_entities(
        sql_func.coalesce(sql_func.sum(Inference.tokens_used), 0)
    ).scalar()
    avg_latency = query.with_entities(
        sql_func.coalesce(sql_func.avg(Inference.latency_ms), 0)
    ).scalar()

    # Per-domain breakdown
    domain_rows = (
        query.with_entities(
            Inference.domain,
            sql_func.count().label("count"),
            sql_func.coalesce(sql_func.sum(Inference.tokens_used), 0).label("tokens"),
        )
        .group_by(Inference.domain)
        .all()
    )

    by_domain = {}
    for row in domain_rows:
        by_domain[row[0]] = {"count": row[1], "tokens": int(row[2])}

    return {
        "total_inferences": total,
        "total_tokens": int(tokens_sum),
        "average_latency_ms": round(float(avg_latency), 1),
        "by_domain": by_domain,
    }


# ── Routing Decisions ──────────────────────────────────────


def create_routing_decision(db: Session, data: RoutingDecisionCreate) -> RoutingDecision:
    """Insert a new routing decision record."""
    row = RoutingDecision(
        request_id=data.request_id,
        task_type=data.task_type,
        selected_provider=data.selected_provider,
        selected_model=data.selected_model,
        selected_tier=data.selected_tier,
        reasons=data.reasons,
        fallback_chain=data.fallback_chain,
        rejected=data.rejected,
        latency_ms=data.latency_ms,
        cost_estimate=data.cost_estimate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_routing_decisions(
    db: Session,
    task_type: Optional[str] = None,
    selected_provider: Optional[str] = None,
    selected_tier: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[RoutingDecision], int]:
    """List routing decisions with optional filters. Returns (items, total_count)."""
    query = db.query(RoutingDecision)

    if task_type:
        query = query.filter(RoutingDecision.task_type == task_type)
    if selected_provider:
        query = query.filter(RoutingDecision.selected_provider == selected_provider)
    if selected_tier:
        query = query.filter(RoutingDecision.selected_tier == selected_tier)
    if date_from:
        query = query.filter(RoutingDecision.created_at >= date_from)
    if date_to:
        query = query.filter(RoutingDecision.created_at <= date_to)

    total = query.count()
    items = query.order_by(RoutingDecision.created_at.desc()).offset(offset).limit(limit).all()
    return items, total

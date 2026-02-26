"""
NeuroForge Database Models

SQLAlchemy ORM for the inferences table (created by migration 20251216_1901)
and routing_decisions table (created by migration routing_decisions_001).
Used for AI transparency logging — tracking every LLM inference and routing
decision across the system.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, Numeric,
    DateTime, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4

from app.database import Base


class Inference(Base):
    __tablename__ = "inferences"

    inference_id = Column(String(36), primary_key=True)
    domain = Column(String(50), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    context_pack_id = Column(String(256), nullable=False, server_default="")
    user_query = Column(String(10000), nullable=False)
    model_id = Column(String(256), nullable=False, index=True)
    model_provider = Column(String(50), nullable=False)
    output = Column(String(16000), nullable=True)
    tokens_used = Column(Integer, nullable=True, server_default="0")
    evaluation_score = Column(Float, nullable=True)
    evaluation_passed = Column(Boolean, nullable=True, server_default="false")
    evaluation_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True, server_default="pending", index=True)
    error_message = Column(String(1000), nullable=True)


class RoutingDecision(Base):
    """Routing decision audit log — every model routing decision persisted for transparency."""
    __tablename__ = "routing_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id = Column(String(128), nullable=False)
    task_type = Column(String(64), nullable=False, index=True)
    selected_provider = Column(String(32), nullable=False, index=True)
    selected_model = Column(String(128), nullable=False)
    selected_tier = Column(String(20), nullable=False)
    reasons = Column(JSONB, nullable=False)
    fallback_chain = Column(JSONB, nullable=False, server_default="[]")
    rejected = Column(JSONB, nullable=False, server_default="{}")
    latency_ms = Column(Numeric(10, 2), nullable=True)
    cost_estimate = Column(Numeric(10, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

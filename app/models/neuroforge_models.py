"""
NeuroForge Database Models

SQLAlchemy ORM for the inferences table (created by migration 20251216_1901).
Used for AI transparency logging — tracking every LLM inference across the system.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, JSON
)
from sqlalchemy.sql import func

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

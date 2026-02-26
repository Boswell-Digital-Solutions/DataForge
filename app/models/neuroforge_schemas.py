"""
NeuroForge Pydantic Schemas

API request/response models for inference logging and transparency endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# Inference Schemas
# ============================================

class InferenceCreate(BaseModel):
    inference_id: str
    domain: str
    task_type: str
    context_pack_id: str = ""
    user_query: str
    model_id: str
    model_provider: str
    output: Optional[str] = None
    tokens_used: int = 0
    evaluation_score: Optional[float] = None
    evaluation_passed: Optional[bool] = None
    evaluation_details: Optional[Dict[str, Any]] = None
    latency_ms: Optional[int] = None
    status: str = "completed"
    error_message: Optional[str] = None


class InferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inference_id: str
    domain: str
    task_type: str
    context_pack_id: str
    user_query: str
    model_id: str
    model_provider: str
    output: Optional[str] = None
    tokens_used: int
    evaluation_score: Optional[float] = None
    evaluation_passed: Optional[bool] = None
    latency_ms: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class InferenceListResponse(BaseModel):
    items: List[InferenceResponse]
    total: int


# ============================================
# Stats Schemas
# ============================================

class DomainBreakdown(BaseModel):
    count: int
    tokens: int


class InferenceStats(BaseModel):
    total_inferences: int
    total_tokens: int
    average_latency_ms: float
    by_domain: Dict[str, DomainBreakdown]


# ============================================
# Routing Decision Schemas
# ============================================

class RoutingDecisionCreate(BaseModel):
    request_id: str
    task_type: str
    selected_provider: str
    selected_model: str
    selected_tier: str
    reasons: List[str]
    fallback_chain: List[str] = []
    rejected: Dict[str, str] = {}
    latency_ms: Optional[float] = None
    cost_estimate: Optional[float] = None


class RoutingDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    task_type: str
    selected_provider: str
    selected_model: str
    selected_tier: str
    reasons: List[str]
    fallback_chain: List[str]
    rejected: Dict[str, str]
    latency_ms: Optional[float] = None
    cost_estimate: Optional[float] = None
    created_at: datetime


class RoutingDecisionListResponse(BaseModel):
    items: List[RoutingDecisionResponse]
    total: int

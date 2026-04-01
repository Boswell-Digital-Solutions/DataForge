"""
NeuroForge Domain Models

Core models for the inference pipeline.
"""
from typing import Any, Dict, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field


# ============================================================================
# Inference Pipeline Models
# ============================================================================

class InferenceRequest(BaseModel):
    """Request model for inference pipeline."""
    request_id: str  # Unique request identifier
    domain: str  # e.g., "literary", "trading", "generic"
    task_type: str  # e.g., "analysis", "generation", "summary"
    context_pack_id: Optional[str] = None  # Optional DataForge context pack ID
    user_query: str
    additional_context: Optional[str] = None
    max_tokens: int = 2048
    model_override: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BuiltContext(BaseModel):
    """Internally-built context for pipeline execution."""
    context_pack_id: str  # ID from DataForge or local generation
    text_blocks: list[str]  # Concatenated/formatted context snippets
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "dataforge"  # "dataforge", "fallback", "cache"
    cached_at: Optional[datetime] = None
    ttl_seconds: int = 3600


class ModelDecision(BaseModel):
    """Decision made by model router."""
    selected_model_id: str
    confidence: float = 1.0
    ensemble_models: Optional[list[str]] = None
    reasoning: Optional[str] = None


class EvaluationScore(BaseModel):
    """Score from evaluator."""
    metric: str
    score: float  # 0.0 to 1.0
    reasoning: Optional[str] = None


class InferenceResult(BaseModel):
    """Result of inference pipeline execution."""
    inference_id: str
    request_id: str
    status: str  # "success", "partial", "failed"
    output: str  # Final answer text
    model_id: str
    latency_ms: int
    tokens_used: int
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    evaluation_scores: list[EvaluationScore] = Field(default_factory=list)
    model_decision: Optional[ModelDecision] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    context_pack_id: Optional[str] = None  # Reference to DataForge context


# ============================================================================
# Cache Models
# ============================================================================

class CacheEntry(BaseModel):
    """Entry stored in LRU cache."""
    key: str
    value: BuiltContext
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        elapsed = (datetime.now(UTC) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

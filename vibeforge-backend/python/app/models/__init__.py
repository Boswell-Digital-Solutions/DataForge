"""Data models for FastAPI."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import all VibeForge models from dedicated module
from app.models.vibeforge_models import (
    TokenUsageModel,
    ContextBlockModel,
    RunStatusEnum,
    CreateRunRequest,
    ModelRunModel,
    RunHistoryResponse,
)

__all__ = [
    "TokenUsageModel",
    "ContextBlockModel",
    "RunStatusEnum",
    "CreateRunRequest",
    "ModelRunModel",
    "RunHistoryResponse",
    "DocumentModel",
    "CorpusModel",
    "SearchResultModel",
    "ScoreModel",
    "EvaluationModel",
    "SweepConfigModel",
]


# ============================================================================
# DataForge Models (Stub)
# ============================================================================


class DocumentModel(BaseModel):
    """Document for ingestion."""

    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class CorpusModel(BaseModel):
    """Corpus for semantic search."""

    id: str
    name: str
    document_count: int = 0
    created_at: str


class SearchResultModel(BaseModel):
    """Search result item."""

    document_id: str
    content: str
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# NeuroForge Models (Stub)
# ============================================================================


class ScoreModel(BaseModel):
    """Evaluation score."""

    name: str
    value: float
    scale: str = Field(..., description="1-5 | 1-10 | 0-1")


class EvaluationModel(BaseModel):
    """Evaluation of a model run."""

    id: str
    run_id: str
    evaluator: str
    scores: Dict[str, float]
    notes: str = ""
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "eval-123",
                "run_id": "run-789",
                "evaluator": "human",
                "scores": {"accuracy": 4.5, "clarity": 4.8},
                "notes": "Good explanation",
                "created_at": "2025-11-18T10:10:00Z",
            }
        }


class SweepConfigModel(BaseModel):
    """Hyperparameter sweep configuration."""

    id: str
    name: str
    parameters: Dict[str, List[Any]]
    total_runs: int
    completed_runs: int = 0
    created_at: str

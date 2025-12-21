"""
NeuroForge Backend

Cognitive inference engine for the Forge ecosystem.

Architecture:
- ContextBuilder (Stage 1): Fetch context from DataForge
- PromptEngine (Stage 2): Build prompt with context
- ModelRouter (Stage 3): Route to best model
- Evaluator (Stage 4): Score output quality
- PostProcessor (Stage 5): Log provenance to DataForge

This module integrates with DataForge for:
- Context retrieval with caching
- Provenance tracking and logging
- Circuit breaker protection
- Retry resilience
"""

from app.neuroforge.config import (
    NeuroForgeSettings,
    get_settings,
    init_settings,
)
from app.neuroforge.models import (
    InferenceRequest,
    BuiltContext,
    InferenceResult,
    ModelDecision,
    EvaluationScore,
)

__version__ = "1.0.0"
__all__ = [
    "NeuroForgeSettings",
    "get_settings",
    "init_settings",
    "InferenceRequest",
    "BuiltContext",
    "InferenceResult",
    "ModelDecision",
    "EvaluationScore",
]

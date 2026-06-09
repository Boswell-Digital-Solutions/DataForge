"""Model-outcome receipt persistence (DataForge owns durable learning state).

Append-only ground-truth code-fix outcomes — the learning receipts that teach
NeuroForge's (model, category) Category Champion Matrix which model is best for
which kind of fix. DataForge is the durable-truth boundary (NeuroForge is a DB
consumer); the matrix is a replayable projection rebuilt from these rows.

Idempotent per (context_bundle_id, model_id, stage) so a retry never double-counts.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

_JSON = JSON().with_variant(JSONB, "postgresql")


class ModelOutcome(Base):
    """One ground-truth outcome for a (model, routing_cell) generation."""

    __tablename__ = "model_outcomes"

    # deterministic id = hash(context_bundle_id|model_id|stage) -> idempotent receipt
    outcome_id = Column(String(128), primary_key=True)
    context_bundle_id = Column(Text, nullable=False, index=True)
    task_intent_id = Column(Text, nullable=True)
    model_id = Column(Text, nullable=False, index=True)
    tier = Column(Text, nullable=True)
    routing_cell = Column(Text, nullable=False, index=True)
    family = Column(Text, nullable=True)
    kind = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    complexity = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)
    stage = Column(Text, nullable=False)
    reward = Column(Float, nullable=False, default=0.0)
    evidence_json = Column(_JSON, nullable=False, default=list)
    source_system = Column(Text, nullable=False, default="forgehq")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<ModelOutcome {self.outcome_id} {self.model_id} {self.routing_cell} r={self.reward}>"

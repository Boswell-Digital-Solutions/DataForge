"""Context-pack persistence model.

Governed, precomputed context packs for the self-healing AI program. A pack is
the PCC-assembled + pact-verified context for one target, keyed by its
context_bundle_id (``ctxb_...``). NeuroForge's Context Builder fetches a pack by
id (``GET /df/rag/context-pack/{id}``) and serves inference from it instead of
re-grounding — the faster/cheaper-tokens path (precompute + verify once, reuse).

This is the cloud mirror of DataForge-Local's context_packs table; the producer
publishes the same governed pack to both tiers.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

# JSONB on Postgres (prod), generic JSON on sqlite (tests) — both round-trip dict/list.
_JSON = JSON().with_variant(JSONB, "postgresql")


class ContextPack(Base):
    """Precomputed governed context pack, keyed by context_bundle_id."""

    __tablename__ = "context_packs"

    context_pack_id = Column(String(128), primary_key=True)
    bundle_hash = Column(Text, nullable=False)
    task_intent_id = Column(Text, nullable=True, index=True)
    # NeuroForge read contract: pack_data["primary"].
    primary_text = Column(Text, nullable=False, default="")
    # NeuroForge read contract: pack_data["supporting"] (list[str]).
    supporting_json = Column(_JSON, nullable=False, default=list)
    # Governance + provenance: lineage handle, source classes, pact verdict.
    metadata_json = Column(_JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ContextPack {self.context_pack_id} hash={self.bundle_hash}>"

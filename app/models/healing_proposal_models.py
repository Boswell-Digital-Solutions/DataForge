"""Healing proposal store ORM model.

Pending self-healing code-fix proposals (Forge_Command inbox ``LocalEventEnvelope``,
``event_class=proposal``) awaiting operator accept/reject in Forge_Command.

The full envelope is preserved as JSONB; key fields are mirrored for filtering
(the local FC bridge pulls ``status=pending``). On the operator's decision,
``status`` advances (accepted/rejected/applied/failed) and ``decision`` records
the receipt (the learning signal).
"""

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class HealingProposalRecord(Base):
    __tablename__ = "healing_proposals"

    # The proposal id is the inbox envelope's event_id (idempotent ingest key).
    proposal_id = Column(String(64), primary_key=True, index=True)
    source_system = Column(String(64), nullable=False, index=True)
    repo_id = Column(String(128), nullable=True, index=True)
    commit_sha = Column(String(64), nullable=True)
    severity = Column(String(16), nullable=False, index=True)
    schema_version = Column(String(64), nullable=False)
    # pending | ingested | accepted | rejected | applied | failed
    status = Column(String(16), nullable=False, default="pending", index=True)
    envelope = Column(JSONB, nullable=False)
    decision = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

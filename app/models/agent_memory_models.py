"""Agent memory store ORM model.

A generic, agent-writable memory store for the reference agents' long-term and
episodic memory. Distinct from:

* the admin document store (`/admin/documents`) — admin-JWT-gated knowledge base
* the Experience Store (`/api/v1/experience`) — structured execution outcomes

This table holds arbitrary agent memory entries keyed by ``collection`` +
``agent_id``, with the full entry preserved as JSONB and ``content`` mirrored
for full-text search.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class AgentMemoryRecord(Base):
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String(128), nullable=False, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=False)
    data = Column(JSONB, nullable=False)
    doc_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

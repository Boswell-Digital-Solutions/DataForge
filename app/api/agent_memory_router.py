"""Agent Memory Store API.

Generic, agent-writable memory persistence for the reference agents' long-term
and episodic memory (the DataForgeAdapter's store_data / search_* / query_data
tools target these endpoints).

Endpoints:
* POST /api/v1/agent-memory          — store a memory entry (returns its id)
* POST /api/v1/agent-memory/search   — full-text search over memory content
* GET  /api/v1/agent-memory/{id}     — fetch a single memory entry

Auth is optional (mirrors the Experience Store): agents are trusted callers
within the fleet. Search is read-only full-text (ILIKE) over ``content``,
ordered by recency; results return the originally-stored entry dicts so the
caller can reconstruct its own memory objects.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent_memory_models import AgentMemoryRecord

router = APIRouter(prefix="/api/v1/agent-memory", tags=["Agent Memory"])


class AgentMemoryStoreRequest(BaseModel):
    collection: str = Field(..., min_length=1, max_length=128)
    data: dict[str, Any]
    metadata: Optional[dict[str, Any]] = None
    # Accepted for adapter compatibility; embeddings are supplied inside `data`
    # (or omitted) — this store ranks by recency + full-text, not vectors.
    generate_embedding: bool = False


class AgentMemoryStoreResponse(BaseModel):
    id: int
    collection: str
    stored_at: datetime


class AgentMemorySearchRequest(BaseModel):
    query: Optional[str] = None
    collections: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=200)
    # Accepted for adapter compatibility (semantic/fulltext callers):
    threshold: Optional[float] = None
    highlight: Optional[bool] = None


class AgentMemorySearchResponse(BaseModel):
    results: list[dict[str, Any]]
    count: int


def _content_of(data: dict[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, str):
        return content
    return "" if content is None else str(content)


@router.post("", status_code=201, response_model=AgentMemoryStoreResponse)
def store_agent_memory(
    body: AgentMemoryStoreRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AgentMemoryStoreResponse:
    meta = body.metadata or {}
    agent_id = meta.get("agent_id")
    row = AgentMemoryRecord(
        collection=body.collection,
        agent_id=(str(agent_id)[:64] if agent_id else None),
        content=_content_of(body.data),
        data=body.data,
        doc_metadata=(meta or None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return AgentMemoryStoreResponse(id=row.id, collection=row.collection, stored_at=row.created_at)


@router.post("/search", response_model=AgentMemorySearchResponse)
def search_agent_memory(
    body: AgentMemorySearchRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AgentMemorySearchResponse:
    q = db.query(AgentMemoryRecord)
    if body.collections:
        q = q.filter(AgentMemoryRecord.collection.in_(body.collections))
    if body.query:
        q = q.filter(AgentMemoryRecord.content.ilike(f"%{body.query}%"))
    rows = q.order_by(AgentMemoryRecord.created_at.desc()).limit(body.limit).all()
    results = [row.data for row in rows]
    return AgentMemorySearchResponse(results=results, count=len(results))


@router.get("/{memory_id}")
def get_agent_memory(memory_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.query(AgentMemoryRecord).filter(AgentMemoryRecord.id == memory_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    return row.data

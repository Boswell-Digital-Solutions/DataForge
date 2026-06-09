"""Context-Pack Store (cloud DataForge).

Cloud mirror of DataForge-Local's context-pack store. NeuroForge's Context Builder
fetches a governed precomputed pack by id (``GET /df/rag/context-pack/{id}``) and
serves inference from it instead of re-grounding (cheaper/faster tokens). The
producer publishes the PCC-assembled + pact-verified pack here keyed by the
context_bundle_id (``ctxb_...``).

The GET response matches NeuroForge's read contract exactly (``build_context``
reads ``primary`` / ``supporting`` / ``metadata``), so no NeuroForge change is
needed: callers pass ``context_pack_id = ctxb_...``.

* POST /df/rag/context-pack       — store/refresh a pack (idempotent on id)
* GET  /df/rag/context-pack/{id}  — fetch a pack (NeuroForge read shape)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.context_pack_models import ContextPack

router = APIRouter(prefix="/df/rag/context-pack", tags=["Context Pack"])


class ContextPackStoreRequest(BaseModel):
    context_pack_id: str = Field(..., min_length=1, max_length=128)
    bundle_hash: str = Field(..., min_length=1)
    primary: str = ""
    supporting: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    task_intent_id: str | None = None


class ContextPackStoreResponse(BaseModel):
    context_pack_id: str
    status: str


@router.post("", status_code=201, response_model=ContextPackStoreResponse)
def store_context_pack(
    body: ContextPackStoreRequest, db: Session = Depends(get_db)
) -> ContextPackStoreResponse:
    """Store or refresh a governed context pack, idempotent on context_pack_id.

    The id is hash-derived, so a re-store with the same id is the same pack;
    ORM get-then-update refreshes content/metadata (dialect-agnostic upsert).
    """
    obj = db.get(ContextPack, body.context_pack_id)
    existed = obj is not None
    if obj is None:
        obj = ContextPack(context_pack_id=body.context_pack_id)
    obj.bundle_hash = body.bundle_hash
    obj.task_intent_id = body.task_intent_id
    obj.primary_text = body.primary
    obj.supporting_json = list(body.supporting)
    obj.metadata_json = dict(body.metadata)
    obj.updated_at = datetime.utcnow()
    db.add(obj)
    db.commit()
    return ContextPackStoreResponse(
        context_pack_id=body.context_pack_id, status=("refreshed" if existed else "stored")
    )


@router.get("/{context_pack_id}")
def get_context_pack(context_pack_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Fetch a pack in NeuroForge's read shape: {primary, supporting, metadata}."""
    obj = db.get(ContextPack, context_pack_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"context pack {context_pack_id} not found")

    metadata = dict(obj.metadata_json or {})
    metadata.update(
        {
            "context_pack_id": obj.context_pack_id,
            "context_bundle_id": obj.context_pack_id,
            "context_bundle_hash": obj.bundle_hash,
            "task_intent_id": obj.task_intent_id,
            "served_from": "precomputed_pact_packet",
        }
    )
    created = obj.created_at
    return {
        # NeuroForge build_context reads exactly these three:
        "primary": obj.primary_text or "",
        "supporting": list(obj.supporting_json or []),
        "metadata": metadata,
        # Convenience echoes (ignored by NeuroForge):
        "context_pack_id": obj.context_pack_id,
        "bundle_hash": obj.bundle_hash,
        "created_at": created.isoformat() if isinstance(created, datetime) else created,
    }

"""Pydantic request/response models for the Forge Memory spine (FMEM-02)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactIn(BaseModel):
    """A full memory artifact (shared envelope + family payload) as produced by
    the forge-memory engine. Envelope is strict — unknown envelope fields fail
    closed."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(..., min_length=1, max_length=64)
    artifact_family: str = Field(..., min_length=1, max_length=128)
    artifact_version: int = Field(..., ge=1)
    produced_by_system: str
    produced_by_component: str
    source_scope: str
    lineage_root_id: str
    parent_artifact_id: str | None = None
    trace_id: str
    idempotency_key: str = Field(..., min_length=64, max_length=64)
    created_at: str
    recorded_at: str
    sensitivity_class: str
    visibility_class: str
    promotion_class: str
    validation_status: str
    signer_identity: str
    signature: str
    payload: dict[str, Any]


class WriteResponse(BaseModel):
    artifact_id: str
    family: str
    status: str  # stored | refreshed


class SupersedeRequest(BaseModel):
    new_fact: ArtifactIn
    effective_at: str = Field(..., description="RFC 3339 supersession time")


class DeletionReceiptOut(BaseModel):
    receipt_id: str
    target_family: str
    target_id: str
    deleted: bool
    deleted_at: str | None = None

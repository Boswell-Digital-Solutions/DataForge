"""Pydantic schemas for the proving-slice intake API surface.

Request model:
  ArtifactIntakeRequest  — full shared-envelope artifact submitted by DataForge Local.
                           Uses extra="allow" so all envelope fields pass through;
                           forge-contract-core performs the authoritative validation.

Response models:
  ReceiptPayload         — payload section of the returned promotion_receipt artifact.
  ProofReceiptArtifact   — full promotion_receipt artifact returned after intake.
  ReceiptLookupResponse  — thin wrapper for GET /receipts/by-artifact/{artifact_id}.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ArtifactIntakeRequest(BaseModel):
    """Full shared-envelope artifact from DataForge Local.

    Accepts all fields; forge-contract-core validates envelope + payload.
    """

    model_config = ConfigDict(extra="allow")

    artifact_id: str
    artifact_family: str
    artifact_version: int
    produced_by_system: str
    produced_by_component: str
    source_scope: str
    lineage_root_id: str
    parent_artifact_id: str | None = None
    trace_id: str
    idempotency_key: str
    created_at: str
    recorded_at: str
    sensitivity_class: str
    visibility_class: str
    promotion_class: str
    validation_status: str
    signer_identity: str
    signature: str
    payload: dict[str, Any]


class ReceiptPayload(BaseModel):
    """Payload section of the returned promotion_receipt artifact."""

    receipt_id: str
    related_artifact_ref: str
    intake_outcome: Literal["accepted", "rejected", "duplicate_reconciled"]
    shared_record_ref: str | None
    received_at: str
    idempotency_key: str
    outcome_summary: str
    rejection_class: str | None
    retry_allowed: bool
    producer_identity: str


class ProofReceiptArtifact(BaseModel):
    """Full promotion_receipt artifact returned to DataForge Local after intake.

    Conforms to the forge-contract-core shared envelope schema and the
    promotion_receipt family schema.
    """

    artifact_id: str
    artifact_family: Literal["promotion_receipt"]
    artifact_version: int
    produced_by_system: Literal["DataForge"]
    produced_by_component: Literal["proving_slice_intake"]
    source_scope: Literal["shared"]
    lineage_root_id: str
    parent_artifact_id: str | None
    trace_id: str
    idempotency_key: str
    created_at: str
    recorded_at: str
    sensitivity_class: Literal["internal"]
    visibility_class: Literal["operator"]
    promotion_class: Literal["local_only"]
    validation_status: Literal["valid"]
    signer_identity: str
    signature: str
    payload: ReceiptPayload


class ReceiptLookupResponse(BaseModel):
    """Response for GET /receipts/by-artifact/{artifact_id}."""

    artifact_id: str
    receipt: ProofReceiptArtifact

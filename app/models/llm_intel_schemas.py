"""Pydantic schemas for LLM provider intelligence source trust APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceTrustPolicyResponse(BaseModel):
    trust_class: str
    promotion_authority: str
    can_enter_extraction: bool
    can_support_candidate_promotion: bool
    candidate_disposition: str


class ApprovedSourceResponse(BaseModel):
    source_id: str
    provider_id: str
    source_url: str
    source_type: str
    trust_class: str
    approved_for_extraction: bool
    supports_candidate_promotion: bool
    source_registry_hash: str
    approved_at: str
    approved_by: str
    review_notes: str | None = None


class ApprovedSourceListResponse(BaseModel):
    items: list[ApprovedSourceResponse]
    total: int
    registry_hash: str


class SourceTrustValidationRequest(BaseModel):
    source_ids: list[str] = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)


class SourceTrustValidationResponse(BaseModel):
    allowed: bool
    outcome: str
    reason: str
    source_id: str | None = None
    provider_id: str | None = None
    trust_class: str | None = None
    requires_review: bool = False
    requires_maid: bool = False
    can_support_promotion: bool = False

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


DfRfFamily = Literal[
    "df_rf_evidence_link",
    "df_rf_finding_candidate",
    "df_rf_disposition",
]


class DfRfIngestRequest(BaseModel):
    family: DfRfFamily
    payload: dict[str, Any] = Field(..., min_length=1)


class DfRfIngestResponse(BaseModel):
    family: str
    record_id: str
    payload_hash: str
    storage_status: Literal["stored", "duplicate"]


class DfRfCandidateReviewItem(BaseModel):
    """One finding candidate enriched with its evidence links and (if closed) its
    disposition, for the Forge_Command operator review surface. Read-only."""

    candidate_id: str
    record_family: str
    run_id: str
    category: str
    disposition_state: str
    summary: str
    evidence_link_ids: list[str] = Field(default_factory=list)
    evidence_verification_statuses: dict[str, str] = Field(default_factory=dict)
    disposition: DfRfDispositionRead | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DfRfDispositionRead(BaseModel):
    disposition_id: str
    candidate_id: str
    operator_id: str
    decision: str
    rationale: str
    decided_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


DfRfCandidateReviewItem.model_rebuild()


class DfRfCandidateReviewFeed(BaseModel):
    items: list[DfRfCandidateReviewItem]
    count: int

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


LLMIntelPendingRecordFamily = Literal[
    "llm_intel_fetch_receipts",
    "llm_intel_provider_adapter_receipts",
    "llm_intel_source_fingerprints",
    "llm_intel_extracted_claims",
    "llm_intel_model_candidates",
    "llm_intel_pricing_candidates",
    "llm_intel_capability_candidates",
    "llm_intel_drift_reports",
    "llm_intel_replay_manifests",
]


class LLMIntelPendingRecordIngestRequest(BaseModel):
    record_family: LLMIntelPendingRecordFamily
    run_id: str | None = Field(default=None, min_length=1, max_length=128)
    payload: dict[str, Any] = Field(..., min_length=1)


class LLMIntelPendingRecordIngestResponse(BaseModel):
    record_family: str
    record_id: str
    run_id: str | None = None
    provider_id: str | None = None
    payload_hash: str
    storage_status: Literal["stored", "duplicate"]
    promotion_application_allowed: Literal[False] = False


class LLMIntelRunPendingRecordSummary(BaseModel):
    run_id: str
    record_counts: dict[str, int]
    receipt_ids: list[str]
    source_fingerprint_ids: list[str]
    claim_ids: list[str]
    candidate_ids: list[str]
    drift_report_ids: list[str]
    replay_manifest_ids: list[str]
    promotion_application_allowed: Literal[False] = False

    model_config = ConfigDict(from_attributes=True)


class LLMIntelPromotionDecisionApplyRequest(BaseModel):
    payload: dict[str, Any] = Field(..., min_length=1)


class LLMIntelPromotionApplicationResponse(BaseModel):
    decision_id: str
    candidate_id: str
    decision: str
    decision_resulting_state: str
    promotion_state: str
    promotion_applied: bool
    application_status: Literal["stored", "duplicate", "recorded_no_promotion"]
    payload_hash: str
    promoted_record_id: str | None = None
    promotion_action: str | None = None
    supersedes_record_id: str | None = None
    lineage_root_id: str | None = None
    supersession_chain_event_id: str | None = None
    promoted_payload: dict[str, Any] | None = None


class LLMIntelPromotedRecordRead(BaseModel):
    promoted_record_id: str
    provider_id: str
    record_type: str
    candidate_id: str
    decision_id: str
    claim_path: str
    promotion_action: str
    lineage_root_id: str
    supersedes_record_id: str | None = None
    superseded_by_record_id: str | None = None
    is_current: bool
    payload_hash: str
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class LLMIntelReceiptRecord(Base):
    __tablename__ = "llm_intel_receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(String(128), nullable=False, unique=True, index=True)
    record_family = Column(String(80), nullable=False, index=True)

    run_id = Column(String(128), nullable=False, index=True)
    provider_id = Column(String(32), nullable=False, index=True)
    source_id = Column(String(128), nullable=True, index=True)
    adapter_id = Column(String(128), nullable=True, index=True)
    receipt_status = Column(String(32), nullable=False, index=True)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelSourceFingerprintRecord(Base):
    __tablename__ = "llm_intel_source_fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint_id = Column(String(128), nullable=False, unique=True, index=True)

    run_id = Column(String(128), nullable=True, index=True)
    source_id = Column(String(128), nullable=False, index=True)
    provider_id = Column(String(32), nullable=False, index=True)
    trust_class = Column(String(32), nullable=False, index=True)
    content_hash = Column(String(71), nullable=False, index=True)
    adapter_id = Column(String(128), nullable=False, index=True)
    adapter_version = Column(String(64), nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelExtractedClaimRecord(Base):
    __tablename__ = "llm_intel_extracted_claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(128), nullable=False, unique=True, index=True)

    run_id = Column(String(128), nullable=False, index=True)
    provider_id = Column(String(32), nullable=False, index=True)
    claim_type = Column(String(64), nullable=False, index=True)
    claim_path = Column(String(512), nullable=False, index=True)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelPendingCandidateRecord(Base):
    __tablename__ = "llm_intel_pending_candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(128), nullable=False, unique=True, index=True)
    record_family = Column(String(80), nullable=False, index=True)

    run_id = Column(String(128), nullable=False, index=True)
    provider_id = Column(String(32), nullable=False, index=True)
    candidate_type = Column(String(64), nullable=False, index=True)
    claim_type = Column(String(64), nullable=False, index=True)
    claim_path = Column(String(512), nullable=False, index=True)
    promotion_state = Column(String(64), nullable=False, index=True)

    source_fingerprint_ids = Column(JSONB, nullable=False)
    receipt_ids = Column(JSONB, nullable=False)
    claim_ids = Column(JSONB, nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )


class LLMIntelDriftReportRecord(Base):
    __tablename__ = "llm_intel_drift_reports"

    id = Column(Integer, primary_key=True, index=True)
    drift_report_id = Column(String(128), nullable=False, unique=True, index=True)

    run_id = Column(String(128), nullable=False, index=True)
    provider_id = Column(String(32), nullable=False, index=True)
    candidate_id = Column(String(128), nullable=False, index=True)
    drift_type = Column(String(64), nullable=False, index=True)
    impact_class = Column(String(32), nullable=False, index=True)
    requires_maid = Column(Boolean, nullable=False, default=False, index=True)
    conflict_status = Column(String(32), nullable=False, index=True)
    promotion_state = Column(String(64), nullable=False, index=True)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelReplayManifestRecord(Base):
    __tablename__ = "llm_intel_replay_manifests"

    id = Column(Integer, primary_key=True, index=True)
    replay_manifest_id = Column(String(128), nullable=False, unique=True, index=True)

    run_id = Column(String(128), nullable=False, index=True)
    manifest_status = Column(String(64), nullable=False, index=True)
    input_manifest_hash = Column(String(71), nullable=False, index=True)
    output_manifest_hash = Column(String(71), nullable=True, index=True)
    replay_determinism_hash = Column(String(71), nullable=False, index=True)

    source_fingerprint_ids = Column(JSONB, nullable=False)
    fetch_receipt_ids = Column(JSONB, nullable=False)
    adapter_receipt_ids = Column(JSONB, nullable=False)
    claim_ids = Column(JSONB, nullable=False)
    candidate_ids = Column(JSONB, nullable=False)
    drift_report_ids = Column(JSONB, nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelPromotionDecisionRecord(Base):
    __tablename__ = "llm_intel_promotion_decisions"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(128), nullable=False, unique=True, index=True)

    review_packet_id = Column(String(128), nullable=False, index=True)
    candidate_id = Column(String(128), nullable=False, index=True)
    operator_id = Column(String(256), nullable=False, index=True)
    authority_ring = Column(String(32), nullable=False, index=True)
    decision = Column(String(32), nullable=False, index=True)
    resulting_state = Column(String(64), nullable=False, index=True)
    evidence_bundle_hash = Column(String(71), nullable=False, index=True)

    affected_record_refs = Column(JSONB, nullable=False)
    constraints = Column(JSONB, nullable=False)
    promoted_record_id = Column(String(128), nullable=True, index=True)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    decided_at = Column(String(64), nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelPromotedRecord(Base):
    __tablename__ = "llm_intel_promoted_records"

    id = Column(Integer, primary_key=True, index=True)
    promoted_record_id = Column(String(128), nullable=False, unique=True, index=True)

    provider_id = Column(String(32), nullable=False, index=True)
    record_type = Column(String(64), nullable=False, index=True)
    candidate_id = Column(String(128), nullable=False, index=True)
    decision_id = Column(String(128), nullable=False, index=True)
    source_decision_ref = Column(String(512), nullable=False, index=True)
    evidence_bundle_hash = Column(String(71), nullable=False, index=True)
    claim_path = Column(String(512), nullable=False, index=True)

    promotion_action = Column(String(32), nullable=False, index=True)
    lineage_root_id = Column(String(128), nullable=False, index=True)
    supersedes_record_id = Column(String(128), nullable=True, index=True)
    superseded_by_record_id = Column(String(128), nullable=True, index=True)
    is_current = Column(Boolean, nullable=False, default=True, index=True)

    source_fingerprint_ids = Column(JSONB, nullable=False)
    receipt_ids = Column(JSONB, nullable=False)
    claim_ids = Column(JSONB, nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    promoted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    superseded_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LLMIntelSupersessionChainRecord(Base):
    __tablename__ = "llm_intel_supersession_chains"

    id = Column(Integer, primary_key=True, index=True)
    chain_event_id = Column(String(128), nullable=False, unique=True, index=True)

    provider_id = Column(String(32), nullable=False, index=True)
    record_type = Column(String(64), nullable=False, index=True)
    claim_path = Column(String(512), nullable=False, index=True)
    lineage_root_id = Column(String(128), nullable=False, index=True)
    from_record_id = Column(String(128), nullable=True, index=True)
    to_record_id = Column(String(128), nullable=False, index=True)
    decision_id = Column(String(128), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

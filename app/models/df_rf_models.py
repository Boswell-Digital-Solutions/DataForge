"""ORM mappings for the BDS-DF-RF-001 Receipt-to-Finding Knowledge Spine.

Generalizes the storage *pattern* of app/models/llm_intel_pending_records_models.py
(stable externally-supplied id column, payload_hash + payload stored verbatim,
JSONB arrays for cross-references instead of FKs) per OD-03 -- new tables, not
reused ones; the llm-intel tables stay untouched and unrelated.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class DfRfEvidenceLinkRecord(Base):
    __tablename__ = "df_rf_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    evidence_link_id = Column(String(128), nullable=False, unique=True, index=True)

    source_plan_id = Column(String(64), nullable=False, index=True)
    upstream_family = Column(String(128), nullable=False, index=True)
    upstream_record_id = Column(String(128), nullable=False, index=True)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    collected_by = Column(String(128), nullable=False)
    verification_status = Column(String(32), nullable=False, index=True)
    privacy_class = Column(String(32), nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class DfRfFindingCandidateRecord(Base):
    __tablename__ = "df_rf_finding_candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(128), nullable=False, unique=True, index=True)

    record_family = Column(String(80), nullable=False, index=True)
    natural_key = Column(String(512), nullable=False)
    run_id = Column(String(128), nullable=False, index=True)
    category = Column(String(128), nullable=False, index=True)
    evidence_link_ids = Column(JSONB, nullable=False)
    disposition_state = Column(String(32), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    classification = Column(String(32), nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )


class DfRfDispositionRecord(Base):
    __tablename__ = "df_rf_dispositions"

    id = Column(Integer, primary_key=True, index=True)
    disposition_id = Column(String(128), nullable=False, unique=True, index=True)

    candidate_id = Column(String(128), nullable=False, index=True)
    operator_id = Column(String(256), nullable=False, index=True)
    decision = Column(String(32), nullable=False, index=True)
    rationale = Column(Text, nullable=False)
    evidence_bundle_hash = Column(String(71), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=False)

    payload_hash = Column(String(71), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

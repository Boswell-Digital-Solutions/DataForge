"""add llm intel pending record tables

Revision ID: 20260528_01
Revises: 20260404_10
Create Date: 2026-05-28 19:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260528_01"
down_revision = "20260404_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_intel_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("record_family", sa.String(length=80), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("adapter_id", sa.String(length=128), nullable=True),
        sa.Column("receipt_status", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_receipts_run_id", "llm_intel_receipts", ["run_id"])
    op.create_index("ix_llm_intel_receipts_provider_id", "llm_intel_receipts", ["provider_id"])
    op.create_index("ix_llm_intel_receipts_record_family", "llm_intel_receipts", ["record_family"])

    op.create_table(
        "llm_intel_source_fingerprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fingerprint_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("trust_class", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("adapter_id", sa.String(length=128), nullable=False),
        sa.Column("adapter_version", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_llm_intel_source_fingerprints_run_id",
        "llm_intel_source_fingerprints",
        ["run_id"],
    )
    op.create_index(
        "ix_llm_intel_source_fingerprints_provider_id",
        "llm_intel_source_fingerprints",
        ["provider_id"],
    )
    op.create_index(
        "ix_llm_intel_source_fingerprints_trust_class",
        "llm_intel_source_fingerprints",
        ["trust_class"],
    )

    op.create_table(
        "llm_intel_extracted_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False),
        sa.Column("claim_path", sa.String(length=512), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_extracted_claims_run_id", "llm_intel_extracted_claims", ["run_id"])
    op.create_index(
        "ix_llm_intel_extracted_claims_provider_id",
        "llm_intel_extracted_claims",
        ["provider_id"],
    )
    op.create_index(
        "ix_llm_intel_extracted_claims_claim_type",
        "llm_intel_extracted_claims",
        ["claim_type"],
    )

    op.create_table(
        "llm_intel_pending_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("record_family", sa.String(length=80), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("candidate_type", sa.String(length=64), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False),
        sa.Column("claim_path", sa.String(length=512), nullable=False),
        sa.Column("promotion_state", sa.String(length=64), nullable=False),
        sa.Column("source_fingerprint_ids", JSONB(), nullable=False),
        sa.Column("receipt_ids", JSONB(), nullable=False),
        sa.Column("claim_ids", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_pending_candidates_run_id", "llm_intel_pending_candidates", ["run_id"])
    op.create_index(
        "ix_llm_intel_pending_candidates_provider_id",
        "llm_intel_pending_candidates",
        ["provider_id"],
    )
    op.create_index(
        "ix_llm_intel_pending_candidates_promotion_state",
        "llm_intel_pending_candidates",
        ["promotion_state"],
    )

    op.create_table(
        "llm_intel_drift_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("drift_report_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("impact_class", sa.String(length=32), nullable=False),
        sa.Column("requires_maid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("conflict_status", sa.String(length=32), nullable=False),
        sa.Column("promotion_state", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_drift_reports_run_id", "llm_intel_drift_reports", ["run_id"])
    op.create_index(
        "ix_llm_intel_drift_reports_candidate_id",
        "llm_intel_drift_reports",
        ["candidate_id"],
    )
    op.create_index(
        "ix_llm_intel_drift_reports_promotion_state",
        "llm_intel_drift_reports",
        ["promotion_state"],
    )

    op.create_table(
        "llm_intel_replay_manifests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("replay_manifest_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("manifest_status", sa.String(length=64), nullable=False),
        sa.Column("input_manifest_hash", sa.String(length=71), nullable=False),
        sa.Column("output_manifest_hash", sa.String(length=71), nullable=True),
        sa.Column("replay_determinism_hash", sa.String(length=71), nullable=False),
        sa.Column("source_fingerprint_ids", JSONB(), nullable=False),
        sa.Column("fetch_receipt_ids", JSONB(), nullable=False),
        sa.Column("adapter_receipt_ids", JSONB(), nullable=False),
        sa.Column("claim_ids", JSONB(), nullable=False),
        sa.Column("candidate_ids", JSONB(), nullable=False),
        sa.Column("drift_report_ids", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_replay_manifests_run_id", "llm_intel_replay_manifests", ["run_id"])
    op.create_index(
        "ix_llm_intel_replay_manifests_manifest_status",
        "llm_intel_replay_manifests",
        ["manifest_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_intel_replay_manifests_manifest_status", table_name="llm_intel_replay_manifests")
    op.drop_index("ix_llm_intel_replay_manifests_run_id", table_name="llm_intel_replay_manifests")
    op.drop_table("llm_intel_replay_manifests")

    op.drop_index("ix_llm_intel_drift_reports_promotion_state", table_name="llm_intel_drift_reports")
    op.drop_index("ix_llm_intel_drift_reports_candidate_id", table_name="llm_intel_drift_reports")
    op.drop_index("ix_llm_intel_drift_reports_run_id", table_name="llm_intel_drift_reports")
    op.drop_table("llm_intel_drift_reports")

    op.drop_index("ix_llm_intel_pending_candidates_promotion_state", table_name="llm_intel_pending_candidates")
    op.drop_index("ix_llm_intel_pending_candidates_provider_id", table_name="llm_intel_pending_candidates")
    op.drop_index("ix_llm_intel_pending_candidates_run_id", table_name="llm_intel_pending_candidates")
    op.drop_table("llm_intel_pending_candidates")

    op.drop_index("ix_llm_intel_extracted_claims_claim_type", table_name="llm_intel_extracted_claims")
    op.drop_index("ix_llm_intel_extracted_claims_provider_id", table_name="llm_intel_extracted_claims")
    op.drop_index("ix_llm_intel_extracted_claims_run_id", table_name="llm_intel_extracted_claims")
    op.drop_table("llm_intel_extracted_claims")

    op.drop_index("ix_llm_intel_source_fingerprints_trust_class", table_name="llm_intel_source_fingerprints")
    op.drop_index("ix_llm_intel_source_fingerprints_provider_id", table_name="llm_intel_source_fingerprints")
    op.drop_index("ix_llm_intel_source_fingerprints_run_id", table_name="llm_intel_source_fingerprints")
    op.drop_table("llm_intel_source_fingerprints")

    op.drop_index("ix_llm_intel_receipts_record_family", table_name="llm_intel_receipts")
    op.drop_index("ix_llm_intel_receipts_provider_id", table_name="llm_intel_receipts")
    op.drop_index("ix_llm_intel_receipts_run_id", table_name="llm_intel_receipts")
    op.drop_table("llm_intel_receipts")

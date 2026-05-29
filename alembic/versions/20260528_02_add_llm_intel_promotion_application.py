"""add llm intel promotion application tables

Revision ID: 20260528_02
Revises: 20260528_01
Create Date: 2026-05-28 21:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260528_02"
down_revision = "20260528_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_intel_promotion_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("review_packet_id", sa.String(length=128), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("operator_id", sa.String(length=256), nullable=False),
        sa.Column("authority_ring", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("resulting_state", sa.String(length=64), nullable=False),
        sa.Column("evidence_bundle_hash", sa.String(length=71), nullable=False),
        sa.Column("affected_record_refs", JSONB(), nullable=False),
        sa.Column("constraints", JSONB(), nullable=False),
        sa.Column("promoted_record_id", sa.String(length=128), nullable=True),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("decided_at", sa.String(length=64), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_llm_intel_promotion_decisions_candidate_id",
        "llm_intel_promotion_decisions",
        ["candidate_id"],
    )
    op.create_index(
        "ix_llm_intel_promotion_decisions_decision",
        "llm_intel_promotion_decisions",
        ["decision"],
    )
    op.create_index(
        "ix_llm_intel_promotion_decisions_resulting_state",
        "llm_intel_promotion_decisions",
        ["resulting_state"],
    )
    op.create_index(
        "ix_llm_intel_promotion_decisions_promoted_record_id",
        "llm_intel_promotion_decisions",
        ["promoted_record_id"],
    )

    op.create_table(
        "llm_intel_promoted_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("promoted_record_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("record_type", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("source_decision_ref", sa.String(length=512), nullable=False),
        sa.Column("evidence_bundle_hash", sa.String(length=71), nullable=False),
        sa.Column("claim_path", sa.String(length=512), nullable=False),
        sa.Column("promotion_action", sa.String(length=32), nullable=False),
        sa.Column("lineage_root_id", sa.String(length=128), nullable=False),
        sa.Column("supersedes_record_id", sa.String(length=128), nullable=True),
        sa.Column("superseded_by_record_id", sa.String(length=128), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_fingerprint_ids", JSONB(), nullable=False),
        sa.Column("receipt_ids", JSONB(), nullable=False),
        sa.Column("claim_ids", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_promoted_records_provider_id", "llm_intel_promoted_records", ["provider_id"])
    op.create_index("ix_llm_intel_promoted_records_record_type", "llm_intel_promoted_records", ["record_type"])
    op.create_index("ix_llm_intel_promoted_records_candidate_id", "llm_intel_promoted_records", ["candidate_id"])
    op.create_index("ix_llm_intel_promoted_records_decision_id", "llm_intel_promoted_records", ["decision_id"])
    op.create_index("ix_llm_intel_promoted_records_claim_path", "llm_intel_promoted_records", ["claim_path"])
    op.create_index("ix_llm_intel_promoted_records_lineage_root_id", "llm_intel_promoted_records", ["lineage_root_id"])
    op.create_index("ix_llm_intel_promoted_records_is_current", "llm_intel_promoted_records", ["is_current"])
    op.create_index(
        "ix_llm_intel_promoted_records_current_lookup",
        "llm_intel_promoted_records",
        ["provider_id", "record_type", "claim_path", "is_current"],
    )

    op.create_table(
        "llm_intel_supersession_chains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chain_event_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("provider_id", sa.String(length=32), nullable=False),
        sa.Column("record_type", sa.String(length=64), nullable=False),
        sa.Column("claim_path", sa.String(length=512), nullable=False),
        sa.Column("lineage_root_id", sa.String(length=128), nullable=False),
        sa.Column("from_record_id", sa.String(length=128), nullable=True),
        sa.Column("to_record_id", sa.String(length=128), nullable=False),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_intel_supersession_chains_provider_id", "llm_intel_supersession_chains", ["provider_id"])
    op.create_index("ix_llm_intel_supersession_chains_record_type", "llm_intel_supersession_chains", ["record_type"])
    op.create_index("ix_llm_intel_supersession_chains_lineage_root_id", "llm_intel_supersession_chains", ["lineage_root_id"])
    op.create_index("ix_llm_intel_supersession_chains_from_record_id", "llm_intel_supersession_chains", ["from_record_id"])
    op.create_index("ix_llm_intel_supersession_chains_to_record_id", "llm_intel_supersession_chains", ["to_record_id"])
    op.create_index("ix_llm_intel_supersession_chains_decision_id", "llm_intel_supersession_chains", ["decision_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_intel_supersession_chains_decision_id", table_name="llm_intel_supersession_chains")
    op.drop_index("ix_llm_intel_supersession_chains_to_record_id", table_name="llm_intel_supersession_chains")
    op.drop_index("ix_llm_intel_supersession_chains_from_record_id", table_name="llm_intel_supersession_chains")
    op.drop_index("ix_llm_intel_supersession_chains_lineage_root_id", table_name="llm_intel_supersession_chains")
    op.drop_index("ix_llm_intel_supersession_chains_record_type", table_name="llm_intel_supersession_chains")
    op.drop_index("ix_llm_intel_supersession_chains_provider_id", table_name="llm_intel_supersession_chains")
    op.drop_table("llm_intel_supersession_chains")

    op.drop_index("ix_llm_intel_promoted_records_current_lookup", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_is_current", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_lineage_root_id", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_claim_path", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_decision_id", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_candidate_id", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_record_type", table_name="llm_intel_promoted_records")
    op.drop_index("ix_llm_intel_promoted_records_provider_id", table_name="llm_intel_promoted_records")
    op.drop_table("llm_intel_promoted_records")

    op.drop_index("ix_llm_intel_promotion_decisions_promoted_record_id", table_name="llm_intel_promotion_decisions")
    op.drop_index("ix_llm_intel_promotion_decisions_resulting_state", table_name="llm_intel_promotion_decisions")
    op.drop_index("ix_llm_intel_promotion_decisions_decision", table_name="llm_intel_promotion_decisions")
    op.drop_index("ix_llm_intel_promotion_decisions_candidate_id", table_name="llm_intel_promotion_decisions")
    op.drop_table("llm_intel_promotion_decisions")

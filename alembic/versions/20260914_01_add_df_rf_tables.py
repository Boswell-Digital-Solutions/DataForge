"""add BDS-DF-RF-001 receipt-to-finding spine tables

Revision ID: 20260914_01
Revises: 20260913_02
Create Date: 2026-09-14 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260914_01"
down_revision = "20260913_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "df_rf_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_link_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("source_plan_id", sa.String(length=64), nullable=False),
        sa.Column("upstream_family", sa.String(length=128), nullable=False),
        sa.Column("upstream_record_id", sa.String(length=128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by", sa.String(length=128), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("privacy_class", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_df_rf_evidence_links_source_plan_id", "df_rf_evidence_links", ["source_plan_id"])
    op.create_index("ix_df_rf_evidence_links_upstream_family", "df_rf_evidence_links", ["upstream_family"])
    op.create_index("ix_df_rf_evidence_links_upstream_record_id", "df_rf_evidence_links", ["upstream_record_id"])
    op.create_index("ix_df_rf_evidence_links_verification_status", "df_rf_evidence_links", ["verification_status"])
    op.create_index("ix_df_rf_evidence_links_payload_hash", "df_rf_evidence_links", ["payload_hash"])

    op.create_table(
        "df_rf_finding_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("record_family", sa.String(length=80), nullable=False),
        sa.Column("natural_key", sa.String(length=512), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("evidence_link_ids", JSONB(), nullable=False),
        sa.Column("disposition_state", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_df_rf_finding_candidates_record_family", "df_rf_finding_candidates", ["record_family"])
    op.create_index("ix_df_rf_finding_candidates_run_id", "df_rf_finding_candidates", ["run_id"])
    op.create_index("ix_df_rf_finding_candidates_category", "df_rf_finding_candidates", ["category"])
    op.create_index(
        "ix_df_rf_finding_candidates_disposition_state", "df_rf_finding_candidates", ["disposition_state"]
    )
    op.create_index("ix_df_rf_finding_candidates_payload_hash", "df_rf_finding_candidates", ["payload_hash"])

    op.create_table(
        "df_rf_dispositions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("disposition_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("operator_id", sa.String(length=256), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_bundle_hash", sa.String(length=71), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_df_rf_dispositions_candidate_id", "df_rf_dispositions", ["candidate_id"])
    op.create_index("ix_df_rf_dispositions_operator_id", "df_rf_dispositions", ["operator_id"])
    op.create_index("ix_df_rf_dispositions_decision", "df_rf_dispositions", ["decision"])
    op.create_index("ix_df_rf_dispositions_payload_hash", "df_rf_dispositions", ["payload_hash"])


def downgrade() -> None:
    op.drop_index("ix_df_rf_dispositions_payload_hash", table_name="df_rf_dispositions")
    op.drop_index("ix_df_rf_dispositions_decision", table_name="df_rf_dispositions")
    op.drop_index("ix_df_rf_dispositions_operator_id", table_name="df_rf_dispositions")
    op.drop_index("ix_df_rf_dispositions_candidate_id", table_name="df_rf_dispositions")
    op.drop_table("df_rf_dispositions")

    op.drop_index("ix_df_rf_finding_candidates_payload_hash", table_name="df_rf_finding_candidates")
    op.drop_index("ix_df_rf_finding_candidates_disposition_state", table_name="df_rf_finding_candidates")
    op.drop_index("ix_df_rf_finding_candidates_category", table_name="df_rf_finding_candidates")
    op.drop_index("ix_df_rf_finding_candidates_run_id", table_name="df_rf_finding_candidates")
    op.drop_index("ix_df_rf_finding_candidates_record_family", table_name="df_rf_finding_candidates")
    op.drop_table("df_rf_finding_candidates")

    op.drop_index("ix_df_rf_evidence_links_payload_hash", table_name="df_rf_evidence_links")
    op.drop_index("ix_df_rf_evidence_links_verification_status", table_name="df_rf_evidence_links")
    op.drop_index("ix_df_rf_evidence_links_upstream_record_id", table_name="df_rf_evidence_links")
    op.drop_index("ix_df_rf_evidence_links_upstream_family", table_name="df_rf_evidence_links")
    op.drop_index("ix_df_rf_evidence_links_source_plan_id", table_name="df_rf_evidence_links")
    op.drop_table("df_rf_evidence_links")

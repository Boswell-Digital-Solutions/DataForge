"""proving slice cloud intake and receipt tables

Revision ID: 20260404_10
Revises: 20260401_02
Create Date: 2026-04-04 12:00:00

Two tables for the proving-slice intake surface:

  ps_cloud_intake_records  — one row per artifact received from DataForge Local.
                             Idempotency key is UNIQUE: duplicate submits are
                             detected here and reconciled without re-processing.

  ps_cloud_receipts        — one row per receipt artifact emitted back to Local.
                             Each intake record produces exactly one receipt row.

Both tables are in the default public schema, following Cloud conventions.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260404_10"
down_revision = "20260401_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ps_cloud_intake_records ───────────────────────────────────────────────
    op.create_table(
        "ps_cloud_intake_records",
        sa.Column("intake_id", sa.String(length=36), primary_key=True),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_family", sa.String(length=128), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("produced_by_system", sa.String(length=255), nullable=False),
        sa.Column("lineage_root_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("intake_outcome", sa.String(length=64), nullable=False),
        sa.Column("rejection_class", sa.Text(), nullable=True),
        sa.Column("rejection_detail", sa.Text(), nullable=True),
        sa.Column("shared_record_ref", sa.Text(), nullable=True),
        sa.Column("payload_json", JSONB(), nullable=False),
        sa.Column("envelope_json", JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ps_cloud_intake_records_artifact_id",
        "ps_cloud_intake_records",
        ["artifact_id"],
    )
    op.create_index(
        "ix_ps_cloud_intake_records_artifact_family",
        "ps_cloud_intake_records",
        ["artifact_family"],
    )
    op.create_index(
        "ix_ps_cloud_intake_records_intake_outcome",
        "ps_cloud_intake_records",
        ["intake_outcome"],
    )
    op.create_index(
        "ix_ps_cloud_intake_records_received_at",
        "ps_cloud_intake_records",
        ["received_at"],
    )
    op.create_index(
        "ix_ps_cloud_intake_records_lineage_root_id",
        "ps_cloud_intake_records",
        ["lineage_root_id"],
    )

    # ── ps_cloud_receipts ─────────────────────────────────────────────────────
    op.create_table(
        "ps_cloud_receipts",
        sa.Column("receipt_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "intake_id",
            sa.String(length=36),
            sa.ForeignKey("ps_cloud_intake_records.intake_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_artifact_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("intake_outcome", sa.String(length=64), nullable=False),
        sa.Column("rejection_class", sa.Text(), nullable=True),
        sa.Column(
            "retry_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("outcome_summary", sa.Text(), nullable=True),
        sa.Column("shared_record_ref", sa.Text(), nullable=True),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ps_cloud_receipts_artifact_id",
        "ps_cloud_receipts",
        ["artifact_id"],
    )
    op.create_index(
        "ix_ps_cloud_receipts_intake_id",
        "ps_cloud_receipts",
        ["intake_id"],
    )
    op.create_index(
        "ix_ps_cloud_receipts_intake_outcome",
        "ps_cloud_receipts",
        ["intake_outcome"],
    )


def downgrade() -> None:
    op.drop_index("ix_ps_cloud_receipts_intake_outcome", table_name="ps_cloud_receipts")
    op.drop_index("ix_ps_cloud_receipts_intake_id", table_name="ps_cloud_receipts")
    op.drop_index("ix_ps_cloud_receipts_artifact_id", table_name="ps_cloud_receipts")
    op.drop_table("ps_cloud_receipts")

    op.drop_index(
        "ix_ps_cloud_intake_records_lineage_root_id",
        table_name="ps_cloud_intake_records",
    )
    op.drop_index(
        "ix_ps_cloud_intake_records_received_at",
        table_name="ps_cloud_intake_records",
    )
    op.drop_index(
        "ix_ps_cloud_intake_records_intake_outcome",
        table_name="ps_cloud_intake_records",
    )
    op.drop_index(
        "ix_ps_cloud_intake_records_artifact_family",
        table_name="ps_cloud_intake_records",
    )
    op.drop_index(
        "ix_ps_cloud_intake_records_artifact_id",
        table_name="ps_cloud_intake_records",
    )
    op.drop_table("ps_cloud_intake_records")

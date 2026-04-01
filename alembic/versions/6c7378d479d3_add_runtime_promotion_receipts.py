"""add runtime promotion receipts

Revision ID: 6c7378d479d3
Revises: policy_envelope_002
Create Date: 2026-03-31 21:17:10.737545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6c7378d479d3"
down_revision: Union[str, Sequence[str], None] = "policy_envelope_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "runtime_promotion_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("envelope_type", sa.String(length=100), nullable=False),
        sa.Column("envelope_version", sa.String(length=20), nullable=False),
        sa.Column("fleet_member_id", sa.String(length=255), nullable=False),
        sa.Column("runtime_bundle_id", sa.String(length=255), nullable=True),
        sa.Column("runtime_bundle_version", sa.String(length=100), nullable=True),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingest_status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_created_at"),
        "runtime_promotion_receipts",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_dedupe_key"),
        "runtime_promotion_receipts",
        ["dedupe_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_envelope_type"),
        "runtime_promotion_receipts",
        ["envelope_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_fleet_member_id"),
        "runtime_promotion_receipts",
        ["fleet_member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_id"),
        "runtime_promotion_receipts",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_ingest_status"),
        "runtime_promotion_receipts",
        ["ingest_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_observed_at"),
        "runtime_promotion_receipts",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_receipt_id"),
        "runtime_promotion_receipts",
        ["receipt_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_runtime_promotion_receipts_service"),
        "runtime_promotion_receipts",
        ["service"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_runtime_promotion_receipts_service"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_receipt_id"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_observed_at"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_ingest_status"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_id"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_fleet_member_id"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_envelope_type"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_dedupe_key"), table_name="runtime_promotion_receipts")
    op.drop_index(op.f("ix_runtime_promotion_receipts_created_at"), table_name="runtime_promotion_receipts")
    op.drop_table("runtime_promotion_receipts")
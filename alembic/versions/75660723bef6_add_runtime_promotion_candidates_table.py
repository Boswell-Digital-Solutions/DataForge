"""add runtime promotion candidates table

Revision ID: 75660723bef6
Revises: 18d6ce4f3d7b
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "75660723bef6"
down_revision: Union[str, None] = "6c7378d479d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runtime_promotion_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_type", sa.String(length=100), nullable=False),
        sa.Column("source_envelope_type", sa.String(length=100), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("fleet_member_id", sa.String(length=255), nullable=False),
        sa.Column("issue_class", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="review_ready",
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default="runtime_promotion",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.UniqueConstraint("candidate_id"),
        sa.UniqueConstraint("receipt_id"),
    )

    op.create_index(
        "ix_runtime_promotion_candidates_candidate_id",
        "runtime_promotion_candidates",
        ["candidate_id"],
        unique=True,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_receipt_id",
        "runtime_promotion_candidates",
        ["receipt_id"],
        unique=True,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_candidate_type",
        "runtime_promotion_candidates",
        ["candidate_type"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_source_envelope_type",
        "runtime_promotion_candidates",
        ["source_envelope_type"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_service",
        "runtime_promotion_candidates",
        ["service"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_fleet_member_id",
        "runtime_promotion_candidates",
        ["fleet_member_id"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_issue_class",
        "runtime_promotion_candidates",
        ["issue_class"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_severity",
        "runtime_promotion_candidates",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_status",
        "runtime_promotion_candidates",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_created_at",
        "runtime_promotion_candidates",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidates_updated_at",
        "runtime_promotion_candidates",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_promotion_candidates_updated_at",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_created_at",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_status",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_severity",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_issue_class",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_fleet_member_id",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_service",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_source_envelope_type",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_candidate_type",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_receipt_id",
        table_name="runtime_promotion_candidates",
    )
    op.drop_index(
        "ix_runtime_promotion_candidates_candidate_id",
        table_name="runtime_promotion_candidates",
    )
    op.drop_table("runtime_promotion_candidates")
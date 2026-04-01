"""add runtime promotion candidate decisions table

Revision ID: 20260401_1200
Revises: 75660723bef6
Create Date: 2026-04-01 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_1200"
down_revision = "75660723bef6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_promotion_candidate_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("prior_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column("operator_identity", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["runtime_promotion_candidates.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_runtime_promotion_candidate_decisions_candidate_id",
        "runtime_promotion_candidate_decisions",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_promotion_candidate_decisions_created_at",
        "runtime_promotion_candidate_decisions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_promotion_candidate_decisions_created_at",
        table_name="runtime_promotion_candidate_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_candidate_decisions_candidate_id",
        table_name="runtime_promotion_candidate_decisions",
    )
    op.drop_table("runtime_promotion_candidate_decisions")
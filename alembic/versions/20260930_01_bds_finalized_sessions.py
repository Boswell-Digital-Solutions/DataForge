"""Persist finalized BDS sessions behind a dedicated service API.

Revision ID: 20260930_01
Revises: 20260914_02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260930_01"
down_revision = "20260914_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bds_sessions",
        sa.Column("session_kind", sa.String(length=16), primary_key=True),
        sa.Column("session_id", sa.String(length=100), primary_key=True),
        sa.Column("final_status", sa.String(length=16), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_data", JSONB(), nullable=False),
        sa.Column(
            "persisted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "session_kind IN ('planning','execution','evaluation','workflow')",
            name="ck_bds_sessions_kind",
        ),
        sa.CheckConstraint(
            "final_status IN ('COMPLETED','FAILED','CANCELLED')",
            name="ck_bds_sessions_final_status",
        ),
    )
    op.create_index(
        "ix_bds_sessions_kind_completed",
        "bds_sessions",
        ["session_kind", "completed_at", "session_id"],
    )
    op.execute("ALTER TABLE bds_sessions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_bds_sessions_kind_completed", table_name="bds_sessions")
    op.drop_table("bds_sessions")

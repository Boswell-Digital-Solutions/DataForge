"""add healing_proposals

Pending self-healing code-fix proposals (Forge_Command inbox envelopes) awaiting
operator accept/reject.

Revision ID: 20260606_02
Revises: 20260606_01
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260606_02"
down_revision = "20260606_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "healing_proposals",
        sa.Column("proposal_id", sa.String(length=64), primary_key=True),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("repo_id", sa.String(length=128), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_index("ix_healing_proposals_status", "healing_proposals", ["status"])
    op.create_index("ix_healing_proposals_repo_id", "healing_proposals", ["repo_id"])
    op.create_index("ix_healing_proposals_severity", "healing_proposals", ["severity"])
    op.create_index("ix_healing_proposals_source_system", "healing_proposals", ["source_system"])
    op.create_index("ix_healing_proposals_created_at", "healing_proposals", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_healing_proposals_created_at", table_name="healing_proposals")
    op.drop_index("ix_healing_proposals_source_system", table_name="healing_proposals")
    op.drop_index("ix_healing_proposals_severity", table_name="healing_proposals")
    op.drop_index("ix_healing_proposals_repo_id", table_name="healing_proposals")
    op.drop_index("ix_healing_proposals_status", table_name="healing_proposals")
    op.drop_table("healing_proposals")

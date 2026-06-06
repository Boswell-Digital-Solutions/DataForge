"""drop healing_proposals

The healing_proposals feature (model + router + migration 20260606_02) was
reverted in application code. Some environments were already deployed at
revision 20260606_02 and therefore have the table present, while fresh
databases create it via 20260606_02. This migration drops the table in both
cases so the post-revert schema is consistent: no healing_proposals surface.

Revision ID: 20260606_03
Revises: 20260606_02
Create Date: 2026-06-06
"""

from alembic import op

revision = "20260606_03"
down_revision = "20260606_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DROP ... IF EXISTS CASCADE also removes dependent indexes, tolerating any
    # partial state left by the reverted feature.
    op.execute("DROP TABLE IF EXISTS healing_proposals CASCADE")


def downgrade() -> None:
    # Recreate the table to mirror 20260606_02's upgrade() if rolled back.
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

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

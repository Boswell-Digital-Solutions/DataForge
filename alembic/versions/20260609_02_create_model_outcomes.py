"""create model_outcomes (DataForge owns durable learning state)

Append-only ground-truth code-fix outcome receipts that teach NeuroForge's
(model, category) Category Champion Matrix. DataForge is the durable-truth
boundary; the matrix is a replayable projection of these rows.

Revision ID: 20260609_02
Revises: 20260609_01
Create Date: 2026-06-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260609_02"
down_revision = "20260609_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_outcomes",
        sa.Column("outcome_id", sa.String(128), primary_key=True),
        sa.Column("context_bundle_id", sa.Text(), nullable=False),
        sa.Column("task_intent_id", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column("routing_cell", sa.Text(), nullable=False),
        sa.Column("family", sa.Text(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("complexity", sa.Text(), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("reward", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("source_system", sa.Text(), nullable=False, server_default=sa.text("'forgehq'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_model_outcomes_routing_cell", "model_outcomes", ["routing_cell"])
    op.create_index("ix_model_outcomes_model_id", "model_outcomes", ["model_id"])
    op.create_index("ix_model_outcomes_context_bundle_id", "model_outcomes", ["context_bundle_id"])
    op.create_index("ix_model_outcomes_created_at", "model_outcomes", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_outcomes_created_at", table_name="model_outcomes")
    op.drop_index("ix_model_outcomes_context_bundle_id", table_name="model_outcomes")
    op.drop_index("ix_model_outcomes_model_id", table_name="model_outcomes")
    op.drop_index("ix_model_outcomes_routing_cell", table_name="model_outcomes")
    op.drop_table("model_outcomes")

"""create context_packs (cloud DataForge)

Cloud mirror of DataForge-Local's context-pack store. NeuroForge's Context Builder
fetches a governed precomputed pack by id (GET /df/rag/context-pack/{id}) and
serves inference from it instead of re-grounding — the faster/cheaper-tokens path.
Keyed by the governed context_bundle_id (ctxb_...). Holds NeuroForge's read
contract (primary / supporting / metadata).

Revision ID: 20260609_01
Revises: 20260606_03
Create Date: 2026-06-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260609_01"
down_revision = "20260606_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_packs",
        sa.Column("context_pack_id", sa.String(128), primary_key=True),
        sa.Column("bundle_hash", sa.Text(), nullable=False),
        sa.Column("task_intent_id", sa.Text(), nullable=True),
        sa.Column("primary_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "supporting_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_context_packs_task_intent_id", "context_packs", ["task_intent_id"])
    op.create_index("ix_context_packs_created_at", "context_packs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_context_packs_created_at", table_name="context_packs")
    op.drop_index("ix_context_packs_task_intent_id", table_name="context_packs")
    op.drop_table("context_packs")

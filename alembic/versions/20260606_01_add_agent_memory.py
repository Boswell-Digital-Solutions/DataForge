"""add agent memory store

Revision ID: 20260606_01
Revises: 20260528_02
Create Date: 2026-06-06 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260606_01"
down_revision = "20260528_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("doc_metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_memories_collection", "agent_memories", ["collection"])
    op.create_index("ix_agent_memories_agent_id", "agent_memories", ["agent_id"])
    op.create_index("ix_agent_memories_created_at", "agent_memories", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_memories_created_at", table_name="agent_memories")
    op.drop_index("ix_agent_memories_agent_id", table_name="agent_memories")
    op.drop_index("ix_agent_memories_collection", table_name="agent_memories")
    op.drop_table("agent_memories")

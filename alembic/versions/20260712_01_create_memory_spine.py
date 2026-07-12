"""create Forge Memory spine (FMEM-02) + merge heads

Merges the two prior alembic heads (20260623_01, add_tarcie_events) and creates
the typed, scoped, bitemporal memory tables.

Revision ID: fmem02_memory_spine
Revises: 20260623_01, add_tarcie_events
Create Date: 2026-07-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "fmem02_memory_spine"
down_revision = ("20260623_01", "add_tarcie_events")
branch_labels = None
depends_on = None


def _scope_columns() -> list[sa.Column]:
    return [
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("repo_id", sa.String(length=128), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "memory_episodes",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("episode_id", sa.String(length=64), nullable=False),
        *_scope_columns(),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("agent_id", sa.String(length=128), nullable=True),
        sa.Column("episode_type", sa.String(length=32), nullable=False),
        sa.Column("origin_class", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("residency", sa.String(length=32), nullable=False),
        sa.Column("sensitivity_class", sa.String(length=32), nullable=False),
        sa.Column("instruction_capability", sa.String(length=16), nullable=False),
        sa.Column("quarantined", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_episodes_tenant_id", "memory_episodes", ["tenant_id"])
    op.create_index("ix_memory_episodes_episode_id", "memory_episodes", ["episode_id"])

    op.create_table(
        "memory_claims",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        *_scope_columns(),
        sa.Column("subject_entity_id", sa.String(length=256), nullable=False),
        sa.Column("predicate", sa.String(length=256), nullable=False),
        sa.Column("object", sa.Text(), nullable=False),
        sa.Column("authority_class", sa.String(length=32), nullable=False),
        sa.Column("trust_state", sa.String(length=32), nullable=False),
        sa.Column("verification_state", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_claims_tenant_id", "memory_claims", ["tenant_id"])
    op.create_index("ix_memory_claims_subject_entity_id", "memory_claims", ["subject_entity_id"])
    op.create_index("ix_memory_claims_predicate", "memory_claims", ["predicate"])

    op.create_table(
        "memory_facts",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        *_scope_columns(),
        sa.Column("subject_entity_id", sa.String(length=256), nullable=False),
        sa.Column("predicate", sa.String(length=256), nullable=False),
        sa.Column("object", sa.Text(), nullable=False),
        sa.Column("authority_class", sa.String(length=32), nullable=False),
        sa.Column("trust_state", sa.String(length=32), nullable=False),
        sa.Column("verification_state", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_memory_id", sa.String(length=64), nullable=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_facts_tenant_id", "memory_facts", ["tenant_id"])
    op.create_index("ix_memory_facts_memory_id", "memory_facts", ["memory_id"])
    op.create_index("ix_memory_facts_subject_entity_id", "memory_facts", ["subject_entity_id"])
    op.create_index("ix_memory_facts_predicate", "memory_facts", ["predicate"])
    op.create_index("ix_memory_facts_status", "memory_facts", ["status"])
    op.create_index("ix_memory_facts_valid_from", "memory_facts", ["valid_from"])
    op.create_index("ix_memory_facts_valid_to", "memory_facts", ["valid_to"])
    op.create_index(
        "ix_memory_facts_current",
        "memory_facts",
        ["tenant_id", "subject_entity_id", "predicate", "status"],
    )
    op.create_index("ix_memory_facts_temporal", "memory_facts", ["valid_from", "valid_to"])

    op.create_table(
        "memory_receipts",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("receipt_kind", sa.String(length=32), nullable=False),
        *_scope_columns(),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_receipts_receipt_kind", "memory_receipts", ["receipt_kind"])
    op.create_index("ix_memory_receipts_tenant_id", "memory_receipts", ["tenant_id"])

    op.create_table(
        "memory_deletions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("target_family", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_deletions_target_id", "memory_deletions", ["target_id"])
    op.create_index("ix_memory_deletions_tenant_id", "memory_deletions", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("memory_deletions")
    op.drop_table("memory_receipts")
    op.drop_table("memory_facts")
    op.drop_table("memory_claims")
    op.drop_table("memory_episodes")

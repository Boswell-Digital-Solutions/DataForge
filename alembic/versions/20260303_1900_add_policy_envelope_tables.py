"""Add deterministic policy envelope tables.

Revision ID: policy_envelope_001
Revises: corpus_governance_001
Create Date: 2026-03-03 19:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "policy_envelope_001"
down_revision: Union[str, Sequence[str], None] = "corpus_governance_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_policy_envelopes",
        sa.Column("policy_key", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("policy_key"),
    )
    op.create_index(
        "ix_llm_policy_envelopes_policy_version",
        "llm_policy_envelopes",
        ["policy_version"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_envelopes_is_active",
        "llm_policy_envelopes",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "llm_policy_run_ledger",
        sa.Column("ledger_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("policy_key", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_estimated_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("termination_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "entry_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("ledger_id"),
        sa.UniqueConstraint(
            "run_id",
            "sequence_no",
            name="uq_llm_policy_run_ledger_sequence",
        ),
    )
    op.create_index(
        "ix_llm_policy_run_ledger_run_id",
        "llm_policy_run_ledger",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_ledger_policy_key",
        "llm_policy_run_ledger",
        ["policy_key"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_ledger_model",
        "llm_policy_run_ledger",
        ["model"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_ledger_termination_reason",
        "llm_policy_run_ledger",
        ["termination_reason"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_ledger_run_sequence",
        "llm_policy_run_ledger",
        ["run_id", "sequence_no"],
        unique=False,
    )

    op.create_table(
        "llm_policy_run_finalizations",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("policy_key", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("termination_reason", sa.String(length=64), nullable=True),
        sa.Column("total_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finalization_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_llm_policy_run_finalizations_policy_key",
        "llm_policy_run_finalizations",
        ["policy_key"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_finalizations_status",
        "llm_policy_run_finalizations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_run_finalizations_termination_reason",
        "llm_policy_run_finalizations",
        ["termination_reason"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_policy_run_finalizations_termination_reason",
        table_name="llm_policy_run_finalizations",
    )
    op.drop_index("ix_llm_policy_run_finalizations_status", table_name="llm_policy_run_finalizations")
    op.drop_index(
        "ix_llm_policy_run_finalizations_policy_key",
        table_name="llm_policy_run_finalizations",
    )
    op.drop_table("llm_policy_run_finalizations")

    op.drop_index("ix_llm_policy_run_ledger_run_sequence", table_name="llm_policy_run_ledger")
    op.drop_index(
        "ix_llm_policy_run_ledger_termination_reason",
        table_name="llm_policy_run_ledger",
    )
    op.drop_index("ix_llm_policy_run_ledger_model", table_name="llm_policy_run_ledger")
    op.drop_index("ix_llm_policy_run_ledger_policy_key", table_name="llm_policy_run_ledger")
    op.drop_index("ix_llm_policy_run_ledger_run_id", table_name="llm_policy_run_ledger")
    op.drop_table("llm_policy_run_ledger")

    op.drop_index("ix_llm_policy_envelopes_is_active", table_name="llm_policy_envelopes")
    op.drop_index(
        "ix_llm_policy_envelopes_policy_version",
        table_name="llm_policy_envelopes",
    )
    op.drop_table("llm_policy_envelopes")

"""Add Slice 2 policy routing tables.

Revision ID: policy_envelope_002
Revises: policy_envelope_001
Create Date: 2026-03-04 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "policy_envelope_002"
down_revision: Union[str, Sequence[str], None] = "policy_envelope_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_policy_bandit_states",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("policy_key", sa.String(length=128), nullable=False),
        sa.Column("partition_key", sa.String(length=256), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("bandit_policy_id", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "state_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("tenant_id", "policy_key", "partition_key"),
    )
    op.create_index(
        "ix_llm_policy_bandit_states_bandit_policy_id",
        "llm_policy_bandit_states",
        ["bandit_policy_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_bandit_states_tenant_policy",
        "llm_policy_bandit_states",
        ["tenant_id", "policy_key"],
        unique=False,
    )

    op.create_table(
        "llm_policy_reward_records",
        sa.Column("call_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("policy_key", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("partition_key", sa.String(length=256), nullable=False),
        sa.Column("action_id", sa.String(length=256), nullable=False),
        sa.Column("bandit_policy_id", sa.String(length=32), nullable=False),
        sa.Column("reward_version", sa.String(length=32), nullable=False),
        sa.Column("reward_value", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("router_degraded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "reward_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("call_id"),
    )
    op.create_index(
        "ix_llm_policy_reward_records_run_id",
        "llm_policy_reward_records",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_tenant_id",
        "llm_policy_reward_records",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_policy_key",
        "llm_policy_reward_records",
        ["policy_key"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_partition_key",
        "llm_policy_reward_records",
        ["partition_key"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_action_id",
        "llm_policy_reward_records",
        ["action_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_bandit_policy_id",
        "llm_policy_reward_records",
        ["bandit_policy_id"],
        unique=False,
    )
    op.create_index(
        "ix_llm_policy_reward_records_tenant_policy_created",
        "llm_policy_reward_records",
        ["tenant_id", "policy_key", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_policy_reward_records_tenant_policy_created",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_bandit_policy_id",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_action_id",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_partition_key",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_policy_key",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_tenant_id",
        table_name="llm_policy_reward_records",
    )
    op.drop_index(
        "ix_llm_policy_reward_records_run_id",
        table_name="llm_policy_reward_records",
    )
    op.drop_table("llm_policy_reward_records")

    op.drop_index(
        "ix_llm_policy_bandit_states_tenant_policy",
        table_name="llm_policy_bandit_states",
    )
    op.drop_index(
        "ix_llm_policy_bandit_states_bandit_policy_id",
        table_name="llm_policy_bandit_states",
    )
    op.drop_table("llm_policy_bandit_states")

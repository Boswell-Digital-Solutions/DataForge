"""create CSSA security ledger (append-only) + anti-rollback counters

DataForge owns the durable append-only security ledger (CSSA authority plan
§22, §30; Phase 0 acceptance §6). Decisions, authorizations, and outcomes are
immutable records written by the ForgeAgents CSSA recorder; cardinality is
enforced at the database level:

  - one decision and one authorization per governed attempt (unique indexes)
  - at most one TERMINAL outcome per attempt (partial unique index)

cssa_counters backs the ForgeAgents anti-rollback high-water marks
(policy bundle / entitlement snapshot versions) so they survive restarts.

Revision ID: 20260612_01
Revises: 20260609_02
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260612_01"
down_revision = "20260609_02"
branch_labels = None
depends_on = None


def _record_table(name: str, id_column: str) -> None:
    op.create_table(
        name,
        sa.Column(id_column, sa.String(128), primary_key=True),
        sa.Column("attempt_id", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("record_hash", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def upgrade() -> None:
    _record_table("cssa_decisions", "decision_id")
    op.create_index(
        "ix_cssa_decisions_attempt_unique", "cssa_decisions", ["attempt_id"], unique=True
    )

    _record_table("cssa_authorizations", "authorization_id")
    op.create_index(
        "ix_cssa_authorizations_attempt_unique",
        "cssa_authorizations",
        ["attempt_id"],
        unique=True,
    )

    _record_table("cssa_outcomes", "outcome_id")
    op.add_column("cssa_outcomes", sa.Column("terminal", sa.Boolean(), nullable=False))
    op.create_index(
        "ix_cssa_outcomes_attempt_terminal_unique",
        "cssa_outcomes",
        ["attempt_id"],
        unique=True,
        postgresql_where=sa.text("terminal"),
        sqlite_where=sa.text("terminal"),
    )

    op.create_table(
        "cssa_counters",
        sa.Column("counter", sa.String(128), primary_key=True),
        sa.Column("high_water", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("cssa_counters")
    op.drop_table("cssa_outcomes")
    op.drop_table("cssa_authorizations")
    op.drop_table("cssa_decisions")

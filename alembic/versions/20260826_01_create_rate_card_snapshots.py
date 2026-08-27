"""create rate_card_snapshots (Cost Provenance Tranche 3, RFC-CP-03)

Durable store for RateCardSnapshot.v1 (forge_contract_core, RFC-CP-02).
NeuroForge's promote_rate_card_candidate.py CLI is the sole writer;
DataForge_Local mirrors this table via a read-through cache in front of
the same /api/v1/rate-cards endpoint contract.

Revision ID: 20260826_01
Revises: 20260725_03
Create Date: 2026-08-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260826_01"
down_revision = "20260725_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_card_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(256), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("uncached_input_rate_micros_per_million_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_rate_micros_per_million_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_write_rate_micros_per_million_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_rate_micros_per_million_tokens", sa.Integer(), nullable=True),
        sa.Column("output_rate_micros_per_million_tokens", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("retrieved_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(256), nullable=True),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rounding_rule", sa.String(64), nullable=False),
        sa.Column("digest", sa.String(80), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('CANDIDATE','ACTIVE','EXPIRED','SUPERSEDED','REVOKED')",
            name="ck_rate_card_status",
        ),
        sa.CheckConstraint(
            "uncached_input_rate_micros_per_million_tokens IS NULL OR uncached_input_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_uncached_input_nonneg",
        ),
        sa.CheckConstraint(
            "cached_input_rate_micros_per_million_tokens IS NULL OR cached_input_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_cached_input_nonneg",
        ),
        sa.CheckConstraint(
            "cache_write_rate_micros_per_million_tokens IS NULL OR cache_write_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_cache_write_nonneg",
        ),
        sa.CheckConstraint(
            "reasoning_rate_micros_per_million_tokens IS NULL OR reasoning_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_reasoning_nonneg",
        ),
        sa.CheckConstraint(
            "output_rate_micros_per_million_tokens IS NULL OR output_rate_micros_per_million_tokens >= 0",
            name="ck_rate_card_output_nonneg",
        ),
    )
    op.create_index(
        "ix_rate_card_lookup",
        "rate_card_snapshots",
        ["provider", "model", "model_version", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_card_lookup", table_name="rate_card_snapshots")
    op.drop_table("rate_card_snapshots")

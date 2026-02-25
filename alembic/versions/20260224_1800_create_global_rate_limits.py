"""Create global_rate_limits table for cross-run XAI/MAID rate limiting.

Revision ID: rate_limits_001
Revises: sentinel_001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "rate_limits_001"
down_revision: Union[str, Sequence[str], None] = "sentinel_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── global_rate_limits ──────────────────────────────────
    op.create_table(
        "global_rate_limits",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(30), nullable=False, comment="xai or maid"),
        sa.Column(
            "window_start",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Start of the current rate-limit window",
        ),
        sa.Column(
            "window_duration_seconds",
            sa.Integer,
            nullable=False,
            comment="Duration of the window in seconds",
        ),
        sa.Column(
            "current_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Number of requests in the current window",
        ),
        sa.Column(
            "max_count",
            sa.Integer,
            nullable=False,
            comment="Maximum requests allowed in the window",
        ),
        sa.Column(
            "cost_usd",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0",
            comment="Accumulated cost in USD for the window",
        ),
        sa.Column(
            "max_cost_usd",
            sa.Numeric(10, 4),
            nullable=True,
            comment="Maximum cost allowed for the window",
        ),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Additional tracking metadata",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "provider IN ('xai', 'maid')",
            name="ck_rate_limits_provider",
        ),
        sa.UniqueConstraint("provider", "window_start", name="uq_rate_limits_provider_window"),
    )
    op.create_index("ix_rate_limits_provider", "global_rate_limits", ["provider"])
    op.create_index("ix_rate_limits_window_start", "global_rate_limits", ["window_start"])


def downgrade() -> None:
    op.drop_table("global_rate_limits")

"""create supabase_log_events (redacted Supabase log mirror)

DataForge owns a durable, redacted copy of security/operational Supabase log
entries, pulled on a schedule by scripts/poll_supabase_logs.py. The id column is
the Supabase log id (UUID string) so re-pulling an overlapping window is
idempotent via INSERT ... ON CONFLICT (id) DO NOTHING. Sensitive request fields
are stripped before insert (app/utils/supabase_log_ingest.py).

Revision ID: 20260623_01
Revises: 20260612_02
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260623_01"
down_revision = "20260612_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supabase_log_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("log_type", sa.String(40), nullable=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("method", sa.String(10), nullable=True),
        sa.Column("pathname", sa.String(500), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("source", sa.String(20), nullable=False, server_default="supabase"),
        sa.Column("redacted", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_cursor", sa.String(64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_supabase_log_events_event_time", "supabase_log_events", ["event_time"]
    )
    op.create_index(
        "ix_supabase_log_events_log_type", "supabase_log_events", ["log_type"]
    )
    op.create_index(
        "ix_supabase_log_events_category_time",
        "supabase_log_events",
        ["category", "event_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_supabase_log_events_category_time", table_name="supabase_log_events")
    op.drop_index("ix_supabase_log_events_log_type", table_name="supabase_log_events")
    op.drop_index("ix_supabase_log_events_event_time", table_name="supabase_log_events")
    op.drop_table("supabase_log_events")

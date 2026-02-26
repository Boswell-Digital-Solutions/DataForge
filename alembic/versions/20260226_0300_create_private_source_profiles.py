"""Create private_source_profiles table for PSIM.

Revision ID: private_source_profiles_001
Revises: routing_decisions_001
Create Date: 2026-02-26

Stores operator-curated private source configurations for authenticated
crawling via ForgeCommand. Credentials live in OS keyring; only profile
metadata is persisted here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'private_source_profiles_001'
down_revision: Union[str, Sequence[str], None] = 'routing_decisions_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS private_source_profiles (
            id              SERIAL PRIMARY KEY,
            workspace_id    VARCHAR(255) NOT NULL,
            name            VARCHAR(255) NOT NULL,
            description     TEXT,
            source_type     VARCHAR(50) NOT NULL DEFAULT 'web',
            base_url        VARCHAR(2048) NOT NULL,
            allowed_paths   JSONB NOT NULL DEFAULT '[]'::jsonb,
            auth_type       VARCHAR(50) NOT NULL DEFAULT 'cookie',
            config          JSONB NOT NULL DEFAULT '{}'::jsonb,
            quality_gates   JSONB,
            is_active       BOOLEAN NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_psp_auth_type
                CHECK (auth_type IN ('cookie', 'bearer', 'basic', 'header')),
            CONSTRAINT ck_psp_source_type
                CHECK (source_type IN ('web', 'api', 'rss'))
        )
    """))

    # Indexes
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_psp_workspace_id "
        "ON private_source_profiles(workspace_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_psp_is_active "
        "ON private_source_profiles(is_active)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_psp_created_at "
        "ON private_source_profiles(created_at)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_psp_workspace_active "
        "ON private_source_profiles(workspace_id, is_active)"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_psp_workspace_name "
        "ON private_source_profiles(workspace_id, name)"
    ))


def downgrade() -> None:
    op.drop_index('ix_psp_workspace_name', table_name='private_source_profiles')
    op.drop_index('ix_psp_workspace_active', table_name='private_source_profiles')
    op.drop_index('ix_psp_created_at', table_name='private_source_profiles')
    op.drop_index('ix_psp_is_active', table_name='private_source_profiles')
    op.drop_index('ix_psp_workspace_id', table_name='private_source_profiles')
    op.drop_table('private_source_profiles')

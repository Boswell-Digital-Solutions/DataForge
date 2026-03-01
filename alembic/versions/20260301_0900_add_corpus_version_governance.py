"""Add corpus version governance tables.

Revision ID: corpus_governance_001
Revises: private_source_profiles_001
Create Date: 2026-03-01 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "corpus_governance_001"
down_revision: Union[str, Sequence[str], None] = "private_source_profiles_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS corpus_state (
                id INTEGER PRIMARY KEY,
                current_version INTEGER NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS corpus_versions (
                id SERIAL PRIMARY KEY,
                version INTEGER NOT NULL UNIQUE,
                trigger_event VARCHAR(50) NOT NULL,
                trigger_entity_id INTEGER NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO corpus_state (id, current_version)
            VALUES (1, 1)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO corpus_versions (version, trigger_event, trigger_entity_id)
            VALUES (1, 'initial', NULL)
            ON CONFLICT (version) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("corpus_versions")
    op.drop_table("corpus_state")

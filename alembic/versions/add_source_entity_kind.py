"""add 'source' to entitykind enum (E1: Rake → Lore bridge)

Revision ID: entity_source_001
Revises: collab_001
Create Date: 2026-02-20

Extends the PostgreSQL entitykind ENUM with 'source' so that Rake
research jobs can auto-create Lore source entities via the E1 bridge
in AuthorForge's rakeStore.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'entity_source_001'
down_revision: Union[str, Sequence[str], None] = 'collab_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE entitykind ADD VALUE IF NOT EXISTS 'source'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an ENUM type.
    # To fully reverse, recreate the type without 'source' and migrate
    # the column. In practice this value is safe to leave in place.
    pass

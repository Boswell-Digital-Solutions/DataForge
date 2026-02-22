"""Add parent_of and cites to edgetype enum

Revision ID: edge_cites_001
Revises: gallery_collections_001
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'edge_cites_001'
down_revision: Union[str, Sequence[str], None] = 'gallery_collections_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new edge types to the edgetype enum (idempotent)
    op.execute("""
        DO $$
        BEGIN
            ALTER TYPE edgetype ADD VALUE IF NOT EXISTS 'parent_of';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            ALTER TYPE edgetype ADD VALUE IF NOT EXISTS 'cites';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # To reverse: recreate the enum without 'parent_of' and 'cites',
    # update the column, then swap. Intentionally left as no-op.
    pass

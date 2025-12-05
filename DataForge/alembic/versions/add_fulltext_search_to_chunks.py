"""add_fulltext_search_to_chunks

Revision ID: 7f3a8b9c2d4e
Revises: 4bae83731016
Create Date: 2025-12-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3a8b9c2d4e'
down_revision: Union[str, Sequence[str], None] = '4bae83731016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search support to chunks table."""

    # Add tsvector column for full-text search
    op.add_column('chunks', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))

    # Create function to update search_vector from content
    op.execute("""
        CREATE OR REPLACE FUNCTION chunks_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update search_vector on INSERT or UPDATE
    op.execute("""
        CREATE TRIGGER chunks_search_vector_trigger
        BEFORE INSERT OR UPDATE ON chunks
        FOR EACH ROW
        EXECUTE FUNCTION chunks_search_vector_update();
    """)

    # Populate search_vector for existing rows
    op.execute("""
        UPDATE chunks
        SET search_vector = to_tsvector('english', COALESCE(content, ''))
        WHERE search_vector IS NULL;
    """)

    # Make search_vector NOT NULL after populating existing rows
    op.alter_column('chunks', 'search_vector', nullable=False)

    # Create GIN index for fast full-text search
    op.create_index(
        'idx_chunks_search_vector',
        'chunks',
        ['search_vector'],
        postgresql_using='gin'
    )

    # Create composite index for filtered searches (common pattern: filter by document, search content)
    op.create_index(
        'idx_chunks_document_search',
        'chunks',
        ['document_id', 'search_vector'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove full-text search support from chunks table."""

    # Drop indexes
    op.drop_index('idx_chunks_document_search', table_name='chunks')
    op.drop_index('idx_chunks_search_vector', table_name='chunks')

    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON chunks')

    # Drop function
    op.execute('DROP FUNCTION IF EXISTS chunks_search_vector_update()')

    # Drop column
    op.drop_column('chunks', 'search_vector')

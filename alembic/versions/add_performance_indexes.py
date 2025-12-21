"""
Database Performance Optimization Migration

Adds:
- Index on DiligenceProject.user_id for faster queries
- Index on DiligenceReview.status for filtering reviews by status
- Index on DiligenceFinding.status for filtering findings by status
- Composite indexes for common query patterns

These indexes significantly improve query performance for large datasets.
"""
from alembic import op  # type: ignore
import sqlalchemy as sa


# Revision identifiers (these would normally be auto-generated)
revision: str = 'performance_indexes_001'
down_revision: str | None = None  # Will be set by migration system
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add performance indexes."""
    from sqlalchemy import inspect
    from alembic import context

    # Get connection and check if tables exist
    conn = context.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Only create indexes if tables exist
    if 'diligence_project' not in existing_tables:
        return  # Skip if diligence tables don't exist yet

    # Index on user_id for projects (very common query pattern)
    op.create_index(
        'idx_diligence_project_user_id',
        'diligence_project',
        ['user_id'],
        unique=False
    )
    
    # Index on project_id + user_id (for ownership verification)
    op.create_index(
        'idx_diligence_project_user_id_project_id',
        'diligence_project',
        ['user_id', 'id'],
        unique=False
    )
    
    # Index on created_at for sorting
    op.create_index(
        'idx_diligence_project_created_at',
        'diligence_project',
        ['created_at'],
        unique=False
    )
    
    # Index on review status for filtering
    op.create_index(
        'idx_diligence_review_status',
        'diligence_review',
        ['overall_rating'],
        unique=False
    )
    
    # Index on project_id + review_date for latest reviews query
    op.create_index(
        'idx_diligence_review_project_id_date',
        'diligence_review',
        ['project_id', 'review_date'],
        unique=False
    )
    
    # Index on finding status for filtering
    op.create_index(
        'idx_diligence_finding_status',
        'diligence_finding',
        ['status'],
        unique=False
    )
    
    # Index on review_id for review findings
    op.create_index(
        'idx_diligence_finding_review_id',
        'diligence_finding',
        ['review_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_diligence_project_user_id', table_name='diligence_project')
    op.drop_index('idx_diligence_project_user_id_project_id', table_name='diligence_project')
    op.drop_index('idx_diligence_project_created_at', table_name='diligence_project')
    op.drop_index('idx_diligence_review_status', table_name='diligence_review')
    op.drop_index('idx_diligence_review_project_id_date', table_name='diligence_review')
    op.drop_index('idx_diligence_finding_status', table_name='diligence_finding')
    op.drop_index('idx_diligence_finding_review_id', table_name='diligence_finding')

"""Add Rake jobs table for pipeline tracking

Revision ID: 20251216_1900
Revises: 34fa1f6a4cbd
Create Date: 2025-12-16 19:00:00

This migration adds the jobs table from the Rake service to support
the consolidated database architecture where DataForge owns all tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251216_1900'
down_revision: Union[str, None] = '34fa1f6a4cbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jobs table with indexes for Rake pipeline tracking."""
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('documents_stored', sa.Integer(), nullable=True),
        sa.Column('chunks_created', sa.Integer(), nullable=True),
        sa.Column('embeddings_generated', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('stages_completed', sa.JSON(), nullable=True),
        sa.Column('source_params', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )

    # Create indexes for common queries
    op.create_index('idx_job_id', 'jobs', ['job_id'], unique=True)
    op.create_index('idx_correlation_id', 'jobs', ['correlation_id'])
    op.create_index('idx_source', 'jobs', ['source'])
    op.create_index('idx_status', 'jobs', ['status'])
    op.create_index('idx_tenant_id', 'jobs', ['tenant_id'])
    op.create_index('idx_created_at', 'jobs', ['created_at'])

    # Composite indexes for common query patterns
    op.create_index('idx_jobs_tenant_status', 'jobs', ['tenant_id', 'status'])
    op.create_index('idx_jobs_tenant_created', 'jobs', ['tenant_id', 'created_at'])
    op.create_index('idx_jobs_status_created', 'jobs', ['status', 'created_at'])


def downgrade() -> None:
    """Drop jobs table and all indexes."""
    op.drop_index('idx_jobs_status_created', table_name='jobs')
    op.drop_index('idx_jobs_tenant_created', table_name='jobs')
    op.drop_index('idx_jobs_tenant_status', table_name='jobs')
    op.drop_index('idx_created_at', table_name='jobs')
    op.drop_index('idx_tenant_id', table_name='jobs')
    op.drop_index('idx_status', table_name='jobs')
    op.drop_index('idx_source', table_name='jobs')
    op.drop_index('idx_correlation_id', table_name='jobs')
    op.drop_index('idx_job_id', table_name='jobs')
    op.drop_table('jobs')

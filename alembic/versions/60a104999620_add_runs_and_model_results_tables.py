"""add runs and model_results tables

Revision ID: 60a104999620
Revises: 34fa1f6a4cbd
Create Date: 2025-11-21 22:09:57.469295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60a104999620'
down_revision: Union[str, Sequence[str], None] = '34fa1f6a4cbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create runs table
    op.create_table(
        'runs',
        sa.Column('run_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('prompt_snapshot', sa.Text(), nullable=False),
        sa.Column('context_block_ids', sa.dialects.postgresql.JSON(), nullable=True),
        sa.Column('total_latency_ms', sa.Float(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('total_cost_usd', sa.Float(), nullable=False),
        sa.Column('tags', sa.dialects.postgresql.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('run_id')
    )
    
    # Create indexes for runs
    op.create_index('ix_runs_run_id', 'runs', ['run_id'])
    op.create_index('ix_runs_workspace_id', 'runs', ['workspace_id'])
    op.create_index('ix_runs_status', 'runs', ['status'])
    op.create_index('ix_runs_created_at', 'runs', ['created_at'])
    op.create_index('idx_workspace_created', 'runs', ['workspace_id', 'created_at'])
    op.create_index('idx_workspace_status', 'runs', ['workspace_id', 'status'])
    op.create_index('idx_created_status', 'runs', ['created_at', 'status'])
    
    # Create model_results table
    op.create_table(
        'model_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=255), nullable=False),
        sa.Column('model_id', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for model_results
    op.create_index('ix_model_results_id', 'model_results', ['id'])
    op.create_index('ix_model_results_run_id', 'model_results', ['run_id'])
    op.create_index('ix_model_results_model_id', 'model_results', ['model_id'])
    op.create_index('ix_model_results_provider', 'model_results', ['provider'])
    op.create_index('idx_run_model', 'model_results', ['run_id', 'model_id'])
    op.create_index('idx_provider_model', 'model_results', ['provider', 'model_id'])
    op.create_index('idx_model_created', 'model_results', ['model_id', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop model_results table and indexes
    op.drop_index('idx_model_created', table_name='model_results')
    op.drop_index('idx_provider_model', table_name='model_results')
    op.drop_index('idx_run_model', table_name='model_results')
    op.drop_index('ix_model_results_provider', table_name='model_results')
    op.drop_index('ix_model_results_model_id', table_name='model_results')
    op.drop_index('ix_model_results_run_id', table_name='model_results')
    op.drop_index('ix_model_results_id', table_name='model_results')
    op.drop_table('model_results')
    
    # Drop runs table and indexes
    op.drop_index('idx_created_status', table_name='runs')
    op.drop_index('idx_workspace_status', table_name='runs')
    op.drop_index('idx_workspace_created', table_name='runs')
    op.drop_index('ix_runs_created_at', table_name='runs')
    op.drop_index('ix_runs_status', table_name='runs')
    op.drop_index('ix_runs_workspace_id', table_name='runs')
    op.drop_index('ix_runs_run_id', table_name='runs')
    op.drop_table('runs')

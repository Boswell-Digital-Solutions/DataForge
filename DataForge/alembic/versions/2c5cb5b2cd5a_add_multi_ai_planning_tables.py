"""add_multi_ai_planning_tables

Revision ID: 2c5cb5b2cd5a
Revises: 2a208f07b7fd
Create Date: 2025-11-27 04:50:39.626967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c5cb5b2cd5a'
down_revision: Union[str, Sequence[str], None] = '2a208f07b7fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add Multi-AI Planning System tables."""

    # Create planning_outcomes table
    op.create_table(
        'planning_outcomes',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string for SQLite compatibility
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),

        # Session context
        sa.Column('session_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=True),

        # Request metadata
        sa.Column('workflow_type', sa.String(50), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=True),
        sa.Column('request_complexity', sa.String(20), nullable=True),
        sa.Column('codebase_context', sa.JSON, nullable=True),

        # Stage-by-stage results (JSON array)
        sa.Column('stages', sa.JSON, nullable=False),

        # Aggregates
        sa.Column('total_duration_ms', sa.Integer, nullable=True),
        sa.Column('total_tokens_used', sa.Integer, nullable=True),
        sa.Column('total_cost_cents', sa.Integer, nullable=True),
        sa.Column('iteration_count', sa.Integer, default=1),

        # Execution outcome
        sa.Column('execution_started', sa.Boolean, default=False),
        sa.Column('execution_success', sa.Boolean, nullable=True),
        sa.Column('execution_duration_seconds', sa.Integer, nullable=True),
        sa.Column('tasks_completed', sa.Integer, nullable=True),
        sa.Column('tasks_failed', sa.Integer, nullable=True),

        # User feedback
        sa.Column('user_rating', sa.Integer, nullable=True),
        sa.Column('user_feedback', sa.Text, nullable=True),
        sa.Column('plan_was_modified', sa.Boolean, default=False),
        sa.Column('modification_extent', sa.Float, nullable=True),
    )

    op.create_index('idx_planning_outcomes_created', 'planning_outcomes', ['created_at'])
    op.create_index('idx_planning_outcomes_task', 'planning_outcomes', ['task_type', 'workflow_type'])

    # Create planning_model_performance table (renamed to avoid conflict with existing model_performance)
    op.create_table(
        'planning_model_performance',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),

        # Dimensions
        sa.Column('model', sa.String(100), nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False, index=True),
        sa.Column('stage_type', sa.String(50), nullable=False, index=True),
        sa.Column('task_type', sa.String(50), default='general', index=True),

        # Raw aggregates
        sa.Column('sample_count', sa.Integer, default=0),
        sa.Column('total_duration_ms', sa.BigInteger, default=0),
        sa.Column('total_tokens', sa.BigInteger, default=0),
        sa.Column('success_count', sa.Integer, default=0),

        # Calculated averages
        sa.Column('avg_duration_ms', sa.Float, nullable=True),
        sa.Column('avg_tokens', sa.Float, nullable=True),
        sa.Column('avg_quality_score', sa.Float, nullable=True),
        sa.Column('success_rate', sa.Float, nullable=True),

        # EMA values
        sa.Column('ema_duration_ms', sa.Float, nullable=True),
        sa.Column('ema_quality', sa.Float, nullable=True),
        sa.Column('ema_alpha', sa.Float, default=0.1),

        # Cost tracking
        sa.Column('avg_cost_cents', sa.Float, nullable=True),
    )

    op.create_index('idx_planning_model_perf_lookup', 'planning_model_performance',
                    ['model', 'provider', 'stage_type'])
    op.create_index('idx_planning_model_perf_task', 'planning_model_performance',
                    ['task_type', 'stage_type'])

    # Create ai_estimation_feedback table
    op.create_table(
        'ai_estimation_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),

        # Task context
        sa.Column('task_category', sa.String(50), nullable=False, index=True),
        sa.Column('task_complexity', sa.String(20), nullable=True),

        # Estimation vs actual
        sa.Column('estimated_minutes', sa.Float, nullable=False),
        sa.Column('actual_minutes', sa.Float, nullable=False),
        sa.Column('accuracy_ratio', sa.Float, nullable=True),

        # Execution context
        sa.Column('executor_type', sa.String(30), nullable=False, index=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('codebase_lines', sa.Integer, nullable=True),

        # Factors
        sa.Column('factors', sa.JSON, nullable=True),

        # User context
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
    )

    op.create_index('idx_estimation_task', 'ai_estimation_feedback',
                    ['task_category', 'executor_type'])
    op.create_index('idx_estimation_created', 'ai_estimation_feedback', ['created_at'])


def downgrade() -> None:
    """Downgrade schema - Remove Multi-AI Planning System tables."""
    op.drop_table('ai_estimation_feedback')
    op.drop_table('planning_model_performance')
    op.drop_table('planning_outcomes')

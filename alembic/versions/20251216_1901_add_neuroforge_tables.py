"""Add NeuroForge tables for inference tracking

Revision ID: 20251216_1901
Revises: 20251216_1900
Create Date: 2025-12-16 19:01:00.000000

This migration adds all NeuroForge tables to the shared forge-db database:
- inferences: LLM inference execution records
- model_metrics: Model performance metrics
- champion_states: Champion model rotation history
- evaluation_metrics: Detailed evaluation scores

NeuroForge is now a DATABASE CONSUMER - this migration is owned by DataForge.
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251216_1901'
down_revision: Union[str, None] = '20251216_1900'
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    # Create inferences table
    op.create_table(
        'inferences',
        sa.Column('inference_id', sa.String(length=36), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('context_pack_id', sa.String(length=256), nullable=False),
        sa.Column('user_query', sa.String(length=10000), nullable=False),
        sa.Column('model_id', sa.String(length=256), nullable=False),
        sa.Column('model_provider', sa.String(length=50), nullable=False),
        sa.Column('output', sa.String(length=16000), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('evaluation_score', sa.Float(), nullable=True),
        sa.Column('evaluation_passed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('evaluation_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint('inference_id')
    )

    # Create indexes for inferences
    op.create_index('ix_inferences_inference_id', 'inferences', ['inference_id'], unique=False)
    op.create_index('ix_inferences_domain', 'inferences', ['domain'], unique=False)
    op.create_index('ix_inferences_task_type', 'inferences', ['task_type'], unique=False)
    op.create_index('ix_inferences_model_id', 'inferences', ['model_id'], unique=False)
    op.create_index('ix_inferences_created_at', 'inferences', ['created_at'], unique=False)
    op.create_index('ix_inferences_status', 'inferences', ['status'], unique=False)

    # Composite indexes for inferences
    op.create_index('ix_inferences_domain_task_type', 'inferences', ['domain', 'task_type'], unique=False)
    op.create_index('ix_inferences_model_id_created_at', 'inferences', ['model_id', 'created_at'], unique=False)

    # Create model_metrics table
    op.create_table(
        'model_metrics',
        sa.Column('metric_id', sa.String(length=36), nullable=False),
        sa.Column('model_id', sa.String(length=256), nullable=False),
        sa.Column('model_provider', sa.String(length=50), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('total_inferences', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_inferences', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_inferences', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('average_latency_ms', sa.Float(), nullable=True),
        sa.Column('average_tokens_used', sa.Float(), nullable=True),
        sa.Column('average_evaluation_score', sa.Float(), nullable=True),
        sa.Column('pass_rate', sa.Float(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('window_start', sa.DateTime(), nullable=True),
        sa.Column('window_end', sa.DateTime(), nullable=True),
        sa.Column('is_champion', sa.Boolean(), nullable=True, server_default='false'),
        sa.PrimaryKeyConstraint('metric_id')
    )

    # Create indexes for model_metrics
    op.create_index('ix_model_metrics_metric_id', 'model_metrics', ['metric_id'], unique=False)
    op.create_index('ix_model_metrics_model_id', 'model_metrics', ['model_id'], unique=False)
    op.create_index('ix_model_metrics_domain', 'model_metrics', ['domain'], unique=False)
    op.create_index('ix_model_metrics_task_type', 'model_metrics', ['task_type'], unique=False)
    op.create_index('ix_model_metrics_is_champion', 'model_metrics', ['is_champion'], unique=False)
    op.create_index('ix_model_metrics_updated_at', 'model_metrics', ['updated_at'], unique=False)

    # Composite indexes for model_metrics
    op.create_index('ix_model_metrics_domain_task_type', 'model_metrics', ['domain', 'task_type'], unique=False)
    op.create_index('ix_model_metrics_model_id_domain_task', 'model_metrics', ['model_id', 'domain', 'task_type'], unique=False)
    op.create_index('ix_model_metrics_domain_task_champion', 'model_metrics', ['domain', 'task_type', 'is_champion'], unique=False)

    # Create champion_states table
    op.create_table(
        'champion_states',
        sa.Column('state_id', sa.String(length=36), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('champion_model_id', sa.String(length=256), nullable=False),
        sa.Column('champion_provider', sa.String(length=50), nullable=False),
        sa.Column('champion_score', sa.Float(), nullable=True),
        sa.Column('champion_since', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('previous_champion_id', sa.String(length=256), nullable=True),
        sa.Column('rotation_reason', sa.String(length=500), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('state_id')
    )

    # Create indexes for champion_states
    op.create_index('ix_champion_states_state_id', 'champion_states', ['state_id'], unique=False)
    op.create_index('ix_champion_states_domain', 'champion_states', ['domain'], unique=False)
    op.create_index('ix_champion_states_task_type', 'champion_states', ['task_type'], unique=False)
    op.create_index('ix_champion_states_is_current', 'champion_states', ['is_current'], unique=False)
    op.create_index('ix_champion_states_champion_since', 'champion_states', ['champion_since'], unique=False)

    # Composite indexes for champion_states
    op.create_index('ix_champion_states_domain_task_type', 'champion_states', ['domain', 'task_type'], unique=False)
    op.create_index('ix_champion_states_domain_task_current', 'champion_states', ['domain', 'task_type', 'is_current'], unique=False)

    # Create evaluation_metrics table
    op.create_table(
        'evaluation_metrics',
        sa.Column('eval_metric_id', sa.String(length=36), nullable=False),
        sa.Column('inference_id', sa.String(length=36), nullable=False),
        sa.Column('dimension', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('passed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('feedback', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('eval_metric_id'),
        sa.ForeignKeyConstraint(['inference_id'], ['inferences.inference_id'], ondelete='CASCADE')
    )

    # Create indexes for evaluation_metrics
    op.create_index('ix_evaluation_metrics_eval_metric_id', 'evaluation_metrics', ['eval_metric_id'], unique=False)
    op.create_index('ix_evaluation_metrics_inference_id', 'evaluation_metrics', ['inference_id'], unique=False)
    op.create_index('ix_evaluation_metrics_dimension', 'evaluation_metrics', ['dimension'], unique=False)
    op.create_index('ix_evaluation_metrics_passed', 'evaluation_metrics', ['passed'], unique=False)

    # Composite indexes for evaluation_metrics
    op.create_index('ix_evaluation_metrics_inference_dimension', 'evaluation_metrics', ['inference_id', 'dimension'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index('ix_evaluation_metrics_inference_dimension', table_name='evaluation_metrics')
    op.drop_index('ix_evaluation_metrics_passed', table_name='evaluation_metrics')
    op.drop_index('ix_evaluation_metrics_dimension', table_name='evaluation_metrics')
    op.drop_index('ix_evaluation_metrics_inference_id', table_name='evaluation_metrics')
    op.drop_index('ix_evaluation_metrics_eval_metric_id', table_name='evaluation_metrics')
    op.drop_table('evaluation_metrics')

    op.drop_index('ix_champion_states_domain_task_current', table_name='champion_states')
    op.drop_index('ix_champion_states_domain_task_type', table_name='champion_states')
    op.drop_index('ix_champion_states_champion_since', table_name='champion_states')
    op.drop_index('ix_champion_states_is_current', table_name='champion_states')
    op.drop_index('ix_champion_states_task_type', table_name='champion_states')
    op.drop_index('ix_champion_states_domain', table_name='champion_states')
    op.drop_index('ix_champion_states_state_id', table_name='champion_states')
    op.drop_table('champion_states')

    op.drop_index('ix_model_metrics_domain_task_champion', table_name='model_metrics')
    op.drop_index('ix_model_metrics_model_id_domain_task', table_name='model_metrics')
    op.drop_index('ix_model_metrics_domain_task_type', table_name='model_metrics')
    op.drop_index('ix_model_metrics_updated_at', table_name='model_metrics')
    op.drop_index('ix_model_metrics_is_champion', table_name='model_metrics')
    op.drop_index('ix_model_metrics_task_type', table_name='model_metrics')
    op.drop_index('ix_model_metrics_domain', table_name='model_metrics')
    op.drop_index('ix_model_metrics_model_id', table_name='model_metrics')
    op.drop_index('ix_model_metrics_metric_id', table_name='model_metrics')
    op.drop_table('model_metrics')

    op.drop_index('ix_inferences_model_id_created_at', table_name='inferences')
    op.drop_index('ix_inferences_domain_task_type', table_name='inferences')
    op.drop_index('ix_inferences_status', table_name='inferences')
    op.drop_index('ix_inferences_created_at', table_name='inferences')
    op.drop_index('ix_inferences_model_id', table_name='inferences')
    op.drop_index('ix_inferences_task_type', table_name='inferences')
    op.drop_index('ix_inferences_domain', table_name='inferences')
    op.drop_index('ix_inferences_inference_id', table_name='inferences')
    op.drop_table('inferences')

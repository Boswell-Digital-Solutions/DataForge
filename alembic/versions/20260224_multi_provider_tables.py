"""Create multi-provider pipeline tables

Tables: model_catalog, pricing_monitor_runs, pricing_snapshots,
        pricing_alerts, cost_ledger, batch_queue

Revision ID: multi_provider_001
Revises: agentic_reasoning_001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'multi_provider_001'
down_revision: Union[str, Sequence[str], None] = 'agentic_reasoning_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── model_catalog ─────────────────────────────────────────────
    op.create_table(
        'model_catalog',
        sa.Column('model_key', sa.String(128), primary_key=True),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('model_id', sa.String(128), nullable=False),
        sa.Column('input_cost_per_mtok', sa.Numeric(10, 4), nullable=False),
        sa.Column('output_cost_per_mtok', sa.Numeric(10, 4), nullable=False),
        sa.Column('batch_input_cost', sa.Numeric(10, 4), nullable=True),
        sa.Column('batch_output_cost', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_context', sa.Integer(), nullable=False),
        sa.Column('cache_read_discount', sa.Numeric(4, 2), nullable=False, server_default='0'),
        sa.Column('supports_batch', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('supports_structured_output', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', sa.String(64), nullable=False, server_default='system'),
        sa.CheckConstraint("tier IN ('budget', 'workhorse', 'flagship')", name='ck_model_catalog_tier'),
        sa.CheckConstraint('input_cost_per_mtok >= 0', name='ck_model_catalog_input_cost'),
        sa.CheckConstraint('output_cost_per_mtok >= 0', name='ck_model_catalog_output_cost'),
    )
    op.create_index('ix_model_catalog_provider', 'model_catalog', ['provider'])
    op.create_index('ix_model_catalog_tier', 'model_catalog', ['tier'])

    # ── pricing_monitor_runs ──────────────────────────────────────
    op.create_table(
        'pricing_monitor_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('providers_scraped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('models_extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('changes_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_applied', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('alerts_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("trigger_type IN ('scheduled', 'manual')", name='ck_pricing_run_trigger'),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name='ck_pricing_run_status'),
    )
    op.create_index('ix_pricing_monitor_runs_status', 'pricing_monitor_runs', ['status'])

    # ── pricing_snapshots ─────────────────────────────────────────
    op.create_table(
        'pricing_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('pricing_monitor_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('models', JSONB, nullable=False),
        sa.Column('raw_content_hash', sa.String(64), nullable=True),
        sa.Column('extraction_model', sa.String(128), nullable=True),
        sa.Column('validation_errors', JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_pricing_snapshots_provider', 'pricing_snapshots', ['provider'])
    op.create_index('ix_pricing_snapshots_run_id', 'pricing_snapshots', ['run_id'])

    # ── pricing_alerts ────────────────────────────────────────────
    op.create_table(
        'pricing_alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('pricing_monitor_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('model_id', sa.String(128), nullable=False),
        sa.Column('change_type', sa.String(20), nullable=False),
        sa.Column('field_changed', sa.String(64), nullable=True),
        sa.Column('old_value', sa.Numeric(10, 4), nullable=True),
        sa.Column('new_value', sa.Numeric(10, 4), nullable=True),
        sa.Column('change_percent', sa.Numeric(6, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('resolved_by', sa.String(64), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            "change_type IN ('price_increase', 'price_decrease', 'new_model', 'model_deprecated', 'capability_change')",
            name='ck_pricing_alert_change_type',
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'applied', 'dismissed', 'investigating')",
            name='ck_pricing_alert_status',
        ),
    )
    op.create_index('ix_pricing_alerts_run_id', 'pricing_alerts', ['run_id'])
    op.create_index('ix_pricing_alerts_provider', 'pricing_alerts', ['provider'])
    op.create_index('ix_pricing_alerts_status', 'pricing_alerts', ['status'])
    op.create_index('ix_pricing_alerts_model', 'pricing_alerts', ['provider', 'model_id'])

    # ── cost_ledger ───────────────────────────────────────────────
    op.create_table(
        'cost_ledger',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(128), nullable=True),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('model_id', sa.String(128), nullable=False),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('input_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('output_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('total_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('is_batch', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_cached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_cost_ledger_created_at', 'cost_ledger', ['created_at'])
    op.create_index('ix_cost_ledger_period', 'cost_ledger', ['user_id', 'created_at'])
    op.create_index('ix_cost_ledger_provider', 'cost_ledger', ['provider', 'created_at'])
    op.create_index('ix_cost_ledger_task', 'cost_ledger', ['task_type', 'created_at'])

    # ── batch_queue ───────────────────────────────────────────────
    op.create_table(
        'batch_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('batch_group_id', UUID(as_uuid=True), nullable=False),
        sa.Column('app_id', sa.String(50), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('model_key', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('messages_json', JSONB, nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('structured_output_json', JSONB, nullable=True),
        sa.Column('callback_url', sa.String(500), nullable=True),
        sa.Column('callback_meta', JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('provider_batch_id', sa.String(200), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.CheckConstraint("status IN ('queued', 'submitted', 'completed', 'failed')", name='ck_batch_queue_status'),
    )
    op.create_index('ix_batch_queue_status', 'batch_queue', ['status'])
    op.create_index('ix_batch_queue_group', 'batch_queue', ['batch_group_id'])
    op.create_index('ix_batch_queue_provider_status', 'batch_queue', ['provider', 'status'])


def downgrade() -> None:
    op.drop_table('batch_queue')
    op.drop_table('cost_ledger')
    op.drop_table('pricing_alerts')
    op.drop_table('pricing_snapshots')
    op.drop_table('pricing_monitor_runs')
    op.drop_table('model_catalog')

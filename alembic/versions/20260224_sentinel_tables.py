"""Add Sentinel agent tables (sweeps + healing events).

Revision ID: sentinel_001
Revises: multi_provider_001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'sentinel_001'
down_revision: Union[str, Sequence[str], None] = 'multi_provider_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sentinel_sweeps ──────────────────────────────────────
    op.create_table(
        'sentinel_sweeps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('sweep_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('dimensions_checked', JSONB, nullable=False, server_default='[]'),
        sa.Column('findings', JSONB, nullable=False, server_default='[]'),
        sa.Column('overall_status', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('trigger', sa.String(30), nullable=False, server_default='scheduled'),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        sa.CheckConstraint("sweep_type IN ('light', 'deep')", name='ck_sentinel_sweep_type'),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name='ck_sentinel_sweep_status'),
        sa.CheckConstraint("overall_status IN ('healthy', 'degraded', 'critical', 'unknown')", name='ck_sentinel_sweep_overall'),
    )
    op.create_index('ix_sentinel_sweeps_status', 'sentinel_sweeps', ['status'])
    op.create_index('ix_sentinel_sweeps_started_at', 'sentinel_sweeps', ['started_at'])

    # ── sentinel_healing_events ──────────────────────────────
    op.create_table(
        'sentinel_healing_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('sweep_id', UUID(as_uuid=True), sa.ForeignKey('sentinel_sweeps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('playbook', sa.String(60), nullable=False),
        sa.Column('tier', sa.String(1), nullable=False),
        sa.Column('action', sa.String(200), nullable=False),
        sa.Column('target_service', sa.String(60), nullable=True),
        sa.Column('outcome', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('governed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('approval_id', sa.String(100), nullable=True),
        sa.Column('details', JSONB, nullable=False, server_default='{}'),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        sa.CheckConstraint("tier IN ('A', 'B', 'C')", name='ck_sentinel_healing_tier'),
        sa.CheckConstraint("outcome IN ('pending', 'success', 'failure', 'escalated', 'skipped')", name='ck_sentinel_healing_outcome'),
    )
    op.create_index('ix_sentinel_healing_sweep_id', 'sentinel_healing_events', ['sweep_id'])
    op.create_index('ix_sentinel_healing_outcome', 'sentinel_healing_events', ['outcome'])


def downgrade() -> None:
    op.drop_table('sentinel_healing_events')
    op.drop_table('sentinel_sweeps')

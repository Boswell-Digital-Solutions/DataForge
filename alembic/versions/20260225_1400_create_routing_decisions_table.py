"""Create routing_decisions table for NeuroForge routing audit log.

Revision ID: routing_decisions_001
Revises: pressforge_001
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'routing_decisions_001'
down_revision: Union[str, Sequence[str], None] = 'pressforge_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'routing_decisions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_id', sa.String(128), nullable=False),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('selected_provider', sa.String(32), nullable=False),
        sa.Column('selected_model', sa.String(128), nullable=False),
        sa.Column('selected_tier', sa.String(20), nullable=False),
        sa.Column('reasons', JSONB, nullable=False, comment='["COST_OPTIMIZED", "TASK_DEFAULT_APPLIED"]'),
        sa.Column('fallback_chain', JSONB, nullable=False, server_default='[]', comment='["gemini-2.5-flash", "gpt-4.1-mini"]'),
        sa.Column('rejected', JSONB, nullable=False, server_default='{}', comment='{"claude-sonnet-4-5": "PROVIDER_UNAVAILABLE_SKIP"}'),
        sa.Column('latency_ms', sa.Numeric(10, 2), nullable=True),
        sa.Column('cost_estimate', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_routing_decisions_task', 'routing_decisions', ['task_type'])
    op.create_index('idx_routing_decisions_provider', 'routing_decisions', ['selected_provider'])
    op.create_index('idx_routing_decisions_created', 'routing_decisions', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_routing_decisions_created', table_name='routing_decisions')
    op.drop_index('idx_routing_decisions_provider', table_name='routing_decisions')
    op.drop_index('idx_routing_decisions_task', table_name='routing_decisions')
    op.drop_table('routing_decisions')

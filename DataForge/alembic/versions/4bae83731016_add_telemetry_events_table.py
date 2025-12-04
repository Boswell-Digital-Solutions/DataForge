"""add_telemetry_events_table

Revision ID: 4bae83731016
Revises: aada9fc461fe
Create Date: 2025-12-03 19:11:36.361921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bae83731016'
down_revision: Union[str, Sequence[str], None] = 'aada9fc461fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create events table for unified telemetry across Forge ecosystem
    op.create_table(
        'events',
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )

    # Create indexes for common query patterns
    op.create_index('idx_events_service', 'events', ['service'])
    op.create_index('idx_events_event_type', 'events', ['event_type'])
    op.create_index('idx_events_correlation_id', 'events', ['correlation_id'])
    op.create_index('idx_events_timestamp', 'events', ['timestamp'])
    op.create_index('idx_events_service_timestamp', 'events', ['service', 'timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_events_service_timestamp', table_name='events')
    op.drop_index('idx_events_timestamp', table_name='events')
    op.drop_index('idx_events_correlation_id', table_name='events')
    op.drop_index('idx_events_event_type', table_name='events')
    op.drop_index('idx_events_service', table_name='events')
    op.drop_table('events')

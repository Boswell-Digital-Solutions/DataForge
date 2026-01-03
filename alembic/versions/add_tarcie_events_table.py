"""Add tarcie_events table

Revision ID: add_tarcie_events
Revises: aada9fc461fe
Create Date: 2026-01-03

Tarcie friction capture ingest table.
Append-only storage for notes and markers.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_tarcie_events'
down_revision = 'aada9fc461fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tarcie_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timestamp_mono_ms', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('app_context', sa.String(64), nullable=False, server_default='General'),
        sa.Column('source_version', sa.String(32), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('ix_tarcie_events_device_id', 'tarcie_events', ['device_id'])
    op.create_index('ix_tarcie_events_timestamp_utc', 'tarcie_events', ['timestamp_utc'])
    op.create_index('ix_tarcie_events_ingested', 'tarcie_events', ['ingested_at'])
    op.create_index('ix_tarcie_events_device_time', 'tarcie_events', ['device_id', 'timestamp_utc'])


def downgrade() -> None:
    op.drop_index('ix_tarcie_events_device_time', table_name='tarcie_events')
    op.drop_index('ix_tarcie_events_ingested', table_name='tarcie_events')
    op.drop_index('ix_tarcie_events_timestamp_utc', table_name='tarcie_events')
    op.drop_index('ix_tarcie_events_device_id', table_name='tarcie_events')
    op.drop_table('tarcie_events')

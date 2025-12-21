"""add_telemetry_events_view

Creates the 'events' table for unified telemetry across the Forge ecosystem,
plus a 'telemetry_events' view that aliases it for ForgeCommand compatibility.

Also adds the AI insights tables (metric_baselines, detected_anomalies)
and helper functions for anomaly detection.

Revision ID: 20251221_0500
Revises: 20251216_1901
Create Date: 2025-12-21 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251221_0500'
down_revision: Union[str, Sequence[str], None] = '20251216_1901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create events table, telemetry_events view, and AI insights tables."""

    # ============================================================
    # EVENTS TABLE (base telemetry table)
    # ============================================================
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

    # ============================================================
    # TELEMETRY_EVENTS VIEW (alias for ForgeCommand compatibility)
    # ============================================================
    op.execute("""
        CREATE OR REPLACE VIEW telemetry_events AS
        SELECT
            event_id,
            timestamp,
            service,
            event_type,
            severity,
            correlation_id,
            metadata,
            metrics,
            created_at
        FROM events
    """)

    # ============================================================
    # METRIC BASELINES TABLE
    # ============================================================
    op.create_table(
        'metric_baselines',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('mean_value', sa.Numeric(), nullable=False),
        sa.Column('stddev_value', sa.Numeric(), nullable=False),
        sa.Column('p50_value', sa.Numeric(), nullable=False),
        sa.Column('p95_value', sa.Numeric(), nullable=False),
        sa.Column('p99_value', sa.Numeric(), nullable=False),
        sa.Column('min_value', sa.Numeric(), nullable=False),
        sa.Column('max_value', sa.Numeric(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service', 'metric_name', 'window_end', name='uq_baselines_service_metric_window')
    )

    op.create_index(
        'idx_baselines_service_metric',
        'metric_baselines',
        ['service', 'metric_name', sa.text('window_end DESC')]
    )

    # ============================================================
    # DETECTED ANOMALIES TABLE
    # ============================================================
    op.create_table(
        'detected_anomalies',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('observed_value', sa.Numeric(), nullable=False),
        sa.Column('expected_value', sa.Numeric(), nullable=False),
        sa.Column('z_score', sa.Numeric(), nullable=False),
        sa.Column('percentile', sa.Numeric(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('anomaly_type', sa.String(50), nullable=False),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_anomalies_time', 'detected_anomalies', ['detected_at'])
    op.create_index('idx_anomalies_service', 'detected_anomalies', ['service', 'detected_at'])
    op.create_index('idx_anomalies_severity', 'detected_anomalies', ['severity', 'detected_at'])
    op.create_index('idx_anomalies_unacked', 'detected_anomalies', ['acknowledged', 'detected_at'])

    # ============================================================
    # HELPER FUNCTIONS
    # ============================================================

    # Z-score calculation function
    op.execute("""
        CREATE OR REPLACE FUNCTION calculate_z_score(
            observed NUMERIC,
            mean_val NUMERIC,
            stddev_val NUMERIC
        ) RETURNS NUMERIC AS $$
        BEGIN
            IF stddev_val = 0 OR stddev_val IS NULL THEN
                RETURN 0;
            END IF;
            RETURN (observed - mean_val) / stddev_val;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """)

    # Anomaly severity classification
    op.execute("""
        CREATE OR REPLACE FUNCTION classify_anomaly_severity(z NUMERIC)
        RETURNS VARCHAR(20) AS $$
        BEGIN
            IF ABS(z) >= 4 THEN RETURN 'critical';
            ELSIF ABS(z) >= 3 THEN RETURN 'high';
            ELSIF ABS(z) >= 2.5 THEN RETURN 'medium';
            ELSE RETURN 'low';
            END IF;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """)

    # ============================================================
    # BASELINE UPDATE FUNCTION
    # ============================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_metric_baselines()
        RETURNS void AS $$
        BEGIN
            -- Update latency baselines
            INSERT INTO metric_baselines (
                service, metric_name, mean_value, stddev_value,
                p50_value, p95_value, p99_value, min_value, max_value,
                sample_count, window_start, window_end
            )
            SELECT
                service,
                'latency_ms' as metric_name,
                AVG((metrics->>'latency_ms')::numeric) as mean_value,
                COALESCE(STDDEV((metrics->>'latency_ms')::numeric), 0) as stddev_value,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY (metrics->>'latency_ms')::numeric) as p50,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY (metrics->>'latency_ms')::numeric) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY (metrics->>'latency_ms')::numeric) as p99,
                MIN((metrics->>'latency_ms')::numeric) as min_value,
                MAX((metrics->>'latency_ms')::numeric) as max_value,
                COUNT(*) as sample_count,
                NOW() - INTERVAL '7 days' as window_start,
                NOW() as window_end
            FROM events
            WHERE timestamp >= NOW() - INTERVAL '7 days'
              AND metrics->>'latency_ms' IS NOT NULL
            GROUP BY service
            ON CONFLICT (service, metric_name, window_end)
            DO UPDATE SET
                mean_value = EXCLUDED.mean_value,
                stddev_value = EXCLUDED.stddev_value,
                p50_value = EXCLUDED.p50_value,
                p95_value = EXCLUDED.p95_value,
                p99_value = EXCLUDED.p99_value,
                min_value = EXCLUDED.min_value,
                max_value = EXCLUDED.max_value,
                sample_count = EXCLUDED.sample_count;
        END;
        $$ LANGUAGE plpgsql
    """)

    # ============================================================
    # VIEW REFRESH FUNCTION (for ForgeCommand)
    # ============================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_forge_command_views()
        RETURNS void AS $$
        BEGIN
            -- Update metric baselines
            PERFORM update_metric_baselines();
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    """Drop telemetry_events view, events table, and AI insights tables."""
    op.execute("DROP FUNCTION IF EXISTS refresh_forge_command_views()")
    op.execute("DROP FUNCTION IF EXISTS update_metric_baselines()")
    op.execute("DROP FUNCTION IF EXISTS classify_anomaly_severity(NUMERIC)")
    op.execute("DROP FUNCTION IF EXISTS calculate_z_score(NUMERIC, NUMERIC, NUMERIC)")

    op.drop_index('idx_anomalies_unacked', table_name='detected_anomalies')
    op.drop_index('idx_anomalies_severity', table_name='detected_anomalies')
    op.drop_index('idx_anomalies_service', table_name='detected_anomalies')
    op.drop_index('idx_anomalies_time', table_name='detected_anomalies')
    op.drop_table('detected_anomalies')

    op.drop_index('idx_baselines_service_metric', table_name='metric_baselines')
    op.drop_table('metric_baselines')

    op.execute("DROP VIEW IF EXISTS telemetry_events")

    op.drop_index('idx_events_service_timestamp', table_name='events')
    op.drop_index('idx_events_timestamp', table_name='events')
    op.drop_index('idx_events_correlation_id', table_name='events')
    op.drop_index('idx_events_event_type', table_name='events')
    op.drop_index('idx_events_service', table_name='events')
    op.drop_table('events')

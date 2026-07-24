"""create dedicated strict AuthorForge analytics storage

Revision ID: 20260724_01
Revises: 20260723_01
Create Date: 2026-07-24

AuthorForge content remains local. This table accepts only the closed,
content-free AuthorForgeAnalyticsEnvelope.v1 projection and is deliberately
separate from both ForgeEvent.v1 and the retained pre-v1 events table.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260724_01"
down_revision: Union[str, Sequence[str], None] = "20260723_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE authorforge_analytics_events (
            event_id UUID PRIMARY KEY,
            event_digest CHAR(64) NOT NULL
                CHECK (event_digest ~ '^[0-9a-f]{64}$'),
            canonical_bytes INTEGER NOT NULL
                CHECK (canonical_bytes BETWEEN 1 AND 4096),
            schema_version TEXT NOT NULL
                CHECK (schema_version = 'AuthorForgeAnalyticsEnvelope.v1'),
            policy_version TEXT NOT NULL
                CHECK (policy_version = 'authorforge-analytics-policy.v1'),
            occurred_at TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            event_type TEXT NOT NULL
                CHECK (
                    event_type IN (
                        'feature_invoked',
                        'workflow_completed',
                        'workflow_failed',
                        'model_request_completed',
                        'route_selected',
                        'evaluation_recorded',
                        'receipt_recorded'
                    )
                ),
            dimensions JSONB NOT NULL
                CHECK (jsonb_typeof(dimensions) = 'object')
                CHECK (
                    (
                        dimensions - ARRAY[
                            'product',
                            'application',
                            'build_version',
                            'installation_pseudonym',
                            'project_pseudonym',
                            'run_pseudonym',
                            'tenant_pseudonym',
                            'feature_id',
                            'workflow_id',
                            'execution_lane',
                            'route_classification',
                            'content_authority',
                            'action',
                            'status',
                            'outcome',
                            'provider_id',
                            'model_id',
                            'error_category',
                            'error_code',
                            'review_state',
                            'receipt_version',
                            'evaluation_version',
                            'cache_hit',
                            'offline',
                            'rollback_performed'
                        ]::TEXT[]
                    ) = '{}'::JSONB
                ),
            metrics JSONB NOT NULL
                CHECK (forge_jsonb_object_values_are_numbers_v1(metrics))
                CHECK (
                    (
                        metrics - ARRAY[
                            'operation_count',
                            'item_count',
                            'input_token_count',
                            'output_token_count',
                            'duration_ms',
                            'latency_ms',
                            'cost_microusd'
                        ]::TEXT[]
                    ) = '{}'::JSONB
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_authorforge_analytics_events_occurred_at
            ON authorforge_analytics_events (occurred_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_authorforge_analytics_events_type_occurred_at
            ON authorforge_analytics_events (event_type, occurred_at DESC)
        """
    )
    op.execute("ALTER TABLE authorforge_analytics_events ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE authorforge_analytics_events FROM PUBLIC")


def downgrade() -> None:
    raise RuntimeError(
        "AuthorForge analytics storage is evidence-preserving. Disable its "
        "dedicated writer or add a separately reviewed retirement migration; "
        "this migration will not erase accepted analytics evidence."
    )

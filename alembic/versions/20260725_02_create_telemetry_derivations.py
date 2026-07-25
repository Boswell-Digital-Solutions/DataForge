"""create CP5 shadow retention derivation storage

Revision ID: 20260725_02
Revises: 20260725_01
Create Date: 2026-07-25

Rollback revokes the isolated runtime role and its RLS policies but retains
all CP5 receipts, decisions, and aggregates. Source evidence is never rewritten.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260725_02"
down_revision: str | None = "20260725_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_derivation_receipts_v1 (
            receipt_id UUID PRIMARY KEY,
            derivation_id UUID NOT NULL UNIQUE,
            payload_digest CHAR(64) NOT NULL
                CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
            payload JSONB NOT NULL
                CHECK (
                    jsonb_typeof(payload) = 'object'
                    AND payload ->> 'schema_version'
                        = 'TelemetryDerivationReceipt.v1'
                ),
            derivation_type TEXT NOT NULL
                CHECK (
                    derivation_type IN (
                        'retention_decision',
                        'routine_success_aggregate'
                    )
                ),
            producer_service_name TEXT NOT NULL
                CHECK (producer_service_name = 'dataforge'),
            producer_version TEXT NOT NULL CHECK (length(producer_version) <= 64),
            policy_id TEXT NOT NULL,
            policy_version TEXT NOT NULL CHECK (length(policy_version) <= 64),
            policy_sha256 CHAR(64) NOT NULL
                CHECK (policy_sha256 ~ '^[0-9a-f]{64}$'),
            policy_mode TEXT NOT NULL CHECK (policy_mode = 'shadow'),
            clock_basis TEXT NOT NULL CHECK (clock_basis = 'received_at'),
            window_start_at TIMESTAMPTZ NOT NULL,
            window_end_at TIMESTAMPTZ NOT NULL,
            output_kind TEXT NOT NULL,
            output_ref UUID NOT NULL,
            output_sha256 CHAR(64) NOT NULL
                CHECK (output_sha256 ~ '^[0-9a-f]{64}$'),
            decision_action TEXT NOT NULL
                CHECK (
                    decision_action IN (
                        'retain',
                        'aggregate_then_delete',
                        'delete',
                        'legal_hold'
                    )
                ),
            decision_reason_code TEXT NOT NULL
                CHECK (decision_reason_code ~ '^[a-z0-9_]{1,96}$'),
            decision_applied BOOLEAN NOT NULL CHECK (NOT decision_applied),
            source_overwritten BOOLEAN NOT NULL CHECK (NOT source_overwritten),
            uncertainty_state TEXT NOT NULL
                CHECK (
                    uncertainty_state IN (
                        'complete',
                        'partial',
                        'unknown'
                    )
                ),
            source_count INTEGER NOT NULL CHECK (source_count BETWEEN 1 AND 500),
            created_at TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (output_kind, output_ref),
            CHECK (window_end_at >= window_start_at),
            CHECK (
                payload #>> '{policy,mode}' = 'shadow'
                AND payload #>> '{window,clock_basis}' = 'received_at'
                AND (payload #>> '{decision,applied}')::BOOLEAN IS FALSE
                AND (payload #>> '{decision,source_overwritten}')::BOOLEAN
                    IS FALSE
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_retention_decisions_v1 (
            decision_id UUID PRIMARY KEY,
            receipt_id UUID NOT NULL UNIQUE
                REFERENCES telemetry_derivation_receipts_v1(receipt_id)
                ON DELETE RESTRICT,
            source_kind TEXT NOT NULL
                CHECK (
                    source_kind IN (
                        'forge_event',
                        'forge_check_result',
                        'forge_check_run_receipt'
                    )
                ),
            source_ref TEXT NOT NULL,
            source_sha256 CHAR(64) NOT NULL
                CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
            source_received_at TIMESTAMPTZ NOT NULL,
            service_or_check TEXT NOT NULL,
            environment TEXT NOT NULL
                CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            tenant_ref TEXT
                CHECK (
                    tenant_ref IS NULL
                    OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            privacy_class TEXT NOT NULL
                CHECK (
                    privacy_class IN (
                        'public',
                        'internal',
                        'restricted',
                        'confidential'
                    )
                ),
            retention_class TEXT NOT NULL
                CHECK (
                    retention_class IN (
                        'ephemeral',
                        'short',
                        'standard',
                        'long',
                        'legal_hold'
                    )
                ),
            legal_class TEXT NOT NULL
                CHECK (legal_class IN ('standard', 'regulated', 'legal_hold')),
            policy_id TEXT NOT NULL,
            policy_version TEXT NOT NULL CHECK (length(policy_version) <= 64),
            policy_sha256 CHAR(64) NOT NULL
                CHECK (policy_sha256 ~ '^[0-9a-f]{64}$'),
            policy_mode TEXT NOT NULL CHECK (policy_mode = 'shadow'),
            clock_basis TEXT NOT NULL CHECK (clock_basis = 'received_at'),
            window_start_at TIMESTAMPTZ NOT NULL,
            window_end_at TIMESTAMPTZ NOT NULL,
            action TEXT NOT NULL
                CHECK (
                    action IN (
                        'retain',
                        'aggregate_then_delete',
                        'delete',
                        'legal_hold'
                    )
                ),
            reason_code TEXT NOT NULL CHECK (reason_code ~ '^[a-z0-9_]{1,96}$'),
            projected_delete_at TIMESTAMPTZ,
            applied BOOLEAN NOT NULL CHECK (NOT applied),
            source_overwritten BOOLEAN NOT NULL CHECK (NOT source_overwritten),
            created_at TIMESTAMPTZ NOT NULL,
            UNIQUE (source_kind, source_ref, policy_sha256, window_end_at),
            CHECK (window_end_at >= window_start_at),
            CHECK (source_received_at BETWEEN window_start_at AND window_end_at),
            CHECK (
                (action = 'legal_hold' AND projected_delete_at IS NULL)
                OR (
                    action <> 'legal_hold'
                    AND projected_delete_at IS NOT NULL
                    AND projected_delete_at >= source_received_at
                )
            ),
            CHECK (
                retention_class <> 'legal_hold'
                OR (
                    action = 'legal_hold'
                    AND projected_delete_at IS NULL
                    AND NOT applied
                )
            ),
            CHECK (
                legal_class <> 'legal_hold'
                OR (
                    action = 'legal_hold'
                    AND projected_delete_at IS NULL
                    AND NOT applied
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_routine_aggregates_v1 (
            aggregate_id UUID PRIMARY KEY,
            receipt_id UUID NOT NULL UNIQUE
                REFERENCES telemetry_derivation_receipts_v1(receipt_id)
                ON DELETE RESTRICT,
            payload_digest CHAR(64) NOT NULL
                CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
            payload JSONB NOT NULL
                CHECK (
                    jsonb_typeof(payload) = 'object'
                    AND payload ->> 'schema_version'
                        = 'forge.dataforge.telemetry-routine-aggregate.v1'
                    AND (payload ->> 'source_overwritten')::BOOLEAN IS FALSE
                    AND payload ->> 'clock_basis' = 'received_at'
                    AND payload ->> 'policy_mode' = 'shadow'
                ),
            group_key CHAR(64) NOT NULL
                CHECK (group_key ~ '^[0-9a-f]{64}$'),
            evidence_kind TEXT NOT NULL
                CHECK (
                    evidence_kind IN (
                        'forge_event',
                        'forge_check_result',
                        'forge_check_run_receipt'
                    )
                ),
            service_or_check TEXT NOT NULL,
            environment TEXT NOT NULL
                CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            tenant_ref TEXT
                CHECK (
                    tenant_ref IS NULL
                    OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            privacy_class TEXT NOT NULL
                CHECK (
                    privacy_class IN (
                        'public',
                        'internal',
                        'restricted',
                        'confidential'
                    )
                ),
            retention_class TEXT NOT NULL
                CHECK (
                    retention_class IN (
                        'ephemeral',
                        'short',
                        'standard',
                        'long',
                        'legal_hold'
                    )
                ),
            decision_reason_code TEXT NOT NULL
                CHECK (decision_reason_code ~ '^[a-z0-9_]{1,96}$'),
            source_count INTEGER NOT NULL CHECK (source_count BETWEEN 1 AND 500),
            window_start_at TIMESTAMPTZ NOT NULL,
            window_end_at TIMESTAMPTZ NOT NULL,
            policy_id TEXT NOT NULL,
            policy_version TEXT NOT NULL CHECK (length(policy_version) <= 64),
            policy_sha256 CHAR(64) NOT NULL
                CHECK (policy_sha256 ~ '^[0-9a-f]{64}$'),
            policy_mode TEXT NOT NULL CHECK (policy_mode = 'shadow'),
            created_at TIMESTAMPTZ NOT NULL,
            UNIQUE (group_key, policy_sha256, window_end_at),
            CHECK (window_end_at >= window_start_at)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_telemetry_derivations_window
        ON telemetry_derivation_receipts_v1 (window_end_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_telemetry_retention_scope_window
        ON telemetry_retention_decisions_v1 (
            md5(environment),
            md5(COALESCE(tenant_ref, '')),
            window_end_at DESC
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_telemetry_aggregates_scope_window
        ON telemetry_routine_aggregates_v1 (
            md5(environment),
            md5(COALESCE(tenant_ref, '')),
            window_end_at DESC
        )
        """
    )
    for table in (
        "telemetry_derivation_receipts_v1",
        "telemetry_retention_decisions_v1",
        "telemetry_routine_aggregates_v1",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")

    op.execute(
        """
        GRANT SELECT, INSERT ON TABLE
            telemetry_derivation_receipts_v1,
            telemetry_retention_decisions_v1,
            telemetry_routine_aggregates_v1
        TO dataforge_telemetry_ingest
        """
    )
    for table, policy in (
        (
            "telemetry_derivation_receipts_v1",
            "telemetry_derivations_runtime",
        ),
        (
            "telemetry_retention_decisions_v1",
            "telemetry_retention_decisions_runtime",
        ),
        (
            "telemetry_routine_aggregates_v1",
            "telemetry_routine_aggregates_runtime",
        ),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy}_insert ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {policy}_select ON {table}")
        op.execute(
            f"""
            CREATE POLICY {policy}_insert
            ON {table}
            FOR INSERT TO dataforge_telemetry_ingest
            WITH CHECK (policy_mode = 'shadow')
            """
        )
        op.execute(
            f"""
            CREATE POLICY {policy}_select
            ON {table}
            FOR SELECT TO dataforge_telemetry_ingest
            USING (policy_mode = 'shadow')
            """
        )


def downgrade() -> None:
    """Disable runtime access while retaining all CP5 derivation records."""

    for table, policy in (
        (
            "telemetry_routine_aggregates_v1",
            "telemetry_routine_aggregates_runtime",
        ),
        (
            "telemetry_retention_decisions_v1",
            "telemetry_retention_decisions_runtime",
        ),
        (
            "telemetry_derivation_receipts_v1",
            "telemetry_derivations_runtime",
        ),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {policy}_insert ON {table}")
    op.execute(
        """
        REVOKE SELECT, INSERT ON TABLE
            telemetry_derivation_receipts_v1,
            telemetry_retention_decisions_v1,
            telemetry_routine_aggregates_v1
        FROM dataforge_telemetry_ingest
        """
    )

"""create CP4 ForgeCheck result and receipt evidence storage

Revision ID: 20260725_01
Revises: 20260724_02
Create Date: 2026-07-25

Rollback revokes the isolated runtime role and its RLS policies but retains
all result and receipt rows as required by the CP4 rollback contract.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260725_01"
down_revision: str | None = "20260724_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS forge_check_results_v1 (
            result_id UUID PRIMARY KEY,
            payload_digest CHAR(64) NOT NULL
                CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
            payload JSONB NOT NULL
                CHECK (
                    jsonb_typeof(payload) = 'object'
                    AND payload ->> 'schema_version' = 'ForgeCheckResult.v1'
                ),
            run_id UUID NOT NULL,
            check_id TEXT NOT NULL
                CHECK (check_id ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            check_revision INTEGER NOT NULL CHECK (check_revision >= 1),
            definition_sha256 CHAR(64) NOT NULL
                CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
            environment TEXT NOT NULL
                CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            tenant_ref TEXT
                CHECK (
                    tenant_ref IS NULL
                    OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            evaluation_mode TEXT NOT NULL CHECK (evaluation_mode = 'debug'),
            status TEXT NOT NULL
                CHECK (
                    status IN (
                        'passed',
                        'failed',
                        'timed_out',
                        'disabled',
                        'blocked',
                        'indeterminate'
                    )
                ),
            reason_code TEXT NOT NULL
                CHECK (reason_code ~ '^[a-z0-9_]{1,96}$'),
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ NOT NULL,
            duration_ms INTEGER NOT NULL
                CHECK (duration_ms BETWEEN 0 AND 30000),
            assertion_passed BOOLEAN,
            slo_included BOOLEAN NOT NULL CHECK (NOT slo_included),
            uptime_included BOOLEAN NOT NULL CHECK (NOT uptime_included),
            baseline_included BOOLEAN NOT NULL CHECK (NOT baseline_included),
            cost_units_observed INTEGER NOT NULL
                CHECK (cost_units_observed BETWEEN 0 AND 1000000),
            privacy_class TEXT NOT NULL
                CHECK (
                    privacy_class IN (
                        'public',
                        'internal',
                        'restricted',
                        'confidential'
                    )
                ),
            correlation_id UUID,
            trace_id TEXT
                CHECK (
                    trace_id IS NULL
                    OR (
                        trace_id ~ '^[0-9a-f]{32}$'
                        AND trace_id <> repeat('0', 32)
                    )
                ),
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CHECK (finished_at >= started_at),
            CHECK (
                (status = 'passed' AND assertion_passed)
                OR (
                    status IN ('failed', 'timed_out')
                    AND assertion_passed IS NOT TRUE
                )
                OR (
                    status IN ('disabled', 'blocked', 'indeterminate')
                    AND assertion_passed IS NULL
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS forge_check_run_receipts_v1 (
            receipt_id UUID PRIMARY KEY,
            payload_digest CHAR(64) NOT NULL
                CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
            payload JSONB NOT NULL
                CHECK (
                    jsonb_typeof(payload) = 'object'
                    AND payload ->> 'schema_version' = 'ForgeCheckRunReceipt.v1'
                ),
            run_id UUID NOT NULL,
            result_id UUID NOT NULL UNIQUE
                REFERENCES forge_check_results_v1(result_id)
                ON DELETE RESTRICT,
            check_id TEXT NOT NULL
                CHECK (check_id ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            definition_sha256 CHAR(64) NOT NULL
                CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
            environment TEXT NOT NULL
                CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'),
            tenant_ref TEXT
                CHECK (
                    tenant_ref IS NULL
                    OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]{0,127}$'
                ),
            source_repository TEXT NOT NULL,
            source_commit CHAR(40) NOT NULL
                CHECK (source_commit ~ '^[0-9a-f]{40}$'),
            source_path TEXT NOT NULL,
            runner_service_name TEXT NOT NULL
                CHECK (runner_service_name = 'forgeagents'),
            runner_version TEXT NOT NULL CHECK (length(runner_version) <= 64),
            trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'schedule', 'ci')),
            evaluation_mode TEXT NOT NULL CHECK (evaluation_mode = 'debug'),
            status TEXT NOT NULL
                CHECK (
                    status IN (
                        'passed',
                        'failed',
                        'timed_out',
                        'disabled',
                        'blocked',
                        'indeterminate'
                    )
                ),
            started_at TIMESTAMPTZ NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL,
            slo_included BOOLEAN NOT NULL CHECK (NOT slo_included),
            uptime_included BOOLEAN NOT NULL CHECK (NOT uptime_included),
            baseline_included BOOLEAN NOT NULL CHECK (NOT baseline_included),
            slo_reason TEXT NOT NULL CHECK (slo_reason = 'debug_excluded'),
            max_cost_units INTEGER NOT NULL
                CHECK (max_cost_units BETWEEN 0 AND 1000000),
            observed_cost_units INTEGER NOT NULL
                CHECK (
                    observed_cost_units BETWEEN 0 AND 1000000
                    AND observed_cost_units <= max_cost_units
                ),
            cost_unit TEXT NOT NULL
                CHECK (cost_unit IN ('none', 'request', 'token', 'usd_micros')),
            kill_switch_ref TEXT NOT NULL,
            kill_switch_enabled BOOLEAN NOT NULL,
            evidence_refs JSONB NOT NULL
                CHECK (
                    jsonb_typeof(evidence_refs) = 'array'
                    AND jsonb_array_length(evidence_refs) >= 1
                ),
            received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CHECK (observed_at >= started_at)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_forge_check_results_scope_started
        ON forge_check_results_v1 (
            md5(environment),
            md5(COALESCE(tenant_ref, '')),
            started_at DESC
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_forge_check_results_check_started
        ON forge_check_results_v1 (md5(check_id), started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_forge_check_receipts_scope_observed
        ON forge_check_run_receipts_v1 (
            md5(environment),
            md5(COALESCE(tenant_ref, '')),
            observed_at DESC
        )
        """
    )
    op.execute("ALTER TABLE forge_check_results_v1 ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE forge_check_run_receipts_v1 ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE forge_check_results_v1 FROM PUBLIC")
    op.execute("REVOKE ALL ON TABLE forge_check_run_receipts_v1 FROM PUBLIC")
    op.execute(
        """
        GRANT SELECT, INSERT ON TABLE
            forge_check_results_v1,
            forge_check_run_receipts_v1
        TO dataforge_telemetry_ingest
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_results_runtime_insert
        ON forge_check_results_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_results_runtime_select
        ON forge_check_results_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_receipts_runtime_insert
        ON forge_check_run_receipts_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_receipts_runtime_select
        ON forge_check_run_receipts_v1
        """
    )
    op.execute(
        """
        CREATE POLICY forge_check_results_runtime_insert
        ON forge_check_results_v1
        FOR INSERT
        TO dataforge_telemetry_ingest
        WITH CHECK (evaluation_mode = 'debug' AND NOT slo_included)
        """
    )
    op.execute(
        """
        CREATE POLICY forge_check_results_runtime_select
        ON forge_check_results_v1
        FOR SELECT
        TO dataforge_telemetry_ingest
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY forge_check_receipts_runtime_insert
        ON forge_check_run_receipts_v1
        FOR INSERT
        TO dataforge_telemetry_ingest
        WITH CHECK (
            evaluation_mode = 'debug'
            AND NOT slo_included
            AND runner_service_name = 'forgeagents'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY forge_check_receipts_runtime_select
        ON forge_check_run_receipts_v1
        FOR SELECT
        TO dataforge_telemetry_ingest
        USING (true)
        """
    )


def downgrade() -> None:
    """Disable runtime access while retaining all CP4 evidence."""

    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_receipts_runtime_select
        ON forge_check_run_receipts_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_receipts_runtime_insert
        ON forge_check_run_receipts_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_results_runtime_select
        ON forge_check_results_v1
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS forge_check_results_runtime_insert
        ON forge_check_results_v1
        """
    )
    op.execute(
        """
        REVOKE SELECT, INSERT ON TABLE
            forge_check_results_v1,
            forge_check_run_receipts_v1
        FROM dataforge_telemetry_ingest
        """
    )

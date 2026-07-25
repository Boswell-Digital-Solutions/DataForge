\set ON_ERROR_STOP on

DO $proof$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'forge_check_results_v1'
          AND relrowsecurity
    ) OR NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'forge_check_run_receipts_v1'
          AND relrowsecurity
    ) THEN
        RAISE EXCEPTION 'CP4 evidence tables are missing RLS';
    END IF;
    IF NOT has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_results_v1',
        'SELECT,INSERT'
    ) OR NOT has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_run_receipts_v1',
        'SELECT,INSERT'
    ) THEN
        RAISE EXCEPTION 'CP4 evidence table grants are incomplete';
    END IF;
END
$proof$;

SET ROLE dataforge_telemetry_ingest;

INSERT INTO forge_check_results_v1 (
    result_id,
    payload_digest,
    payload,
    run_id,
    check_id,
    check_revision,
    definition_sha256,
    environment,
    tenant_ref,
    evaluation_mode,
    status,
    reason_code,
    started_at,
    finished_at,
    duration_ms,
    assertion_passed,
    slo_included,
    uptime_included,
    baseline_included,
    cost_units_observed,
    privacy_class
)
VALUES (
    '018f5f7b-20a0-7c41-b4b7-4ff70b42d6af',
    repeat('1', 64),
    '{"schema_version":"ForgeCheckResult.v1"}'::jsonb,
    '018f5f7b-1f90-7182-b9f2-f45be5a55773',
    'bds.dataforge.readiness.debug',
    1,
    repeat('2', 64),
    'test',
    'bds-internal',
    'debug',
    'passed',
    'assertion_passed',
    '2026-07-25T05:30:00Z',
    '2026-07-25T05:30:00.043Z',
    43,
    true,
    false,
    false,
    false,
    0,
    'internal'
);

INSERT INTO forge_check_run_receipts_v1 (
    receipt_id,
    payload_digest,
    payload,
    run_id,
    result_id,
    check_id,
    definition_sha256,
    environment,
    tenant_ref,
    source_repository,
    source_commit,
    source_path,
    runner_service_name,
    runner_version,
    trigger,
    evaluation_mode,
    status,
    started_at,
    observed_at,
    slo_included,
    uptime_included,
    baseline_included,
    slo_reason,
    max_cost_units,
    observed_cost_units,
    cost_unit,
    kill_switch_ref,
    kill_switch_enabled,
    evidence_refs
)
VALUES (
    '018f5f7b-20b0-7701-9dda-6f093a386e61',
    repeat('3', 64),
    '{"schema_version":"ForgeCheckRunReceipt.v1"}'::jsonb,
    '018f5f7b-1f90-7182-b9f2-f45be5a55773',
    '018f5f7b-20a0-7c41-b4b7-4ff70b42d6af',
    'bds.dataforge.readiness.debug',
    repeat('2', 64),
    'test',
    'bds-internal',
    'Boswell-Digital-Solutions/DataForge',
    repeat('a', 40),
    'observability/checks/dataforge.readiness.debug.v1.json',
    'forgeagents',
    'cp4.1',
    'ci',
    'debug',
    'passed',
    '2026-07-25T05:30:00Z',
    '2026-07-25T05:30:00.043Z',
    false,
    false,
    false,
    'debug_excluded',
    0,
    0,
    'none',
    'forgechecks.global.enabled',
    true,
    '["018f5f7b-20a0-7c41-b4b7-4ff70b42d6af"]'::jsonb
);

DO $proof$
BEGIN
    BEGIN
        INSERT INTO forge_check_results_v1 (
            result_id,
            payload_digest,
            payload,
            run_id,
            check_id,
            check_revision,
            definition_sha256,
            environment,
            evaluation_mode,
            status,
            reason_code,
            started_at,
            finished_at,
            duration_ms,
            assertion_passed,
            slo_included,
            uptime_included,
            baseline_included,
            cost_units_observed,
            privacy_class
        )
        VALUES (
            '018f5f7b-20a0-7c41-b4b7-4ff70b42d6b0',
            repeat('4', 64),
            '{"schema_version":"ForgeCheckResult.v1"}'::jsonb,
            '018f5f7b-1f90-7182-b9f2-f45be5a55774',
            'bds.invalid.slo',
            1,
            repeat('5', 64),
            'test',
            'debug',
            'passed',
            'assertion_passed',
            '2026-07-25T05:30:00Z',
            '2026-07-25T05:30:00.001Z',
            1,
            true,
            true,
            true,
            true,
            0,
            'internal'
        );
        RAISE EXCEPTION 'debug evidence entered SLO state';
    EXCEPTION
        WHEN check_violation OR insufficient_privilege THEN NULL;
    END;
END
$proof$;

RESET ROLE;

DO $proof$
BEGIN
    IF (SELECT count(*) FROM forge_check_results_v1) <> 1
        OR (SELECT count(*) FROM forge_check_run_receipts_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP4 evidence cardinality mismatch';
    END IF;
END
$proof$;

\echo CP4_FORGE_CHECK_POSTGRES_OK

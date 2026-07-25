\set ON_ERROR_STOP on

DO $proof$
DECLARE
    relation_name TEXT;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'telemetry_derivation_receipts_v1',
        'telemetry_retention_decisions_v1',
        'telemetry_routine_aggregates_v1'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE relname = relation_name
              AND relrowsecurity
        ) THEN
            RAISE EXCEPTION 'CP5 table % is missing RLS', relation_name;
        END IF;
        IF NOT has_table_privilege(
            'dataforge_telemetry_ingest',
            relation_name,
            'SELECT,INSERT'
        ) THEN
            RAISE EXCEPTION 'CP5 table % grants are incomplete', relation_name;
        END IF;
    END LOOP;
END
$proof$;

INSERT INTO forge_events_v1 (
    event_id,
    event_digest,
    schema_version,
    occurred_at,
    received_at,
    service_name,
    environment,
    event_type,
    severity,
    outcome,
    evidence_class,
    attributes,
    metrics,
    privacy_class,
    retention_class,
    sampled,
    sampling_reason
)
VALUES
(
    '55555555-5555-4555-8555-555555555551',
    repeat('1', 64),
    'ForgeEvent.v1',
    '2026-07-25T12:04:59Z',
    '2026-07-25T12:05:00Z',
    'dataforge',
    'test',
    'telemetry.cp5.routine',
    'info',
    'ok',
    'operational',
    '{}',
    '{}',
    'internal',
    'short',
    true,
    'always_on'
),
(
    '55555555-5555-4555-8555-555555555552',
    repeat('2', 64),
    'ForgeEvent.v1',
    '2026-07-25T12:09:59Z',
    '2026-07-25T12:10:00Z',
    'dataforge',
    'test',
    'telemetry.cp5.legal',
    'info',
    'ok',
    'audit',
    '{}',
    '{}',
    'restricted',
    'legal_hold',
    true,
    'always_on'
);

INSERT INTO telemetry_derivation_receipts_v1 (
    receipt_id,
    derivation_id,
    payload_digest,
    payload,
    derivation_type,
    producer_service_name,
    producer_version,
    policy_id,
    policy_version,
    policy_sha256,
    policy_mode,
    clock_basis,
    window_start_at,
    window_end_at,
    output_kind,
    output_ref,
    output_sha256,
    decision_action,
    decision_reason_code,
    decision_applied,
    source_overwritten,
    uncertainty_state,
    source_count,
    created_at
)
VALUES
(
    '55555555-5555-4555-8555-555555555561',
    '55555555-5555-4555-8555-555555555571',
    repeat('3', 64),
    '{
      "schema_version":"TelemetryDerivationReceipt.v1",
      "policy":{"mode":"shadow"},
      "window":{"clock_basis":"received_at"},
      "decision":{"applied":false,"source_overwritten":false}
    }',
    'retention_decision',
    'dataforge',
    'cp5.shadow.v1',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    'received_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'retention_decision',
    '55555555-5555-4555-8555-555555555581',
    repeat('4', 64),
    'aggregate_then_delete',
    'routine_success_short',
    false,
    false,
    'complete',
    1,
    '2026-07-25T13:00:00Z'
),
(
    '55555555-5555-4555-8555-555555555562',
    '55555555-5555-4555-8555-555555555572',
    repeat('5', 64),
    '{
      "schema_version":"TelemetryDerivationReceipt.v1",
      "policy":{"mode":"shadow"},
      "window":{"clock_basis":"received_at"},
      "decision":{"applied":false,"source_overwritten":false}
    }',
    'retention_decision',
    'dataforge',
    'cp5.shadow.v1',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    'received_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'retention_decision',
    '55555555-5555-4555-8555-555555555582',
    repeat('6', 64),
    'legal_hold',
    'legal_hold',
    false,
    false,
    'complete',
    1,
    '2026-07-25T13:00:00Z'
),
(
    '55555555-5555-4555-8555-555555555563',
    '55555555-5555-4555-8555-555555555573',
    repeat('7', 64),
    '{
      "schema_version":"TelemetryDerivationReceipt.v1",
      "policy":{"mode":"shadow"},
      "window":{"clock_basis":"received_at"},
      "decision":{"applied":false,"source_overwritten":false}
    }',
    'routine_success_aggregate',
    'dataforge',
    'cp5.shadow.v1',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    'received_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'routine_success_aggregate',
    '55555555-5555-4555-8555-555555555583',
    repeat('8', 64),
    'aggregate_then_delete',
    'routine_success_short',
    false,
    false,
    'complete',
    1,
    '2026-07-25T13:00:00Z'
);

INSERT INTO telemetry_retention_decisions_v1 (
    decision_id,
    receipt_id,
    source_kind,
    source_ref,
    source_sha256,
    source_received_at,
    service_or_check,
    environment,
    privacy_class,
    retention_class,
    legal_class,
    policy_id,
    policy_version,
    policy_sha256,
    policy_mode,
    clock_basis,
    window_start_at,
    window_end_at,
    action,
    reason_code,
    projected_delete_at,
    applied,
    source_overwritten,
    created_at
)
VALUES
(
    '55555555-5555-4555-8555-555555555581',
    '55555555-5555-4555-8555-555555555561',
    'forge_event',
    '55555555-5555-4555-8555-555555555551',
    repeat('1', 64),
    '2026-07-25T12:05:00Z',
    'dataforge',
    'test',
    'internal',
    'short',
    'standard',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    'received_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'aggregate_then_delete',
    'routine_success_short',
    '2026-08-01T12:05:00Z',
    false,
    false,
    '2026-07-25T13:00:00Z'
),
(
    '55555555-5555-4555-8555-555555555582',
    '55555555-5555-4555-8555-555555555562',
    'forge_event',
    '55555555-5555-4555-8555-555555555552',
    repeat('2', 64),
    '2026-07-25T12:10:00Z',
    'dataforge',
    'test',
    'restricted',
    'legal_hold',
    'legal_hold',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    'received_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'legal_hold',
    'legal_hold',
    NULL,
    false,
    false,
    '2026-07-25T13:00:00Z'
);

INSERT INTO telemetry_routine_aggregates_v1 (
    aggregate_id,
    receipt_id,
    payload_digest,
    payload,
    group_key,
    evidence_kind,
    service_or_check,
    environment,
    privacy_class,
    retention_class,
    decision_reason_code,
    source_count,
    window_start_at,
    window_end_at,
    policy_id,
    policy_version,
    policy_sha256,
    policy_mode,
    created_at
)
VALUES (
    '55555555-5555-4555-8555-555555555583',
    '55555555-5555-4555-8555-555555555563',
    repeat('9', 64),
    '{
      "schema_version":"forge.dataforge.telemetry-routine-aggregate.v1",
      "source_overwritten":false,
      "clock_basis":"received_at",
      "policy_mode":"shadow"
    }',
    repeat('a', 64),
    'forge_event',
    'dataforge',
    'test',
    'internal',
    'short',
    'routine_success_short',
    1,
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'bds.telemetry.retention',
    '1.0.0-shadow',
    '45456fa6cba2992fd6bee9b11ea76b580c4e5b3b1891603034a60c40ea786a52',
    'shadow',
    '2026-07-25T13:00:00Z'
);

DO $proof$
BEGIN
    BEGIN
        INSERT INTO telemetry_derivation_receipts_v1 (
            receipt_id,
            derivation_id,
            payload_digest,
            payload,
            derivation_type,
            producer_service_name,
            producer_version,
            policy_id,
            policy_version,
            policy_sha256,
            policy_mode,
            clock_basis,
            window_start_at,
            window_end_at,
            output_kind,
            output_ref,
            output_sha256,
            decision_action,
            decision_reason_code,
            decision_applied,
            source_overwritten,
            uncertainty_state,
            source_count,
            created_at
        )
        VALUES (
            '55555555-5555-4555-8555-555555555564',
            '55555555-5555-4555-8555-555555555574',
            repeat('b', 64),
            '{
              "schema_version":"TelemetryDerivationReceipt.v1",
              "policy":{"mode":"shadow"},
              "window":{"clock_basis":"received_at"},
              "decision":{"applied":true,"source_overwritten":false}
            }',
            'retention_decision',
            'dataforge',
            'cp5.shadow.v1',
            'bds.telemetry.retention',
            '1.0.0-shadow',
            repeat('c', 64),
            'shadow',
            'received_at',
            '2026-07-25T12:00:00Z',
            '2026-07-25T13:00:00Z',
            'retention_decision',
            '55555555-5555-4555-8555-555555555584',
            repeat('d', 64),
            'delete',
            'invalid_shadow_apply',
            true,
            false,
            'complete',
            1,
            '2026-07-25T13:00:00Z'
        );
        RAISE EXCEPTION 'shadow receipt claimed deletion was applied';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    BEGIN
        UPDATE telemetry_retention_decisions_v1
        SET applied = true
        WHERE decision_id = '55555555-5555-4555-8555-555555555581';
        RAISE EXCEPTION 'shadow decision was mutable to applied state';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    BEGIN
        UPDATE telemetry_retention_decisions_v1
        SET action = 'delete',
            projected_delete_at = '2026-08-01T12:10:00Z'
        WHERE decision_id = '55555555-5555-4555-8555-555555555582';
        RAISE EXCEPTION 'legal-hold decision became deletable';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    IF (SELECT count(*) FROM forge_events_v1) <> 2
        OR (SELECT count(*) FROM telemetry_derivation_receipts_v1) <> 3
        OR (SELECT count(*) FROM telemetry_retention_decisions_v1) <> 2
        OR (SELECT count(*) FROM telemetry_routine_aggregates_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP5 proof cardinality mismatch';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM telemetry_derivation_receipts_v1
        WHERE decision_applied OR source_overwritten
    ) OR EXISTS (
        SELECT 1
        FROM telemetry_retention_decisions_v1
        WHERE applied OR source_overwritten
    ) THEN
        RAISE EXCEPTION 'CP5 shadow state is not inert';
    END IF;
END
$proof$;

\echo CP5_TELEMETRY_DERIVATION_POSTGRES_OK

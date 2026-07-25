\set ON_ERROR_STOP on

DO $proof$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'telemetry_incident_candidates_v1'
          AND relrowsecurity
    ) THEN
        RAISE EXCEPTION 'CP6 candidate table is missing RLS';
    END IF;
    IF NOT has_table_privilege(
        'dataforge_telemetry_ingest',
        'telemetry_incident_candidates_v1',
        'SELECT,INSERT'
    ) THEN
        RAISE EXCEPTION 'CP6 candidate runtime grants are incomplete';
    END IF;
    IF has_table_privilege(
        'dataforge_telemetry_ingest',
        'telemetry_incident_candidates_v1',
        'UPDATE,DELETE,TRUNCATE'
    ) THEN
        RAISE EXCEPTION 'CP6 candidate runtime role has mutation authority';
    END IF;
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
    correlation_id,
    trace_id,
    span_id,
    attributes,
    metrics,
    privacy_class,
    retention_class,
    sampled,
    sampling_reason
)
VALUES (
    '66666666-6666-4666-8666-666666666601',
    repeat('1', 64),
    'ForgeEvent.v1',
    '2026-07-25T12:04:59Z',
    '2026-07-25T12:05:00Z',
    'dataforge',
    'test',
    'telemetry.cp6.correlated_failure',
    'error',
    'fail',
    'operational',
    '550e8400-e29b-41d4-a716-446655440000',
    '4bf92f3577b34da6a3ce929d0e0e4736',
    '00f067aa0ba902b7',
    '{}',
    '{}',
    'internal',
    'long',
    true,
    'always_on'
);

INSERT INTO telemetry_incident_candidates_v1 (
    candidate_id,
    payload_digest,
    payload,
    fingerprint_version,
    fingerprint_sha256,
    environment,
    tenant_ref,
    correlation_id,
    trace_ids,
    window_clock_basis,
    window_start_at,
    window_end_at,
    suspected_cause_code,
    confidence_basis_points,
    confidence_method,
    uncertainty_state,
    privacy_class,
    analysis_kind,
    producer_service,
    producer_version,
    provider,
    model,
    prompt_sha256,
    model_response_sha256,
    run_receipt_ref,
    candidate_only,
    can_repair,
    can_rollback,
    can_notify,
    can_promote,
    requires_human_decision,
    source_overwritten,
    created_at
)
VALUES (
    '66666666-6666-4666-8666-666666666611',
    repeat('a', 64),
    '{
      "schema_version":"IncidentCandidate.v1",
      "candidate_id":"66666666-6666-4666-8666-666666666611",
      "created_at":"2026-07-25T13:01:00Z",
      "environment":"test",
      "tenant_ref":null,
      "correlation_id":"550e8400-e29b-41d4-a716-446655440000",
      "trace_ids":["4bf92f3577b34da6a3ce929d0e0e4736"],
      "window":{
        "clock_basis":"evidence_observed_at",
        "start_at":"2026-07-25T12:00:00Z",
        "end_at":"2026-07-25T13:00:00Z"
      },
      "source_evidence":[{
        "evidence_kind":"forge_event",
        "evidence_ref":"66666666-6666-4666-8666-666666666601",
        "sha256":"1111111111111111111111111111111111111111111111111111111111111111",
        "observed_at":"2026-07-25T12:05:00Z",
        "clock_basis":"received_at",
        "privacy_class":"internal",
        "retention_class":"long",
        "legal_class":"standard"
      }],
      "suspected_cause":{
        "cause_code":"correlated_service_failure",
        "summary":"A failed observation occurred in the evidence window.",
        "evidence_refs":["66666666-6666-4666-8666-666666666601"]
      },
      "alternatives":[{
        "cause_code":"recent_change",
        "summary":"A recent change remains possible but unproved.",
        "evidence_refs":[]
      }],
      "confidence":{
        "score_basis_points":7200,
        "method":"deterministic_rules",
        "calibration_version":"cp6.rules.v1"
      },
      "uncertainty":{
        "state":"partial",
        "reason_codes":["change_evidence_missing"]
      },
      "missing_evidence":["deployment_change_evidence"],
      "deduplication":{
        "fingerprint_version":"incident-candidate-fingerprint.v1",
        "fingerprint_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      },
      "analysis_provenance":{
        "analysis_kind":"deterministic_rules",
        "producer_service":"dataforge",
        "producer_version":"cp6.1",
        "provider":null,
        "model":null,
        "prompt_sha256":null,
        "model_response_sha256":null,
        "run_receipt_ref":null
      },
      "privacy_class":"internal",
      "authority":{
        "classification":"derived_candidate",
        "candidate_only":true,
        "can_repair":false,
        "can_rollback":false,
        "can_notify":false,
        "can_promote":false,
        "requires_human_decision":true,
        "source_overwritten":false
      }
    }',
    'incident-candidate-fingerprint.v1',
    repeat('b', 64),
    'test',
    NULL,
    '550e8400-e29b-41d4-a716-446655440000',
    '["4bf92f3577b34da6a3ce929d0e0e4736"]',
    'evidence_observed_at',
    '2026-07-25T12:00:00Z',
    '2026-07-25T13:00:00Z',
    'correlated_service_failure',
    7200,
    'deterministic_rules',
    'partial',
    'internal',
    'deterministic_rules',
    'dataforge',
    'cp6.1',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    true,
    false,
    false,
    false,
    false,
    true,
    false,
    '2026-07-25T13:01:00Z'
);

DO $proof$
BEGIN
    BEGIN
        UPDATE telemetry_incident_candidates_v1
        SET can_repair = true
        WHERE candidate_id = '66666666-6666-4666-8666-666666666611';
        RAISE EXCEPTION 'CP6 candidate accepted repair authority';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    BEGIN
        UPDATE telemetry_incident_candidates_v1
        SET provider = 'unproved-provider'
        WHERE candidate_id = '66666666-6666-4666-8666-666666666611';
        RAISE EXCEPTION 'CP6 deterministic candidate accepted model provenance';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    IF (
        SELECT event_digest
        FROM forge_events_v1
        WHERE event_id = '66666666-6666-4666-8666-666666666601'
    ) <> repeat('1', 64) THEN
        RAISE EXCEPTION 'CP6 candidate proof rewrote source evidence';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM telemetry_incident_candidates_v1
        WHERE candidate_id = '66666666-6666-4666-8666-666666666611'
          AND candidate_only
          AND NOT can_repair
          AND NOT can_rollback
          AND NOT can_notify
          AND NOT can_promote
          AND requires_human_decision
          AND NOT source_overwritten
    ) THEN
        RAISE EXCEPTION 'CP6 candidate authority invariants are absent';
    END IF;
END
$proof$;

SET ROLE dataforge_telemetry_ingest;
SELECT candidate_id
FROM telemetry_incident_candidates_v1
WHERE candidate_id = '66666666-6666-4666-8666-666666666611';
RESET ROLE;

SELECT 'CP6_TELEMETRY_POSTGRES_MIGRATION_OK' AS proof;

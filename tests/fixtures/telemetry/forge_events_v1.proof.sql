\set ON_ERROR_STOP on

-- Model the physically retained pre-v1 shape only to prove it is untouched.
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    service VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    correlation_id UUID,
    metadata JSONB,
    metrics JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO events (
    event_id,
    timestamp,
    service,
    event_type,
    severity,
    metadata,
    metrics
)
VALUES (
    '11111111-1111-4111-8111-111111111111',
    '2026-07-23T17:00:00Z',
    'pre-v1-service',
    'pre_v1_event',
    'info',
    '{"preserve": true}',
    '{}'
);

\ir forge_events_v1.proposed.sql

DO $proof$
DECLARE
    event JSONB := '{
      "schema_version": "ForgeEvent.v1",
      "event_id": "22222222-2222-4222-8222-222222222222",
      "occurred_at": "2026-07-23T18:00:00Z",
      "service_name": "forgeagents",
      "service_instance_id": "forgeagents-staging-1",
      "environment": "staging",
      "tenant_ref": null,
      "event_type": "fpvs.readiness.checked",
      "severity": "info",
      "outcome": "ok",
      "evidence_class": "operational",
      "correlation_id": "33333333-3333-4333-8333-333333333333",
      "trace_id": "0123456789abcdef0123456789abcdef",
      "span_id": "0123456789abcdef",
      "parent_span_id": null,
      "attributes": {"check": "fpvs", "ready": true},
      "metrics": {"duration_ms": 12},
      "privacy_class": "internal",
      "retention_class": "standard",
      "sampled": true,
      "sample_rate": null,
      "sampling_reason": "always_on"
    }'::JSONB;
    result TEXT;
    first_received_at TIMESTAMPTZ;
BEGIN
    result := ingest_forge_event_v1(event, repeat('a', 64)::CHAR(64));
    IF result <> 'inserted' THEN
        RAISE EXCEPTION 'first insert returned %', result;
    END IF;

    SELECT received_at
    INTO STRICT first_received_at
    FROM forge_events_v1
    WHERE event_id = (event ->> 'event_id')::UUID;

    PERFORM pg_sleep(0.01);
    result := ingest_forge_event_v1(event, repeat('a', 64)::CHAR(64));
    IF result <> 'exact_replay' THEN
        RAISE EXCEPTION 'replay returned %', result;
    END IF;

    IF (
        SELECT received_at <> first_received_at
        FROM forge_events_v1
        WHERE event_id = (event ->> 'event_id')::UUID
    ) THEN
        RAISE EXCEPTION 'exact replay changed sink received_at';
    END IF;

    result := ingest_forge_event_v1(
        jsonb_set(event, '{attributes,ready}', 'false'::JSONB),
        repeat('b', 64)::CHAR(64)
    );
    IF result <> 'event_identity_conflict' THEN
        RAISE EXCEPTION 'content collision returned %', result;
    END IF;

    IF (SELECT count(*) FROM forge_events_v1) <> 1 THEN
        RAISE EXCEPTION 'identity conflict changed canonical row count';
    END IF;

    IF (SELECT count(*) FROM events) <> 1 THEN
        RAISE EXCEPTION 'canonical proof changed pre-v1 row count';
    END IF;
END
$proof$;

DO $proof$
DECLARE
    canonical JSONB;
    candidate JSONB;
BEGIN
    SELECT to_jsonb(stored) - 'received_at' - 'event_digest'
    INTO STRICT canonical
    FROM forge_events_v1 AS stored
    LIMIT 1;

    candidate := jsonb_set(
        jsonb_set(
            canonical,
            '{event_id}',
            '"44444444-4444-4444-8444-444444444444"'::JSONB
        ),
        '{trace_id}',
        to_jsonb(repeat('0', 32))
    );
    BEGIN
        PERFORM ingest_forge_event_v1(
            candidate,
            repeat('c', 64)::CHAR(64)
        );
        RAISE EXCEPTION 'zero trace ID unexpectedly passed';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    candidate := jsonb_set(
        jsonb_set(
            canonical,
            '{event_id}',
            '"55555555-5555-4555-8555-555555555555"'::JSONB
        ),
        '{metrics}',
        '{"invalid_boolean": true}'::JSONB
    );
    BEGIN
        PERFORM ingest_forge_event_v1(
            candidate,
            repeat('d', 64)::CHAR(64)
        );
        RAISE EXCEPTION 'boolean metric unexpectedly passed';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    BEGIN
        PERFORM ingest_forge_event_v1(
            '{
              "event_id": "66666666-6666-4666-8666-666666666666",
              "timestamp": "2026-07-23T18:00:00Z",
              "service": "pre-v1-service"
            }'::JSONB,
            repeat('e', 64)::CHAR(64)
        );
        RAISE EXCEPTION 'pre-v1 shape unexpectedly passed';
    EXCEPTION
        WHEN not_null_violation OR invalid_text_representation THEN NULL;
    END;

    IF (SELECT count(*) FROM forge_events_v1) <> 1 THEN
        RAISE EXCEPTION 'invalid payload proof changed canonical row count';
    END IF;
END
$proof$;

DO $proof$
DECLARE
    capability JSONB;
BEGIN
    SELECT forge_telemetry_sink_capability_v1.capability
    INTO STRICT capability
    FROM forge_telemetry_sink_capability_v1;

    IF capability ->> 'write_enabled' <> 'false'
        OR capability ->> 'pre_v1_fallback' <> 'false'
        OR capability ->> 'dual_write' <> 'false'
        OR jsonb_array_length(capability -> 'supported_fields') <> 24
        OR NOT capability -> 'supported_fields' ? 'event_digest'
        OR NOT capability -> 'supported_fields' ? 'received_at'
    THEN
        RAISE EXCEPTION 'proof capability differs from the proved sink contract';
    END IF;
END
$proof$;

-- A rollback disables the canonical writer but preserves its evidence and does
-- not re-enable the pre-v1 writer. The proof therefore leaves both physical
-- tables intact and verifies the canonical row after the disabled handshake.
DO $proof$
BEGIN
    IF (SELECT count(*) FROM forge_events_v1) <> 1 THEN
        RAISE EXCEPTION 'rollback rehearsal erased canonical evidence';
    END IF;
    IF (SELECT count(*) FROM events) <> 1 THEN
        RAISE EXCEPTION 'rollback rehearsal changed pre-v1 evidence';
    END IF;
END
$proof$;

SELECT 'FORGE_EVENT_V1_POSTGRES_PROOF_OK' AS proof_result;

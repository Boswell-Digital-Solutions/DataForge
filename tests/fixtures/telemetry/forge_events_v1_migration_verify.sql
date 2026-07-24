\set ON_ERROR_STOP on

DO $proof$
DECLARE
    candidate JSONB := '{
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
    first_received_at TIMESTAMPTZ;
    replay_received_at TIMESTAMPTZ;
    outcome TEXT;
BEGIN
    outcome := ingest_forge_event_v1(candidate, repeat('a', 64)::CHAR(64));
    IF outcome <> 'inserted' THEN
        RAISE EXCEPTION 'canonical insert returned %', outcome;
    END IF;

    SELECT received_at INTO STRICT first_received_at
    FROM forge_events_v1
    WHERE event_id = (candidate ->> 'event_id')::UUID;

    outcome := ingest_forge_event_v1(candidate, repeat('a', 64)::CHAR(64));
    IF outcome <> 'exact_replay' THEN
        RAISE EXCEPTION 'canonical replay returned %', outcome;
    END IF;

    SELECT received_at INTO STRICT replay_received_at
    FROM forge_events_v1
    WHERE event_id = (candidate ->> 'event_id')::UUID;

    IF replay_received_at <> first_received_at THEN
        RAISE EXCEPTION 'exact replay changed sink-owned received_at';
    END IF;

    candidate := jsonb_set(candidate, '{event_type}', '"fpvs.readiness.failed"');
    outcome := ingest_forge_event_v1(candidate, repeat('b', 64)::CHAR(64));
    IF outcome <> 'event_identity_conflict' THEN
        RAISE EXCEPTION 'identity conflict returned %', outcome;
    END IF;

    IF (SELECT count(*) FROM forge_events_v1) <> 1 THEN
        RAISE EXCEPTION 'identity conflict changed canonical row count';
    END IF;
END
$proof$;

-- Long schema-valid identifiers stay insertable because indexed lookup
-- projections hash unbounded contract identifiers instead of imposing an
-- unapproved length limit or risking a B-tree index-row failure.
DO $proof$
DECLARE
    candidate JSONB := jsonb_build_object(
        'schema_version', 'ForgeEvent.v1',
        'event_id', '44444444-4444-4444-8444-444444444444',
        'occurred_at', '2026-07-23T18:01:00Z',
        'service_name', repeat('a', 10000),
        'service_instance_id', NULL,
        'environment', 'staging',
        'tenant_ref', NULL,
        'event_type', 'boundary.long_identifier',
        'severity', 'info',
        'outcome', 'ok',
        'evidence_class', 'diagnostic',
        'correlation_id', NULL,
        'trace_id', NULL,
        'span_id', NULL,
        'parent_span_id', NULL,
        'attributes', '{}'::JSONB,
        'metrics', '{}'::JSONB,
        'privacy_class', 'internal',
        'retention_class', 'short',
        'sampled', false,
        'sample_rate', NULL,
        'sampling_reason', 'rate_limited'
    );
BEGIN
    IF ingest_forge_event_v1(candidate, repeat('c', 64)::CHAR(64)) <> 'inserted' THEN
        RAISE EXCEPTION 'long canonical identifier insert failed';
    END IF;
END
$proof$;

DO $proof$
BEGIN
    IF NOT (
        SELECT relrowsecurity
        FROM pg_class
        WHERE oid = 'forge_events_v1'::REGCLASS
    ) THEN
        RAISE EXCEPTION 'canonical telemetry table does not have RLS enabled';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.role_table_grants
        WHERE table_schema = 'public'
          AND table_name = 'forge_events_v1'
          AND grantee = 'PUBLIC'
    ) THEN
        RAISE EXCEPTION 'canonical telemetry surface grants PUBLIC access';
    END IF;

    IF (SELECT count(*) FROM events) <> 1
        OR (
            SELECT service
            FROM events
            WHERE event_id = '11111111-1111-4111-8111-111111111111'
        ) <> 'pre-v1-service'
    THEN
        RAISE EXCEPTION 'canonical migration changed pre-v1 evidence';
    END IF;
END
$proof$;

SELECT 'FORGE_EVENT_V1_MIGRATION_OK' AS proof_result;

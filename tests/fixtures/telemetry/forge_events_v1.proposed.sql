-- Proof-only ForgeEvent.v1 PostgreSQL shape.
-- This file is executed only inside an ephemeral pg_virtualenv cluster.
-- It is not an Alembic migration and does not authorize production writes.

CREATE FUNCTION forge_jsonb_object_values_are_numbers(candidate JSONB)
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
STRICT
AS $$
    SELECT
        jsonb_typeof(candidate) = 'object'
        AND NOT EXISTS (
            SELECT 1
            FROM jsonb_each(candidate) AS entry
            WHERE jsonb_typeof(entry.value) <> 'number'
        )
$$;

CREATE TABLE forge_events_v1 (
    event_id UUID PRIMARY KEY,
    event_digest CHAR(64) NOT NULL
        CHECK (event_digest ~ '^[0-9a-f]{64}$'),
    schema_version TEXT NOT NULL
        CHECK (schema_version = 'ForgeEvent.v1'),
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    service_name TEXT NOT NULL
        CHECK (service_name ~ '^[a-z0-9][a-z0-9._:-]*$'),
    service_instance_id TEXT
        CHECK (
            service_instance_id IS NULL
            OR service_instance_id ~ '^[a-z0-9][a-z0-9._:-]*$'
        ),
    environment TEXT NOT NULL
        CHECK (environment ~ '^[a-z0-9][a-z0-9._:-]*$'),
    tenant_ref TEXT
        CHECK (
            tenant_ref IS NULL
            OR tenant_ref ~ '^[a-z0-9][a-z0-9._:-]*$'
        ),
    event_type TEXT NOT NULL
        CHECK (event_type ~ '^[a-z0-9][a-z0-9._:-]*$'),
    severity TEXT NOT NULL
        CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    outcome TEXT NOT NULL
        CHECK (
            outcome IN (
                'ok',
                'warn',
                'fail',
                'cancelled',
                'insufficient_signal',
                'blocked'
            )
        ),
    evidence_class TEXT NOT NULL
        CHECK (evidence_class IN ('diagnostic', 'operational', 'audit', 'security')),
    correlation_id UUID,
    trace_id TEXT
        CHECK (
            trace_id IS NULL
            OR (
                trace_id ~ '^[0-9a-f]{32}$'
                AND trace_id <> repeat('0', 32)
            )
        ),
    span_id TEXT
        CHECK (
            span_id IS NULL
            OR (
                span_id ~ '^[0-9a-f]{16}$'
                AND span_id <> repeat('0', 16)
            )
        ),
    parent_span_id TEXT
        CHECK (
            parent_span_id IS NULL
            OR (
                parent_span_id ~ '^[0-9a-f]{16}$'
                AND parent_span_id <> repeat('0', 16)
            )
        ),
    attributes JSONB NOT NULL
        CHECK (jsonb_typeof(attributes) = 'object'),
    metrics JSONB NOT NULL
        CHECK (forge_jsonb_object_values_are_numbers(metrics)),
    privacy_class TEXT NOT NULL
        CHECK (privacy_class IN ('public', 'internal', 'restricted', 'confidential')),
    retention_class TEXT NOT NULL
        CHECK (
            retention_class IN ('ephemeral', 'short', 'standard', 'long', 'legal_hold')
        ),
    sampled BOOLEAN NOT NULL,
    sample_rate DOUBLE PRECISION
        CHECK (sample_rate IS NULL OR (sample_rate > 0 AND sample_rate <= 1)),
    sampling_reason TEXT NOT NULL
        CHECK (
            sampling_reason IN (
                'always_on',
                'probabilistic',
                'rate_limited',
                'required_stub',
                'policy'
            )
        ),
    CHECK (
        (trace_id IS NULL AND span_id IS NULL AND parent_span_id IS NULL)
        OR (trace_id IS NOT NULL AND span_id IS NULL AND parent_span_id IS NULL)
        OR (
            trace_id IS NOT NULL
            AND span_id IS NOT NULL
            AND (parent_span_id IS NULL OR parent_span_id <> span_id)
        )
    ),
    CHECK (
        (
            sampling_reason = 'probabilistic'
            AND sample_rate IS NOT NULL
        )
        OR (
            sampling_reason <> 'probabilistic'
            AND sample_rate IS NULL
        )
    ),
    CHECK (
        (
            sampled
            AND sampling_reason IN ('always_on', 'probabilistic', 'policy')
        )
        OR (
            NOT sampled
            AND sampling_reason IN ('rate_limited', 'required_stub', 'policy')
        )
    )
);

CREATE INDEX ix_forge_events_v1_received_at
    ON forge_events_v1 (received_at);
CREATE INDEX ix_forge_events_v1_service_occurred_at
    ON forge_events_v1 (service_name, occurred_at DESC);
CREATE INDEX ix_forge_events_v1_environment_tenant_occurred_at
    ON forge_events_v1 (environment, tenant_ref, occurred_at DESC);
CREATE INDEX ix_forge_events_v1_trace_id
    ON forge_events_v1 (trace_id)
    WHERE trace_id IS NOT NULL;
CREATE INDEX ix_forge_events_v1_retention_received_at
    ON forge_events_v1 (retention_class, received_at);

CREATE FUNCTION ingest_forge_event_v1(
    candidate JSONB,
    candidate_digest CHAR(64)
)
RETURNS TEXT
LANGUAGE PLPGSQL
AS $$
DECLARE
    inserted_event_id UUID;
    stored forge_events_v1%ROWTYPE;
BEGIN
    INSERT INTO forge_events_v1 (
        event_id,
        event_digest,
        schema_version,
        occurred_at,
        service_name,
        service_instance_id,
        environment,
        tenant_ref,
        event_type,
        severity,
        outcome,
        evidence_class,
        correlation_id,
        trace_id,
        span_id,
        parent_span_id,
        attributes,
        metrics,
        privacy_class,
        retention_class,
        sampled,
        sample_rate,
        sampling_reason
    )
    VALUES (
        (candidate ->> 'event_id')::UUID,
        candidate_digest,
        candidate ->> 'schema_version',
        (candidate ->> 'occurred_at')::TIMESTAMPTZ,
        candidate ->> 'service_name',
        candidate ->> 'service_instance_id',
        candidate ->> 'environment',
        candidate ->> 'tenant_ref',
        candidate ->> 'event_type',
        candidate ->> 'severity',
        candidate ->> 'outcome',
        candidate ->> 'evidence_class',
        (candidate ->> 'correlation_id')::UUID,
        candidate ->> 'trace_id',
        candidate ->> 'span_id',
        candidate ->> 'parent_span_id',
        candidate -> 'attributes',
        candidate -> 'metrics',
        candidate ->> 'privacy_class',
        candidate ->> 'retention_class',
        (candidate ->> 'sampled')::BOOLEAN,
        (candidate ->> 'sample_rate')::DOUBLE PRECISION,
        candidate ->> 'sampling_reason'
    )
    ON CONFLICT (event_id) DO NOTHING
    RETURNING event_id INTO inserted_event_id;

    IF inserted_event_id IS NOT NULL THEN
        RETURN 'inserted';
    END IF;

    SELECT *
    INTO STRICT stored
    FROM forge_events_v1
    WHERE event_id = (candidate ->> 'event_id')::UUID;

    IF stored.event_digest = candidate_digest
        AND stored.schema_version = candidate ->> 'schema_version'
        AND stored.service_name = candidate ->> 'service_name'
        AND stored.service_instance_id IS NOT DISTINCT FROM candidate ->> 'service_instance_id'
        AND stored.environment = candidate ->> 'environment'
        AND stored.tenant_ref IS NOT DISTINCT FROM candidate ->> 'tenant_ref'
    THEN
        RETURN 'exact_replay';
    END IF;

    RETURN 'event_identity_conflict';
END
$$;

CREATE VIEW forge_telemetry_sink_capability_v1 AS
SELECT jsonb_build_object(
    'schema_version', 'ForgeTelemetrySinkCapability.v1',
    'storage_schema_version', 'forge.dataforge.telemetry.v1',
    'event_schema_versions', jsonb_build_array('ForgeEvent.v1'),
    'event_schema_sha256',
        '165ff1ba01d6a4a9b456f77c22c3b664deeb9044c5000daae98deedabdab57d2',
    'event_digest_profile_sha256',
        '024d16505a26c5569d5d2c08a834ae7e635f7f0abf77803c54da17c55aba5b7c',
    'canonicalization', 'RFC8785-JCS',
    'resource_bounds_schema_version', 'forge.telemetry.resource_bounds.v1',
    'resource_bounds_sha256',
        '6729e46ea46544095c1e7dd8bcdb9df9eec84df1889b9e4439db6b3f998eb919',
    'max_canonical_event_bytes', 65536,
    'supported_fields',
        jsonb_build_array(
            'schema_version',
            'event_id',
            'event_digest',
            'occurred_at',
            'received_at',
            'service_name',
            'service_instance_id',
            'environment',
            'tenant_ref',
            'event_type',
            'severity',
            'outcome',
            'evidence_class',
            'correlation_id',
            'trace_id',
            'span_id',
            'parent_span_id',
            'attributes',
            'metrics',
            'privacy_class',
            'retention_class',
            'sampled',
            'sample_rate',
            'sampling_reason'
        ),
    'received_at_owner', 'sink',
    'content_bound_identity', true,
    'identity_outcomes',
        jsonb_build_array('inserted', 'exact_replay', 'identity_conflict'),
    'pre_v1_fallback', false,
    'dual_write', false,
    'write_enabled', false
) AS capability;

\set ON_ERROR_STOP on

-- Model the physically retained pre-v1 evidence. The canonical migration may
-- not reinterpret, update, alias, or delete this row.
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    service TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
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
    '{"source":"pre-v1"}',
    '{}'
);

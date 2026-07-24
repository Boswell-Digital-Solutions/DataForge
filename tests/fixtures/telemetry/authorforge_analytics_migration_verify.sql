\set ON_ERROR_STOP on

DO $proof$
DECLARE
    stored_count INTEGER;
BEGIN
    IF to_regclass('public.authorforge_analytics_events') IS NULL THEN
        RAISE EXCEPTION 'dedicated AuthorForge analytics table is missing';
    END IF;

    IF NOT (
        SELECT relrowsecurity
        FROM pg_class
        WHERE oid = 'public.authorforge_analytics_events'::regclass
    ) THEN
        RAISE EXCEPTION 'AuthorForge analytics RLS is not enabled';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.role_table_grants
        WHERE table_schema = 'public'
          AND table_name = 'authorforge_analytics_events'
          AND grantee = 'PUBLIC'
    ) THEN
        RAISE EXCEPTION 'PUBLIC retains AuthorForge analytics table privileges';
    END IF;

    INSERT INTO authorforge_analytics_events (
        event_id,
        event_digest,
        canonical_bytes,
        schema_version,
        policy_version,
        occurred_at,
        event_type,
        dimensions,
        metrics
    )
    VALUES (
        '5eb1b0cc-86bb-475b-a9c8-48f487fa6071',
        repeat('a', 64),
        512,
        'AuthorForgeAnalyticsEnvelope.v1',
        'authorforge-analytics-policy.v1',
        '2026-07-20T16:00:00Z',
        'workflow_completed',
        '{
            "product": "authorforge",
            "application": "desktop",
            "build_version": "1.4.0",
            "execution_lane": "local",
            "route_classification": "local_only",
            "content_authority": "authorforge_embedded_database",
            "status": "success",
            "offline": true
        }'::JSONB,
        '{"operation_count": 1, "duration_ms": 37}'::JSONB
    );

    BEGIN
        INSERT INTO authorforge_analytics_events (
            event_id,
            event_digest,
            canonical_bytes,
            schema_version,
            policy_version,
            occurred_at,
            event_type,
            dimensions,
            metrics
        )
        VALUES (
            '8ad4232d-8b80-47f3-b7ce-4ab7ebc2557c',
            repeat('b', 64),
            512,
            'AuthorForgeAnalyticsEnvelope.v1',
            'authorforge-analytics-policy.v1',
            clock_timestamp(),
            'workflow_completed',
            '{"product": "authorforge", "manuscript": "must fail"}'::JSONB,
            '{}'::JSONB
        );
        RAISE EXCEPTION 'content-capable analytics dimension was accepted';
    EXCEPTION
        WHEN check_violation THEN
            NULL;
    END;

    BEGIN
        INSERT INTO authorforge_analytics_events (
            event_id,
            event_digest,
            canonical_bytes,
            schema_version,
            policy_version,
            occurred_at,
            event_type,
            dimensions,
            metrics
        )
        VALUES (
            'a92749fb-a9c3-4295-99e8-e5ce87868ad3',
            repeat('c', 64),
            512,
            'AuthorForgeAnalyticsEnvelope.v1',
            'authorforge-analytics-policy.v1',
            clock_timestamp(),
            'workflow_completed',
            '{"product": "authorforge"}'::JSONB,
            '{"duration_ms": "not-a-number"}'::JSONB
        );
        RAISE EXCEPTION 'non-numeric AuthorForge analytics metric was accepted';
    EXCEPTION
        WHEN check_violation THEN
            NULL;
    END;

    SELECT count(*)
    INTO stored_count
    FROM authorforge_analytics_events;

    IF stored_count <> 1 THEN
        RAISE EXCEPTION 'AuthorForge analytics constraint proof left % rows', stored_count;
    END IF;
END
$proof$;

SELECT 'AUTHORFORGE_ANALYTICS_MIGRATION_OK' AS proof_result;

\set ON_ERROR_STOP on

DO $proof$
BEGIN
    IF to_regclass('public.forge_events_v1') IS NULL THEN
        RAISE EXCEPTION 'failed downgrade erased canonical evidence';
    END IF;
    IF (SELECT count(*) FROM forge_events_v1) <> 4 THEN
        RAISE EXCEPTION 'failed downgrade changed canonical evidence';
    END IF;
    IF (SELECT count(*) FROM events) <> 1 THEN
        RAISE EXCEPTION 'failed downgrade changed pre-v1 evidence';
    END IF;
END
$proof$;

SELECT 'FORGE_EVENT_V1_ROLLBACK_PRESERVES_EVIDENCE_OK' AS proof_result;

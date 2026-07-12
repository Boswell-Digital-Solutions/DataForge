-- ============================================================================
-- Supabase hardening + maintenance for DataForge's Postgres
-- ============================================================================
-- Context: this ecosystem is a single-operator backend. Services (DataForge,
-- NeuroForge, Rake) connect to Postgres DIRECTLY as the `postgres` owner role,
-- NOT via Supabase's PostgREST/anon Data API. The owner role bypasses RLS, so
-- enabling RLS does not affect the services — it only denies the public Data API.
--
-- Run in the Supabase SQL editor (as the privileged role). Every statement is
-- idempotent and safe to re-run. Run sections top-to-bottom.
--
-- NOTE: the two credential tables (llm_secrets, api_keys) also enable RLS in
-- application code at creation (app/api/secrets_router.py, app/auth/api_keys.py),
-- so they self-protect on a fresh DB even before this script is run.
--
-- DRIFT WARNING (2026-07-11): because this script lives outside the deploy
-- pipeline, ten tables created by migrations after this script was first run
-- (20260606_01 .. 20260623_01) shipped with RLS disabled and tripped
-- Supabase's rls_disabled_in_public advisor. The fix is now a real Alembic
-- migration -- alembic/versions/20260711_01_enable_rls_on_drifted_public_tables.py
-- -- which runs automatically on every deploy via `alembic upgrade head`
-- (scripts/render-build.sh) and re-scans pg_tables each time, so it cannot
-- drift the same way this script did. This script is kept for the one-time
-- PK/index sections (2-3) and as a historical record; it does not need to be
-- re-run by hand for RLS going forward.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Section 1 — RLS deny-all on every public table
-- ----------------------------------------------------------------------------
-- ENABLE (never FORCE): the postgres owner still bypasses RLS; anon/authenticated
-- (PostgREST) get no access because no policies exist. This is the intended
-- posture for a service-only backend (no Supabase end-user auth, no multitenancy).
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', r.tablename);
  END LOOP;
END $$;


-- ----------------------------------------------------------------------------
-- Section 2 — document_tags: add a primary key
-- ----------------------------------------------------------------------------
-- Association table (document_id -> documents.id, tag_id -> tags.id) created
-- without a PK and with nullable columns. Drop orphan rows (NULL side) and exact
-- duplicate pairs, then add the composite PK (which also covers the document_id FK).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'document_tags_pkey'
      AND conrelid = 'public.document_tags'::regclass
  ) THEN
    DELETE FROM public.document_tags WHERE document_id IS NULL OR tag_id IS NULL;
    DELETE FROM public.document_tags a USING public.document_tags b
      WHERE a.ctid < b.ctid
        AND a.document_id = b.document_id
        AND a.tag_id = b.tag_id;
    ALTER TABLE public.document_tags
      ALTER COLUMN document_id SET NOT NULL,
      ALTER COLUMN tag_id      SET NOT NULL;
    ALTER TABLE public.document_tags
      ADD CONSTRAINT document_tags_pkey PRIMARY KEY (document_id, tag_id);
  END IF;
END $$;


-- ----------------------------------------------------------------------------
-- Section 3 — covering indexes for every unindexed foreign key in public
-- ----------------------------------------------------------------------------
-- Finds each FK whose columns are not already the leading columns of some index
-- and creates one. Idempotent (CREATE INDEX IF NOT EXISTS + coverage check).
-- For very large/write-heavy tables, build that index with CREATE INDEX
-- CONCURRENTLY outside a transaction instead.
DO $$
DECLARE fk record; col_list text; idx_name text;
BEGIN
  FOR fk IN
    SELECT con.conrelid, con.conname, con.conkey
    FROM pg_constraint con
    JOIN pg_class c     ON c.oid = con.conrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE con.contype = 'f' AND n.nspname = 'public'
  LOOP
    IF EXISTS (
      SELECT 1 FROM pg_index i
      WHERE i.indrelid = fk.conrelid
        AND (string_to_array(i.indkey::text, ' ')::int2[])[1:array_length(fk.conkey,1)] = fk.conkey
    ) THEN CONTINUE; END IF;

    SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY k.ord)
      INTO col_list
    FROM unnest(fk.conkey) WITH ORDINALITY AS k(attnum, ord)
    JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = k.attnum;

    idx_name := left('ix_fk_' || replace(fk.conname, '_fkey', ''), 63);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (%s);',
                   idx_name, fk.conrelid::regclass, col_list);
    RAISE NOTICE 'FK index: % ON % (%)', idx_name, fk.conrelid::regclass, col_list;
  END LOOP;
END $$;


-- ----------------------------------------------------------------------------
-- Section 4 — verification
-- ----------------------------------------------------------------------------
-- (a) any public table still missing RLS (should be empty):
SELECT c.relname AS table_without_rls
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity IS FALSE
ORDER BY 1;

-- (b) any FK still without a covering index (should be empty):
SELECT con.conrelid::regclass AS tbl, con.conname
FROM pg_constraint con
JOIN pg_namespace n ON n.oid = con.connamespace
WHERE con.contype='f' AND n.nspname='public'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = con.conrelid
      AND (string_to_array(i.indkey::text,' ')::int2[])[1:array_length(con.conkey,1)] = con.conkey)
ORDER BY 1;

-- NOTE: "unused index" linter findings are intentionally NOT acted on here — the
-- linter only observes sampled traffic; review each before dropping.

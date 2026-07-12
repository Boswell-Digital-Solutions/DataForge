"""enable RLS on public tables that drifted since the 2026-06-02 Supabase hardening pass

Supabase's Security Advisor flagged `rls_disabled_in_public` against the
DataForgedb project (ref embvfponjxejbtrkryzs). Root cause: on 2026-06-02,
commit e9fd9c2 ran sql/supabase_rls_and_indexes.sql by hand in the Supabase
SQL editor, enabling RLS on every public table that existed at that time.
That script is *not* wired into the deploy pipeline. Ten tables were created
by later Alembic migrations (20260606_01 .. 20260623_01) and never got the
same treatment, so they ship with RLS disabled:

  agent_memories, context_packs, model_outcomes, cssa_decisions,
  cssa_authorizations, cssa_outcomes, cssa_counters,
  cssa_quota_reservations, cssa_authorization_consumptions,
  supabase_log_events

(An eleventh, healing_proposals, was created and dropped in the same window
— 20260606_02/03 — so it no longer exists.)

This ecosystem has no Supabase end-user auth and no multitenancy: every
legitimate reader/writer (DataForge itself, the poll_supabase_logs.py cron)
connects with the Postgres owner role via DATAFORGE_DATABASE_URL, which
bypasses RLS entirely regardless of policies (see app/database.py and
sql/supabase_rls_and_indexes.sql's header comment). The only thing "RLS
enabled, zero policies" affects is Supabase's PostgREST anon/authenticated
Data API, which nothing in this ecosystem uses for these tables. A deny-all
posture is therefore both correct and the smallest possible fix — it matches
the precedent already set for llm_secrets/api_keys (which self-protect at
creation in app/api/secrets_router.py and app/auth/api_keys.py) and the
original hardening script.

Unlike that one-off SQL-editor script, this migration runs automatically via
`python -m alembic upgrade head` on every deploy (scripts/render-build.sh),
so — unlike the manual script — it cannot drift again: any future public
table that ships without RLS is caught and closed the next time this
migration chain runs, not just the ten known today.

Revision ID: 20260711_01
Revises: 20260623_01
Create Date: 2026-07-11
"""

from alembic import op

revision = "20260711_01"
down_revision = "20260623_01"
branch_labels = None
depends_on = None

# Known-affected as of this migration (informational only — the upgrade scans
# pg_tables directly, so it also catches anything missed here or added later
# without RLS; kept as a fixed list only for audit-log readability).
_KNOWN_DRIFTED_TABLES = (
    "agent_memories",
    "context_packs",
    "model_outcomes",
    "cssa_decisions",
    "cssa_authorizations",
    "cssa_outcomes",
    "cssa_counters",
    "cssa_quota_reservations",
    "cssa_authorization_consumptions",
    "supabase_log_events",
)


def upgrade() -> None:
    # ENABLE (never FORCE): the Postgres owner role this app connects as
    # still bypasses RLS, so this cannot break any DataForge read/write path.
    # It only denies Supabase's PostgREST anon/authenticated Data API, which
    # is not a supported access path for these tables. No policies are
    # added — deny-all matches the existing architecture (see docstring).
    # Idempotent: re-running is a no-op for any table that already has RLS.
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND c.relrowsecurity IS FALSE
          LOOP
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', r.relname);
            RAISE NOTICE 'RLS enabled: public.%', r.relname;
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Deliberately a no-op. Disabling RLS would reopen these tables (and any
    # other public table this pass caught) to Supabase's anon/authenticated
    # Data API — a security-hardening migration must never have an automatic
    # downgrade path that reintroduces public exposure. If a specific table's
    # RLS genuinely needs to be reverted, do it by hand against that one
    # table, deliberately, with the reason recorded — not via `alembic
    # downgrade`.
    pass

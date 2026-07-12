"""enable RLS on the FMEM-02 memory spine tables

fmem02_memory_spine (20260712_01) was authored in parallel with 20260711_01
(the migration that closed the original rls_disabled_in_public drift) against
the same prior head, so it could not have known about that pass. It created
five new public tables -- memory_episodes, memory_claims, memory_facts,
memory_receipts, memory_deletions -- with RLS disabled, reproducing the exact
drift class 20260711_01 exists to close.

Re-running that migration's idempotent scan (rather than hand-listing these
five tables) both fixes this specific case and re-confirms no other table has
drifted since. Same posture as 20260711_01: RLS ON, zero policies, deny-all
for Supabase's PostgREST anon/authenticated Data API. The Postgres owner role
this app connects as bypasses RLS regardless, so this cannot affect any
DataForge read/write path -- see 20260711_01 for the full rationale.

Revision ID: 20260712_03
Revises: 20260712_02
Create Date: 2026-07-12
"""

from alembic import op

revision = "20260712_03"
down_revision = "20260712_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    # Deliberately a no-op -- see 20260711_01's downgrade for the rationale
    # (a security-hardening migration must never have an automatic rollback
    # path that reintroduces public exposure).
    pass

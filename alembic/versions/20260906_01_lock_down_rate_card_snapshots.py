"""lock down RateCardSnapshot.v1 Supabase Data API access

The rate-card store is read by authenticated DataForge services. It is not a
Supabase client-data surface: BDS Website receives only DataForge's reduced
public projection, while Forge Command and DataForge Local use the authenticated
service API. Keep the raw table unavailable to ``anon`` and ``authenticated``.

Revision ID: 20260906_01
Revises: 20260826_01
Create Date: 2026-09-06
"""

from alembic import op


revision = "20260906_01"
down_revision = "20260826_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.rate_card_snapshots ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.rate_card_snapshots FROM anon';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.rate_card_snapshots FROM authenticated';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Deliberately a no-op. Restoring broad Data API grants or disabling RLS
    # would re-expose raw pricing provenance and governance fields. Any change
    # to this authority boundary requires a separately reviewed migration.
    pass

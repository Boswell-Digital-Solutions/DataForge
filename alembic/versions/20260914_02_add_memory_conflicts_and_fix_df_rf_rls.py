"""add memory_conflicts table; enable RLS on it and on the df_rf_* tables

20260914_01 (add_df_rf_tables) created three new public tables --
df_rf_evidence_links, df_rf_finding_candidates, df_rf_dispositions -- without
enabling row-level security, reproducing the exact drift class 20260711_01/
20260712_03 exist to close. Found while wiring memory_conflict verification
into df_rf_ingest.py's _VERIFIABLE_UPSTREAM_FAMILIES for BDS-FMEM-OPCOURT-001,
not flagged by any test (the local suite runs on SQLite, which has no RLS
concept, so this class of gap is invisible to `bash scripts/preflight.sh`).

This migration both fixes that specific gap and creates memory_conflicts (the
new table storing memory_conflict.v1 records for BDS-FMEM-OPCOURT-001) with
RLS enabled from the start, so it never has the gap in the first place. Same
posture as 20260712_03: RLS ON, zero policies, anon/authenticated privileges
explicitly revoked -- deny-all for Supabase's PostgREST Data API. The Postgres
owner role this app connects as bypasses RLS regardless, so this cannot affect
any DataForge read/write path.

Revision ID: 20260914_02
Revises: 20260914_01
Create Date: 2026-09-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260914_02"
down_revision = "20260914_01"
branch_labels = None
depends_on = None

_DF_RF_TABLES_MISSING_RLS = (
    "df_rf_evidence_links",
    "df_rf_finding_candidates",
    "df_rf_dispositions",
)


def _enable_rls_deny_all(table: str) -> None:
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM anon';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM authenticated';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    op.create_table(
        "memory_conflicts",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("conflict_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("repo_id", sa.String(length=128), nullable=True),
        sa.Column("subject_entity_id", sa.String(length=256), nullable=False),
        sa.Column("predicate", sa.String(length=256), nullable=False),
        sa.Column("conflict_type", sa.String(length=32), nullable=False),
        sa.Column("operator_review_required", sa.Boolean(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_conflicts_conflict_id", "memory_conflicts", ["conflict_id"])
    op.create_index("ix_memory_conflicts_tenant_id", "memory_conflicts", ["tenant_id"])
    op.create_index("ix_memory_conflicts_project_id", "memory_conflicts", ["project_id"])
    op.create_index("ix_memory_conflicts_repo_id", "memory_conflicts", ["repo_id"])
    op.create_index("ix_memory_conflicts_subject_entity_id", "memory_conflicts", ["subject_entity_id"])
    op.create_index("ix_memory_conflicts_predicate", "memory_conflicts", ["predicate"])
    op.create_index("ix_memory_conflicts_conflict_type", "memory_conflicts", ["conflict_type"])
    op.create_index(
        "ix_memory_conflicts_operator_review_required", "memory_conflicts", ["operator_review_required"]
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _enable_rls_deny_all("memory_conflicts")
        for table in _DF_RF_TABLES_MISSING_RLS:
            _enable_rls_deny_all(table)


def downgrade() -> None:
    op.drop_index("ix_memory_conflicts_operator_review_required", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_conflict_type", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_predicate", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_subject_entity_id", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_repo_id", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_project_id", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_tenant_id", table_name="memory_conflicts")
    op.drop_index("ix_memory_conflicts_conflict_id", table_name="memory_conflicts")
    op.drop_table("memory_conflicts")
    # Deliberately does not disable RLS on the df_rf_* tables -- a security-
    # hardening fix must never have an automatic rollback path that
    # reintroduces public exposure (same rationale as 20260712_03's downgrade).

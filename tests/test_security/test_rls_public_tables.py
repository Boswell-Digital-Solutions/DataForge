"""
RLS coverage test for public-schema tables (Supabase `rls_disabled_in_public`).

Row-Level Security is a Postgres-only feature -- the default test suite runs
against sqlite (see tests/conftest.py) and cannot exercise it. This is a
real-Postgres integration check: it provisions a throwaway database on a
Postgres server you provide, runs the actual `alembic upgrade head` chain
against it (the same command scripts/render-build.sh runs on every deploy),
then asserts every public table -- especially the ten that drifted after the
2026-06-02 hardening pass -- has `relrowsecurity = true`.

Run it against a local/disposable Postgres, e.g.:

    docker run --rm -d -p 55432:5432 -e POSTGRES_PASSWORD=postgres \\
        --name rls-test-pg ankane/pgvector:latest
    DATAFORGE_RLS_TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:55432/postgres \\
        pytest tests/test_security/test_rls_public_tables.py -v -m integration

Never point DATAFORGE_RLS_TEST_POSTGRES_URL at a production database -- this
test creates and drops a throwaway database on the target server.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_DSN = os.environ.get("DATAFORGE_RLS_TEST_POSTGRES_URL")

pytestmark = [pytest.mark.integration, pytest.mark.security]

# The ten tables migration 20260711_01 exists to fix. Any of these missing
# RLS after `alembic upgrade head` is the exact regression this test guards
# against. Kept in sync by hand with
# alembic/versions/20260711_01_enable_rls_on_drifted_public_tables.py
# (that migration scans pg_tables directly rather than importing this list).
DRIFTED_TABLES = (
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


def _require_admin_dsn() -> str:
    if not ADMIN_DSN:
        pytest.skip(
            "DATAFORGE_RLS_TEST_POSTGRES_URL not set -- RLS is a Postgres-only "
            "feature and cannot be exercised against the default sqlite test "
            "database. Set this env var to a disposable Postgres server to run "
            "this check (see module docstring)."
        )
    return ADMIN_DSN


@pytest.fixture(scope="module")
def migrated_db_url():
    """Create a throwaway database, run the real Alembic chain against it, yield its URL, then drop it."""
    admin_dsn = _require_admin_dsn()
    admin_url = sa.engine.make_url(admin_dsn)
    db_name = f"dataforge_rls_test_{uuid.uuid4().hex[:12]}"

    admin_engine = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()

    test_url = admin_url.set(database=db_name)

    try:
        env = {**os.environ, "DATAFORGE_DATABASE_URL": test_url.render_as_string(hide_password=False)}
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, (
            "alembic upgrade head failed against the throwaway test database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        yield test_url
    finally:
        admin_engine = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
        try:
            with admin_engine.connect() as conn:
                conn.execute(
                    sa.text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :db AND pid <> pg_backend_pid()"
                    ),
                    {"db": db_name},
                )
                conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            admin_engine.dispose()


def _rls_status(engine: sa.Engine) -> dict[str, bool]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT c.relname, c.relrowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = 'r'"
            )
        ).fetchall()
    return {row[0]: row[1] for row in rows}


class TestRLSEnabledOnDriftedTables:
    """Each table created after the 2026-06-02 hardening pass must have RLS enabled."""

    @pytest.fixture(scope="class")
    def rls_status(self, migrated_db_url) -> dict[str, bool]:
        engine = sa.create_engine(migrated_db_url)
        try:
            return _rls_status(engine)
        finally:
            engine.dispose()

    @pytest.mark.parametrize("table_name", DRIFTED_TABLES)
    def test_table_has_rls_enabled(self, rls_status: dict[str, bool], table_name: str):
        assert table_name in rls_status, f"{table_name} was not created by the migration chain"
        assert rls_status[table_name] is True, (
            f"public.{table_name} has RLS disabled -- this is the exact "
            "rls_disabled_in_public regression migration 20260711_01 fixes"
        )

    def test_no_public_table_missing_rls(self, rls_status: dict[str, bool]):
        """Defense in depth: nothing in public should be missing RLS after `alembic upgrade head`."""
        missing = sorted(name for name, enabled in rls_status.items() if not enabled)
        assert missing == [], f"public tables missing RLS: {missing}"

    def test_agent_registry_is_created_with_rls(self, rls_status: dict[str, bool]):
        """The ForgeAgents registry must be provisioned by Alembic, not ORM side effects."""
        assert rls_status.get("agent_registry") is True


class TestOwnerRoleBypassesRLS:
    """The migration must not break the app's own Postgres-owner-role access path."""

    def test_owner_role_can_read_and_write_drifted_table(self, migrated_db_url):
        engine = sa.create_engine(migrated_db_url)
        try:
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "INSERT INTO cssa_counters (counter, high_water) "
                        "VALUES ('rls_test_counter', 1)"
                    )
                )
                row = conn.execute(
                    sa.text("SELECT high_water FROM cssa_counters WHERE counter = 'rls_test_counter'")
                ).fetchone()
            assert row is not None and row[0] == 1
        finally:
            engine.dispose()

#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_python="${DATAFORGE_TEST_PYTHON:-python3}"
migration_url="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" ]]; then
    echo "PGHOST and PGPORT are required; run through pg_virtualenv" >&2
    exit 2
fi

export DATAFORGE_DATABASE_URL="${migration_url}"
export DATAFORGE_SKIP_STARTUP_DB_INIT=1
export DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true
export DATAFORGE_FORGE_CHECK_EVIDENCE_WRITE_ENABLED=true
export DATAFORGE_FORGE_CHECK_EVIDENCE_READ_ENABLED=true

cd "${repo_dir}"
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"${test_python}" -m alembic stamp 20260714_01
"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/forge_check_evidence_v1_migration_proof.sql

"${test_python}" -m alembic downgrade 20260724_02
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF to_regclass('public.forge_check_results_v1') IS NULL
        OR to_regclass('public.forge_check_run_receipts_v1') IS NULL
    THEN
        RAISE EXCEPTION 'CP4 rollback removed evidence tables';
    END IF;
    IF (SELECT count(*) FROM forge_check_results_v1) <> 1
        OR (SELECT count(*) FROM forge_check_run_receipts_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP4 rollback removed evidence rows';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename IN (
              'forge_check_results_v1',
              'forge_check_run_receipts_v1'
          )
    ) THEN
        RAISE EXCEPTION 'CP4 rollback retained runtime RLS policies';
    END IF;
    IF has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_results_v1',
        'SELECT'
    ) OR has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_run_receipts_v1',
        'INSERT'
    ) THEN
        RAISE EXCEPTION 'CP4 rollback retained runtime grants';
    END IF;
END
\$proof\$;
"
echo "CP4_FORGE_CHECK_POSTGRES_ROLLBACK_OK"

"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM forge_check_results_v1) <> 1
        OR (SELECT count(*) FROM forge_check_run_receipts_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP4 re-upgrade did not retain evidence';
    END IF;
    IF NOT has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_results_v1',
        'SELECT,INSERT'
    ) OR NOT has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_check_run_receipts_v1',
        'SELECT,INSERT'
    ) THEN
        RAISE EXCEPTION 'CP4 re-upgrade did not restore grants';
    END IF;
END
\$proof\$;
"
echo "CP4_FORGE_CHECK_POSTGRES_REUPGRADE_OK"

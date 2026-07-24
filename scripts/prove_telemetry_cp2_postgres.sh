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

cd "${repo_dir}"
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"${test_python}" -m alembic stamp 20260714_01
"${test_python}" -m alembic upgrade head
"${test_python}" -m scripts.prove_telemetry_cp2_postgres

"${test_python}" -m alembic downgrade 20260724_01
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'forge_events_v1'
          AND policyname IN (
              'forge_events_v1_telemetry_insert',
              'forge_events_v1_telemetry_select'
          )
    ) THEN
        RAISE EXCEPTION 'CP2 rollback retained a telemetry RLS policy';
    END IF;
    IF has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_events_v1',
        'SELECT'
    ) OR has_table_privilege(
        'dataforge_telemetry_ingest',
        'forge_events_v1',
        'INSERT'
    ) THEN
        RAISE EXCEPTION 'CP2 rollback retained telemetry table grants';
    END IF;
    IF (SELECT count(*) FROM forge_events_v1) < 1 THEN
        RAISE EXCEPTION 'CP2 rollback removed canonical evidence';
    END IF;
END
\$proof\$;
"
echo "CP2_TELEMETRY_POSTGRES_ROLLBACK_OK"

"${test_python}" -m alembic upgrade head
"${test_python}" -m scripts.prove_telemetry_cp2_postgres

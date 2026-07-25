#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_python="${DATAFORGE_TEST_PYTHON:-python3}"
migration_url="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"
restore_database="cp5_restore"
backup_file="$(mktemp /tmp/dataforge-cp5-telemetry-backup.XXXXXX.sql)"

cleanup() {
    rm -f "${backup_file}"
}
trap cleanup EXIT

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" ]]; then
    echo "PGHOST and PGPORT are required; run through pg_virtualenv" >&2
    exit 2
fi

export DATAFORGE_DATABASE_URL="${migration_url}"
export DATAFORGE_SKIP_STARTUP_DB_INIT=1
export DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true
export DATAFORGE_FORGE_CHECK_EVIDENCE_WRITE_ENABLED=true
export DATAFORGE_FORGE_CHECK_EVIDENCE_READ_ENABLED=true
export DATAFORGE_TELEMETRY_RETENTION_SHADOW_READ_ENABLED=true

cd "${repo_dir}"
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"${test_python}" -m alembic stamp 20260714_01
"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/telemetry_cp5_derivation_migration_proof.sql

pg_dump \
    --data-only \
    --inserts \
    --no-owner \
    --no-privileges \
    --table=forge_events_v1 \
    --table=telemetry_derivation_receipts_v1 \
    --table=telemetry_retention_decisions_v1 \
    --table=telemetry_routine_aggregates_v1 \
    --file="${backup_file}" \
    "${PGDATABASE}"

create_restore_database() {
    createdb "${restore_database}"
    psql --no-psqlrc --set=ON_ERROR_STOP=1 \
        --dbname="${restore_database}" \
        --file=tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
    DATAFORGE_DATABASE_URL="postgresql+psycopg2:///${restore_database}?host=${PGHOST}&port=${PGPORT}" \
        "${test_python}" -m alembic stamp 20260714_01
    DATAFORGE_DATABASE_URL="postgresql+psycopg2:///${restore_database}?host=${PGHOST}&port=${PGPORT}" \
        "${test_python}" -m alembic upgrade head
    psql --no-psqlrc --set=ON_ERROR_STOP=1 \
        --dbname="${restore_database}" \
        --file="${backup_file}"
}

create_restore_database
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --dbname="${restore_database}" \
    --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM forge_events_v1) <> 2
        OR (SELECT count(*) FROM telemetry_derivation_receipts_v1) <> 3
        OR (SELECT count(*) FROM telemetry_retention_decisions_v1) <> 2
        OR (SELECT count(*) FROM telemetry_routine_aggregates_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP5 backup restore cardinality mismatch';
    END IF;
    IF (
        SELECT string_agg(event_digest, ',' ORDER BY event_id)
        FROM forge_events_v1
    ) <> repeat('1', 64) || ',' || repeat('2', 64)
    THEN
        RAISE EXCEPTION 'CP5 backup restore source digest mismatch';
    END IF;
END
\$proof\$;
"
echo "CP5_TELEMETRY_BACKUP_RESTORE_OK"

psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --dbname="${restore_database}" \
    --command="
DELETE FROM forge_events_v1 AS source
USING telemetry_retention_decisions_v1 AS decision
WHERE decision.source_kind = 'forge_event'
  AND decision.source_ref = source.event_id::text
  AND decision.clock_basis = 'received_at'
  AND decision.action = 'aggregate_then_delete'
  AND decision.applied IS FALSE
  AND decision.source_overwritten IS FALSE
  AND decision.legal_class <> 'legal_hold'
  AND decision.retention_class <> 'legal_hold'
  AND decision.projected_delete_at <= '2026-08-02T00:00:00Z';

DO \$proof\$
BEGIN
    IF EXISTS (
        SELECT 1 FROM forge_events_v1
        WHERE event_id = '55555555-5555-4555-8555-555555555551'
    ) OR NOT EXISTS (
        SELECT 1 FROM forge_events_v1
        WHERE event_id = '55555555-5555-4555-8555-555555555552'
          AND retention_class = 'legal_hold'
    ) THEN
        RAISE EXCEPTION 'CP5 disposable deletion rehearsal crossed bounds';
    END IF;
END
\$proof\$;
"
echo "CP5_TELEMETRY_DISPOSABLE_DELETION_REHEARSAL_OK"

dropdb "${restore_database}"
create_restore_database
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --dbname="${restore_database}" \
    --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM forge_events_v1) <> 2
        OR NOT EXISTS (
            SELECT 1 FROM forge_events_v1
            WHERE event_id = '55555555-5555-4555-8555-555555555552'
              AND retention_class = 'legal_hold'
        )
    THEN
        RAISE EXCEPTION 'CP5 post-deletion restore failed';
    END IF;
END
\$proof\$;
"
echo "CP5_TELEMETRY_POST_DELETION_RESTORE_OK"

"${test_python}" -m alembic downgrade 20260725_01
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM telemetry_derivation_receipts_v1) <> 3
        OR (SELECT count(*) FROM telemetry_retention_decisions_v1) <> 2
        OR (SELECT count(*) FROM telemetry_routine_aggregates_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP5 rollback removed derivation records';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename IN (
              'telemetry_derivation_receipts_v1',
              'telemetry_retention_decisions_v1',
              'telemetry_routine_aggregates_v1'
          )
    ) THEN
        RAISE EXCEPTION 'CP5 rollback retained runtime RLS policies';
    END IF;
    IF has_table_privilege(
        'dataforge_telemetry_ingest',
        'telemetry_derivation_receipts_v1',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'CP5 rollback retained runtime grants';
    END IF;
END
\$proof\$;
"
echo "CP5_TELEMETRY_POSTGRES_ROLLBACK_OK"

"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM telemetry_derivation_receipts_v1) <> 3
        OR NOT has_table_privilege(
            'dataforge_telemetry_ingest',
            'telemetry_derivation_receipts_v1',
            'SELECT,INSERT'
        )
    THEN
        RAISE EXCEPTION 'CP5 re-upgrade did not retain records and restore grants';
    END IF;
END
\$proof\$;
"
echo "CP5_TELEMETRY_POSTGRES_REUPGRADE_OK"

#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_python="${DATAFORGE_TEST_PYTHON:-python3}"
migration_url="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"
restore_database="cp6_restore"
backup_file="$(mktemp /tmp/dataforge-cp6-telemetry-backup.XXXXXX.sql)"

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
export DATAFORGE_INCIDENT_CANDIDATE_WRITE_ENABLED=true
export DATAFORGE_INCIDENT_CANDIDATE_READ_ENABLED=true

cd "${repo_dir}"
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"${test_python}" -m alembic stamp 20260714_01
"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --file=tests/fixtures/telemetry/telemetry_cp6_incident_candidate_migration_proof.sql

pg_dump \
    --data-only \
    --inserts \
    --no-owner \
    --no-privileges \
    --table=forge_events_v1 \
    --table=telemetry_incident_candidates_v1 \
    --file="${backup_file}" \
    "${PGDATABASE}"

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
psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --dbname="${restore_database}" \
    --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM forge_events_v1) <> 1
        OR (SELECT count(*) FROM telemetry_incident_candidates_v1) <> 1
    THEN
        RAISE EXCEPTION 'CP6 backup restore cardinality mismatch';
    END IF;
    IF (
        SELECT event_digest
        FROM forge_events_v1
        WHERE event_id = '66666666-6666-4666-8666-666666666601'
    ) <> repeat('1', 64)
    THEN
        RAISE EXCEPTION 'CP6 backup restore source digest mismatch';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM telemetry_incident_candidates_v1
        WHERE candidate_id = '66666666-6666-4666-8666-666666666611'
          AND candidate_only
          AND NOT can_repair
          AND NOT can_rollback
          AND NOT can_notify
          AND NOT can_promote
          AND requires_human_decision
          AND NOT source_overwritten
    ) THEN
        RAISE EXCEPTION 'CP6 backup restore authority mismatch';
    END IF;
END
\$proof\$;
"
echo "CP6_TELEMETRY_BACKUP_RESTORE_OK"

"${test_python}" -m alembic downgrade 20260725_02
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM telemetry_incident_candidates_v1) <> 1
        OR (
            SELECT event_digest
            FROM forge_events_v1
            WHERE event_id = '66666666-6666-4666-8666-666666666601'
        ) <> repeat('1', 64)
    THEN
        RAISE EXCEPTION 'CP6 rollback removed candidate or source evidence';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'telemetry_incident_candidates_v1'
    ) THEN
        RAISE EXCEPTION 'CP6 rollback retained runtime RLS policies';
    END IF;
    IF has_table_privilege(
        'dataforge_telemetry_ingest',
        'telemetry_incident_candidates_v1',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'CP6 rollback retained runtime grants';
    END IF;
END
\$proof\$;
"
echo "CP6_TELEMETRY_POSTGRES_ROLLBACK_OK"

"${test_python}" -m alembic upgrade head
psql --no-psqlrc --set=ON_ERROR_STOP=1 --command="
DO \$proof\$
BEGIN
    IF (SELECT count(*) FROM telemetry_incident_candidates_v1) <> 1
        OR NOT has_table_privilege(
            'dataforge_telemetry_ingest',
            'telemetry_incident_candidates_v1',
            'SELECT,INSERT'
        )
    THEN
        RAISE EXCEPTION 'CP6 re-upgrade did not retain evidence and restore grants';
    END IF;
END
\$proof\$;
"
echo "CP6_TELEMETRY_POSTGRES_REUPGRADE_OK"

#!/usr/bin/env bash
# RFC-FT-04 candidate proof (admission proof only; corrective pass 2026-09-29).
# Run inside a throwaway cluster:
#   pg_virtualenv bash scripts/prove_rfc_ft_04_candidate_postgres.sh
# It migrates that cluster to head, creates a throwaway login role in the
# least-privilege dataforge_telemetry_ingest group, and drives the real HTTP
# ingest path. It never reads a configured or production database.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PYTHON="${DATAFORGE_TEST_PYTHON:-python3}"

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" || -z "${PGDATABASE:-}" ]]; then
    echo "PGHOST, PGPORT, and PGDATABASE are required; run through pg_virtualenv" >&2
    exit 2
fi

export DATAFORGE_DATABASE_URL="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"
export DATAFORGE_SKIP_STARTUP_DB_INIT=1
export DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true
export DATAFORGE_TELEMETRY_INGEST_RATE_BURST=200

cd "$REPO_DIR"
psql -v ON_ERROR_STOP=1 \
  -f tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"$TEST_PYTHON" -m alembic stamp 20260714_01
"$TEST_PYTHON" -m alembic upgrade head

ingest_password="$("$TEST_PYTHON" -c 'import secrets; print(secrets.token_hex(24))')"
psql -v ON_ERROR_STOP=1 -v pw="$ingest_password" <<'SQL'
CREATE ROLE rfc_ft_04_proof_ingest LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD :'pw'
    IN ROLE dataforge_telemetry_ingest;
SQL
export DATAFORGE_TELEMETRY_DATABASE_URL="postgresql+psycopg2://rfc_ft_04_proof_ingest:${ingest_password}@/${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"

"$TEST_PYTHON" -m scripts.prove_rfc_ft_04_candidate_postgres

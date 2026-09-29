#!/usr/bin/env bash
# RFC-FT-04 candidate round-trip (admission proof only, authorized 2026-09-29).
# Run inside a throwaway cluster:
#   pg_virtualenv bash scripts/prove_rfc_ft_04_candidate_postgres.sh
# It migrates that cluster to head the same way prove_forge_event_v1_migration.sh
# does, then ingests the synthetic candidate fixtures. It never reads a
# configured or production database.
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

cd "$REPO_DIR"
psql -v ON_ERROR_STOP=1 \
  -f tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"$TEST_PYTHON" -m alembic stamp 20260714_01
"$TEST_PYTHON" -m alembic upgrade head
"$TEST_PYTHON" -m scripts.prove_rfc_ft_04_candidate_postgres

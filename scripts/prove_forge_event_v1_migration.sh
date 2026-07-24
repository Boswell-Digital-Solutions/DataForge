#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PYTHON="${DATAFORGE_TEST_PYTHON:-python3}"
MIGRATION_URL="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"

export DATAFORGE_DATABASE_URL="$MIGRATION_URL"
export DATAFORGE_SKIP_STARTUP_DB_INIT=1
export DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true

cd "$REPO_DIR"
psql -v ON_ERROR_STOP=1 \
  -f tests/fixtures/telemetry/forge_events_v1_migration_setup.sql
"$TEST_PYTHON" -m alembic stamp 20260714_01
"$TEST_PYTHON" -m alembic upgrade head
psql -v ON_ERROR_STOP=1 \
  -f tests/fixtures/telemetry/forge_events_v1_migration_verify.sql
"$TEST_PYTHON" -m scripts.prove_forge_event_v1_postgres_api

if "$TEST_PYTHON" -m alembic downgrade 20260714_01; then
  echo "ForgeEvent.v1 evidence-preserving downgrade unexpectedly succeeded" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 \
  -f tests/fixtures/telemetry/forge_events_v1_migration_rollback_verify.sql

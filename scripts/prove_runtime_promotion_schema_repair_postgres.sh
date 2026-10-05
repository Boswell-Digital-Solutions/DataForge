#!/usr/bin/env bash
# Proof for the runtime-promotion schema repair (revision 20261005_01).
# Run inside a throwaway cluster:
#   pg_virtualenv bash scripts/prove_runtime_promotion_schema_repair_postgres.sh
# It builds the drifted state (head stamped, no runtime-promotion tables), runs the repair,
# and checks the result. It never reads a configured or production database.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PYTHON="${DATAFORGE_TEST_PYTHON:-python3}"

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" || -z "${PGDATABASE:-}" ]]; then
    echo "PGHOST, PGPORT, and PGDATABASE are required; run through pg_virtualenv" >&2
    exit 2
fi

export DATAFORGE_DATABASE_URL="postgresql+psycopg2:///${PGDATABASE}?host=${PGHOST}&port=${PGPORT}"
export DATAFORGE_SKIP_STARTUP_DB_INIT=1
export NEUROFORGE_URL="http://127.0.0.1:1"
cd "$REPO_DIR"

echo "== drifted state: head stamped, tables absent"
"$TEST_PYTHON" -m alembic stamp 20260930_01
"$TEST_PYTHON" -m alembic upgrade head
"$TEST_PYTHON" -m scripts.prove_runtime_promotion_schema_repair_postgres schema_matches_models

echo "== re-run keeps data and changes nothing"
"$TEST_PYTHON" -m scripts.prove_runtime_promotion_schema_repair_postgres seed_row
"$TEST_PYTHON" -m alembic downgrade 20260930_01   # the downgrade is a no-op by design
"$TEST_PYTHON" -m alembic upgrade head
"$TEST_PYTHON" -m scripts.prove_runtime_promotion_schema_repair_postgres row_survives
"$TEST_PYTHON" -m scripts.prove_runtime_promotion_schema_repair_postgres schema_matches_models

echo "== wrong shape is refused and left unchanged"
psql -v ON_ERROR_STOP=1 -c 'ALTER TABLE runtime_promotion_candidates ALTER COLUMN title DROP NOT NULL'
"$TEST_PYTHON" -m alembic downgrade 20260930_01
if "$TEST_PYTHON" -m alembic upgrade head 2> /tmp/rp_repair_shape.err; then
    echo "FAILED: the repair accepted a table with the wrong shape" >&2
    exit 1
fi
grep -q "wrong shape" /tmp/rp_repair_shape.err
psql -v ON_ERROR_STOP=1 -c 'ALTER TABLE runtime_promotion_candidates ALTER COLUMN title SET NOT NULL'

echo "== an unexpected policy is refused"
psql -v ON_ERROR_STOP=1 -c 'CREATE POLICY rp_proof_policy ON runtime_promotion_receipts USING (true)'
"$TEST_PYTHON" -m alembic downgrade 20260930_01
if "$TEST_PYTHON" -m alembic upgrade head 2> /tmp/rp_repair_policy.err; then
    echo "FAILED: the repair accepted a policy on a runtime-promotion table" >&2
    exit 1
fi
grep -q "Unexpected row-level-security policy" /tmp/rp_repair_policy.err
psql -v ON_ERROR_STOP=1 -c 'DROP POLICY rp_proof_policy ON runtime_promotion_receipts'

echo "== partial state is refused and left unchanged"
psql -v ON_ERROR_STOP=1 -c 'DROP TABLE runtime_promotion_execution_statuses'
"$TEST_PYTHON" -m alembic downgrade 20260930_01
if "$TEST_PYTHON" -m alembic upgrade head 2> /tmp/rp_repair_partial.err; then
    echo "FAILED: the repair accepted a partial schema" >&2
    exit 1
fi
grep -q "Partial runtime-promotion schema" /tmp/rp_repair_partial.err
"$TEST_PYTHON" -m scripts.prove_runtime_promotion_schema_repair_postgres partial_is_refused_unchanged
echo "ALL CHECKS PASSED"

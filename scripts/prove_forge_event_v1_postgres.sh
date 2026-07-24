#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
proof_sql="${repo_root}/tests/fixtures/telemetry/forge_events_v1.proof.sql"

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" ]]; then
    echo "PGHOST and PGPORT are required; run through pg_virtualenv" >&2
    exit 2
fi

psql \
    --no-psqlrc \
    --set=ON_ERROR_STOP=1 \
    --file="${proof_sql}" \
    postgres

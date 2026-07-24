#!/usr/bin/env bash
# Render build for the Supabase log poll cron.
#
# The web service is the single migration runner. The cron installs and checks
# code only; its runtime preflight fails with a stable migration category when
# the required table is absent.
set -euo pipefail

cd "$(dirname "$0")/.."

python --version
python -m pip install --upgrade pip

bash scripts/render-git-auth.sh
python -m pip install --no-cache-dir -r requirements.txt

HEADS="$(python -m alembic heads | wc -l)"
if [ "$HEADS" -ne 1 ]; then
  echo "render-cron-build: ERROR — exactly one Alembic head is required." >&2
  exit 1
fi

python -m compileall -q app scripts
echo "render-cron-build: dependencies, migrations graph, and imports verified."

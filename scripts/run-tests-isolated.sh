#!/usr/bin/env bash
# Thin wrapper of the isolated test runner (finding M1). Every run of the suite goes
# through it. It exits 86 when it cannot isolate. See scripts/isolated_test_runner.py.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "${ISOLATED_RUNNER_PYTHON:-}" ]; then
  PYTHON="$ISOLATED_RUNNER_PYTHON"
elif [ -x "$ROOT/.venv/bin/python" ] && "$ROOT/.venv/bin/python" -c 'import pytest' 2>/dev/null; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi
exec "$PYTHON" "$ROOT/scripts/isolated_test_runner.py" "$@"

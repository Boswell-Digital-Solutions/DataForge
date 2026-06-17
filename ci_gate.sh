#!/usr/bin/env bash
# DataForge Cloud CI gate — proving-slice contract participation
#
# Wires this repo into the forge-contract-core gate runner and runs the
# local proving-slice intake test suite. Both must pass.
#
# The contract-core gate validates: schemas, fixture corpus, validator
# correctness, compatibility notes, and forbidden patterns — using the
# shared contract library that DataForge Cloud consumes via
# app/api/proving_slice_router.py.
#
# The local pytest suite validates: intake validation, signature/identity,
# acceptance/rejection, duplicate reconciliation, restricted visibility,
# unsupported-version behaviour, and triple-variant audit receipt persistence.
# The bytecode gate validates app and test syntax while redirecting pycache
# writes away from repo-local caches.
#
# Exit codes:
#   0 — all gates pass
#   1 — one or more gates failed
#
# Usage (from the DataForge Cloud root):
#   bash ci_gate.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate forge-contract-core relative to ecosystem root
# DataForge Cloud is at: Cloud Systems/DataForge/ → ../../contracts/forge-contract-core
ECOSYSTEM_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONTRACT_CORE_PATH="$ECOSYSTEM_ROOT/contracts/forge-contract-core"
REPORT_DIR="$SCRIPT_DIR/reports"

if [[ ! -d "$CONTRACT_CORE_PATH" ]]; then
    echo "ERROR: forge-contract-core not found at $CONTRACT_CORE_PATH"
    exit 1
fi

echo "DataForge Cloud CI gate — proving-slice contract participation"
echo "  contract core path: $CONTRACT_CORE_PATH"
echo ""

# Gate 1 uses the contract-core venv (only needs forge_contract_core)
PYTHON_CONTRACT="$CONTRACT_CORE_PATH/.venv/bin/python"
if [[ ! -x "$PYTHON_CONTRACT" ]]; then
    PYTHON_CONTRACT="python3"
fi

# Gate 2 uses the DataForge Cloud local venv (needs fastapi, etc.)
PYTHON_LOCAL="$SCRIPT_DIR/venv/bin/python"
if [[ ! -x "$PYTHON_LOCAL" ]]; then
    PYTHON_LOCAL="$SCRIPT_DIR/.venv/bin/python"
fi
if [[ ! -x "$PYTHON_LOCAL" ]]; then
    PYTHON_LOCAL="python3"
fi

echo "  python (contract gate): $PYTHON_CONTRACT"
echo "  python (local tests):   $PYTHON_LOCAL"
echo ""

mkdir -p "$REPORT_DIR"

# ── Gate 1: forge-contract-core canonical gate runner ─────────────────────────
echo "=== Gate 1: forge-contract-core canonical gate ==="
GATE_REPORT="$REPORT_DIR/contract_core_gate_$(date +%Y%m%d_%H%M%S).json"
PYTHONPATH="$CONTRACT_CORE_PATH" "$PYTHON_CONTRACT" -m forge_contract_core.gates.run_all \
    --repo "DataForge-cloud" \
    --report-out "$GATE_REPORT"

echo ""

# ── Gate 2: local proving-slice pytest suite ──────────────────────────────────
echo "=== Gate 2: local proving-slice intake tests ==="
LOCAL_REPORT="$REPORT_DIR/local_tests_$(date +%Y%m%d_%H%M%S).xml"
cd "$SCRIPT_DIR"
PYTHONPATH="." "$PYTHON_LOCAL" -m pytest tests/test_proving_slice_intake.py -v \
    --junit-xml="$LOCAL_REPORT" \
    --tb=short

echo ""
# ── Gate 3: app/test bytecode compilation ────────────────────────────────────
echo "=== Gate 3: app/test bytecode compile ==="
BYTECODE_CACHE_ROOT="${PYTHONPYCACHEPREFIX:-}"
if [[ -z "$BYTECODE_CACHE_ROOT" ]]; then
    BYTECODE_CACHE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dataforge-cloud-pycache.XXXXXX")"
    trap 'rm -rf "$BYTECODE_CACHE_ROOT"' EXIT
fi
PYTHONPYCACHEPREFIX="$BYTECODE_CACHE_ROOT" "$PYTHON_LOCAL" -m compileall -q app tests

echo ""
echo "DataForge Cloud CI gate: PASSED"
echo "  contract core gate report: $GATE_REPORT"
echo "  local test report:         $LOCAL_REPORT"
echo "  bytecode cache prefix:     $BYTECODE_CACHE_ROOT"

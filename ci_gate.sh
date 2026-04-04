#!/usr/bin/env bash
# DataForge Cloud CI gate — proving-slice contract participation
#
# Wires this repo into the forge-contract-core gate runner. All changes to
# DataForge Cloud that touch artifact intake, receipt emission, or the
# proving-slice router must pass this gate.
#
# The gate validates: schemas, fixture corpus, validator correctness,
# compatibility notes, and forbidden patterns — using the shared contract
# library that DataForge Cloud consumes via app/api/proving_slice_router.py.
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

if [[ ! -d "$CONTRACT_CORE_PATH" ]]; then
    echo "ERROR: forge-contract-core not found at $CONTRACT_CORE_PATH"
    exit 1
fi

echo "DataForge Cloud CI gate — proving-slice contract participation"
echo "  contract core path: $CONTRACT_CORE_PATH"
echo ""

# Use the contract-core venv if available, otherwise the local venv, otherwise system python
PYTHON="$CONTRACT_CORE_PATH/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
fi
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="python3"
fi

echo "  python: $PYTHON"
echo ""

PYTHONPATH="$CONTRACT_CORE_PATH" "$PYTHON" -m forge_contract_core.gates.run_all

echo ""
echo "DataForge Cloud CI gate: PASSED"

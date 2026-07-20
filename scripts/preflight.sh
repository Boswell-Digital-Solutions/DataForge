#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# DataForge Preflight — Single deterministic gate
# If this passes locally, Render will pass.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
DIM='\033[2m'
RESET='\033[0m'

SECONDS=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

step() {
  echo -e "\n${CYAN}▸ $1${RESET}"
}

fail() {
  echo -e "\n${RED}✖ PRE-FLIGHT FAILED at: $1${RESET}"
  echo -e "${DIM}  Duration: ${SECONDS}s${RESET}"
  exit 1
}

# ─── Venv Detection ───────────────────────────────────────────────
# Activate local venv if present and not already in one.
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  for candidate in .venv venv; do
    if [[ -x "$PROJECT_DIR/$candidate/bin/python" ]]; then
      echo -e "${DIM}Activating $candidate...${RESET}"
      VIRTUAL_ENV="$(cd "$PROJECT_DIR/$candidate" && pwd)"
      export VIRTUAL_ENV
      export PATH="$VIRTUAL_ENV/bin:$PATH"
      unset PYTHONHOME
      break
    fi
  done
fi

echo "═══════════════════════════════════════════"
echo " DATAFORGE PRE-FLIGHT CHECK"
echo "═══════════════════════════════════════════"
echo -e "${DIM}Python:    $(python3 --version)${RESET}"
echo -e "${DIM}pip:       $(python3 -m pip --version | cut -d' ' -f1-2)${RESET}"
echo -e "${DIM}Venv:      ${VIRTUAL_ENV:-system}${RESET}"
echo -e "${DIM}Git SHA:   $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')${RESET}"
echo -e "${DIM}Dirty:     $(git diff --quiet 2>/dev/null && echo 'no' || echo 'YES')${RESET}"
echo -e "${DIM}Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)${RESET}"

# ─── Phase 1: Dependencies ────────────────────────────────────────
# On Render, deps are already installed by buildCommand before preflight runs.
# Locally, refresh dependencies when a virtualenv is active.
if [[ "${RENDER:-}" == "true" ]]; then
  step "Skipping dependency install (Render buildCommand already installed requirements)"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
  step "Installing dependencies..."
  python3 -m pip install --quiet -r requirements.txt || fail "pip install"
else
  step "Skipping pip install (no venv active, not on Render)"
  echo "  Assuming dependencies are pre-installed."
fi

# ─── Phase 2: Alembic Migration Check ─────────────────────────────
step "Checking Alembic heads (single head required)..."
if python3 -m alembic --version &>/dev/null; then
  HEADS=$(python3 -m alembic heads 2>/dev/null | wc -l)
  if [ "$HEADS" -gt 1 ]; then
    python3 -m alembic heads
    fail "alembic: multiple heads detected ($HEADS). Merge before deploying."
  fi
  echo "  Single head confirmed."
else
  echo "  alembic not found — skipping (install deps first)."
fi

# ─── Phase 3: Production-boundary Tests ──────────────────────────
step "Running poller and AuthorForge boundary tests..."
python3 -m pytest \
  tests/test_unit/test_supabase_log_ingest.py \
  tests/test_unit/test_supabase_log_poller.py \
  tests/test_unit/test_authorforge_analytics.py \
  tests/test_unit/test_authorforge_boundary_audit.py \
  -x --tb=short -q \
  || fail "production-boundary pytest"

# ─── Phase 4: Existing Tests ─────────────────────────────────────
# Exclude tests requiring live infrastructure (PostgreSQL, Redis, pgvector).
# The db_session fixture is undefined without a running database, causing 194+ errors.
step "Running pytest (unit tests)..."
python3 -m pytest tests/ -x --tb=short -q \
  --ignore=tests/test_integration \
  --ignore=tests/test_api \
  --ignore=tests/test_unit \
  --ignore=tests/test_sql_integration.py \
  --ignore=tests/test_performance_optimization.py \
  --ignore=tests/test_security \
  --ignore=tests/load \
  || fail "pytest"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${RESET}"
echo -e "${GREEN} ✅ DATAFORGE PRE-FLIGHT PASSED  (${SECONDS}s)${RESET}"
echo -e "${GREEN}═══════════════════════════════════════════${RESET}"

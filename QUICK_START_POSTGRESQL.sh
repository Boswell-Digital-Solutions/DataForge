#!/bin/bash
set -euo pipefail

# Auto-activate local venv if present
if [ -f "$(dirname "$0")/.venv/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$(dirname "$0")/.venv/bin/activate"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "RAG Pipeline Deployment - Quick Start"
echo "=========================================="
echo ""

LOCAL_MODE="${LOCAL_MODE:-0}"
WRITE_ENV="${WRITE_ENV:-0}"

# --- Mode gate ---
if [[ "$LOCAL_MODE" == "1" ]]; then
  echo "LOCAL_MODE=1: legacy/dev local workflow (backward compatibility)"
else
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo -e "${RED}❌ DATABASE_URL is required when LOCAL_MODE != 1${NC}"
    exit 1
  fi

  # Optional: enforce sslmode for Supabase-style Postgres URLs
  if [[ "$DATABASE_URL" == postgresql* ]] && [[ "$DATABASE_URL" != *"sslmode="* ]]; then
    echo -e "${YELLOW}⚠${NC} DATABASE_URL has no sslmode=...; appending sslmode=require"
    export DATABASE_URL="${DATABASE_URL}?sslmode=require"
  fi

  echo -e "${GREEN}✓${NC} Supabase-first mode detected; using DATABASE_URL for all operations"
fi

# --- Dependency checks ---
if ! command -v psql &>/dev/null; then
  echo -e "${RED}❌ PostgreSQL client (psql) not found. Install:${NC}"
  echo "   sudo apt install postgresql-client"
  exit 1
fi
echo -e "${GREEN}✓${NC} psql is installed"

# Local server management only in LOCAL_MODE
if [[ "$LOCAL_MODE" == "1" ]]; then
  if ! command -v pg_isready &>/dev/null; then
    echo -e "${RED}❌ pg_isready not found. Install:${NC}"
    echo "   sudo apt install postgresql-client"
    exit 1
  fi

  echo ""
  echo "Step 1: Starting PostgreSQL service..."
  sudo service postgresql start
  echo -e "${GREEN}✓${NC} PostgreSQL started successfully"

  echo ""
  echo "Step 2: Checking PostgreSQL connection..."
  pg_isready -h localhost -p 5432
  echo -e "${GREEN}✓${NC} PostgreSQL is accepting connections"
else
  echo ""
  echo "Step 1-2: Skipping local PostgreSQL service checks (Supabase mode)"
fi

# Local DB bootstrap only in LOCAL_MODE
if [[ "$LOCAL_MODE" == "1" ]]; then
  echo ""
  echo "Step 3: Creating local database/user (if missing)..."

  DB_NAME="${DB_NAME:-dataforge}"
  DB_USER="${DB_USER:-dataforge_user}"
  DB_PASS="${DB_PASS:-}"

  if [[ -z "$DB_PASS" ]]; then
    echo -e "${RED}❌ DB_PASS is required in LOCAL_MODE=1 (do not hardcode passwords in scripts).${NC}"
    echo "   Example: DB_PASS='dev_password_here' LOCAL_MODE=1 ./quick_start.sh"
    exit 1
  fi

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
CREATE DATABASE ${DB_NAME};
EOF

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';
EOF

  sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF

  echo -e "${GREEN}✓${NC} Local database '${DB_NAME}' ready"

  echo ""
  echo "Step 4: Installing pgvector extension (local)..."
  sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    && echo -e "${GREEN}✓${NC} pgvector extension installed" \
    || echo -e "${YELLOW}⚠${NC} pgvector install failed (keyword search still works)"

  if [[ "$WRITE_ENV" == "1" ]]; then
    echo ""
    echo "Step 5: Updating DataForge .env configuration (WRITE_ENV=1)..."

    ENV_FILE="${ENV_FILE:-/home/charles/projects/Coding2025/Forge/DataForge/.env}"
    if [[ ! -f "$ENV_FILE" ]]; then
      echo -e "${RED}❌ .env file not found at $ENV_FILE${NC}"
      exit 1
    fi

    cp "$ENV_FILE" "$ENV_FILE.backup"

    # Replace any DATABASE_URL=... line (safer than matching one exact sqlite string)
    NEW_URL="postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
    if grep -qE '^DATABASE_URL=' "$ENV_FILE"; then
      sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${NEW_URL}|" "$ENV_FILE"
    else
      echo "DATABASE_URL=${NEW_URL}" >> "$ENV_FILE"
    fi

    echo -e "${GREEN}✓${NC} .env updated (backup saved as .env.backup)"
  else
    echo ""
    echo "Step 5: Skipping .env mutation (set WRITE_ENV=1 to enable)"
  fi
else
  echo ""
  echo "Step 3-5: Skipping local DB bootstrap and .env mutation (Supabase mode)"
fi

# --- Migrations (always) ---
echo ""
echo "Step 6: Running database migration..."
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
alembic upgrade head
echo -e "${GREEN}✓${NC} Migration completed successfully"

echo ""
echo "Step 7: Verifying migration is at head..."
CURRENT="$(alembic current 2>/dev/null | awk '{print $1}' | head -1 || true)"
HEAD="$(alembic heads 2>/dev/null | awk '{print $1}' | head -1 || true)"

if [[ -n "$CURRENT" && -n "$HEAD" && "$CURRENT" == "$HEAD" ]]; then
  echo -e "${GREEN}✓${NC} Alembic at head: $CURRENT"
else
  echo -e "${YELLOW}⚠${NC} Alembic not at head (current: ${CURRENT:-unknown}, head: ${HEAD:-unknown})"
fi

# --- psql target selection ---
if [[ "$LOCAL_MODE" == "1" ]]; then
  : "${DB_NAME:=dataforge}"
  : "${DB_USER:=dataforge_user}"
  PSQL_CMD=(psql -d "$DB_NAME" -U "$DB_USER" -h localhost)
else
  PSQL_CMD=(psql "$DATABASE_URL")
fi

echo ""
echo "Step 8: Verifying search_vector column..."
COLUMN_EXISTS="$("${PSQL_CMD[@]}" -t -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='chunks' AND column_name='search_vector';" \
  2>/dev/null | tr -d '[:space:]')"

if [[ "$COLUMN_EXISTS" == "search_vector" ]]; then
  echo -e "${GREEN}✓${NC} search_vector column exists"
else
  echo -e "${RED}❌ search_vector column not found${NC}"
  exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ RAG Pipeline Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1) Start DataForge:"
echo "   cd /home/charlie/Forge/ecosystem/DataForge"
echo "   uvicorn app.main:app --reload --port 8001"
echo ""
echo "2) Verify DB via psql: \\dt, \\dx, etc."
echo "3) Run validation:"
echo "   cd /home/charlie/Forge/ecosystem"
echo "   python3 test_rag_refactoring.py"

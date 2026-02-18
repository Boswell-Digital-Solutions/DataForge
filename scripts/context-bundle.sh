#!/usr/bin/env bash
# BDS Documentation Protocol v1.0 — context-bundle.sh
# Generates a focused context bundle for AI sessions.
#
# Usage:
#   ./scripts/context-bundle.sh              # Full bundle (all parts)
#   ./scripts/context-bundle.sh search       # Vector search + hybrid search focus
#   ./scripts/context-bundle.sh bugcheck     # BugCheck integration + access control
#   ./scripts/context-bundle.sh auth         # Auth + security + anomaly detection
#   ./scripts/context-bundle.sh schema       # ORM models + Pydantic schemas
#   ./scripts/context-bundle.sh api          # All 29 routers reference
#   ./scripts/context-bundle.sh migrations   # Alembic migration workflow

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
DOC_DIR="$ROOT/doc/system"
OUT="$ROOT/context-bundle.md"
PRESET="${1:-full}"

echo "🔧 DataForge context-bundle.sh — preset: $PRESET"

write_header() {
  echo "# DataForge — Context Bundle ($PRESET)" > "$OUT"
  echo "_Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ) | Preset: ${PRESET}_" >> "$OUT"
  echo "" >> "$OUT"
  # Always include the critical rules
  echo "## Critical Rules (always in scope)" >> "$OUT"
  echo "" >> "$OUT"
  echo "1. DataForge owns all durable state — no other service persists truth" >> "$OUT"
  echo "2. BugCheck writes findings only (requires run_token, never lifecycle transitions)" >> "$OUT"
  echo "3. Audit log is append-only with HMAC-SHA256 — never modify" >> "$OUT"
  echo "4. After FINALIZED, reject new findings with 409" >> "$OUT"
  echo "" >> "$OUT"
}

append_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    echo "" >> "$OUT"
    echo "---" >> "$OUT"
    echo "" >> "$OUT"
    cat "$file" >> "$OUT"
  else
    echo "⚠️  Warning: $file not found, skipping"
  fi
}

append_source() {
  local file="$1"
  local label="${2:-$file}"
  if [[ -f "$ROOT/$file" ]]; then
    echo "" >> "$OUT"
    echo "---" >> "$OUT"
    echo "<!-- source: $label -->" >> "$OUT"
    echo '```python' >> "$OUT"
    cat "$ROOT/$file" >> "$OUT"
    echo '```' >> "$OUT"
  fi
}

write_header

case "$PRESET" in
  full)
    for f in "$DOC_DIR"/0*.md; do
      append_file "$f"
    done
    ;;

  search)
    # Vector search + hybrid search focus
    append_file "$DOC_DIR/02-architecture.md"
    append_file "$DOC_DIR/07-backend-internals.md"
    append_source "app/api/search.py" "api/search.py"
    append_source "app/api/search_router.py" "api/search_router.py"
    append_source "app/utils/embeddings.py" "utils/embeddings.py"
    ;;

  bugcheck)
    # BugCheck integration + access control matrix
    append_file "$DOC_DIR/08-ecosystem-integration.md"
    append_file "$DOC_DIR/09-error-handling.md"
    append_file "$DOC_DIR/06-api-layer.md"
    ;;

  auth)
    # Auth + security + anomaly detection
    append_file "$DOC_DIR/09-error-handling.md"
    append_source "app/api/auth_router.py" "api/auth_router.py"
    append_source "app/utils/auth.py" "utils/auth.py"
    ;;

  schema)
    # ORM models + Pydantic schemas
    append_file "$DOC_DIR/04-project-structure.md"
    append_source "app/models/models.py" "models/models.py"
    append_source "app/models/schemas.py" "models/schemas.py"
    ;;

  api)
    # All API routers reference
    append_file "$DOC_DIR/06-api-layer.md"
    append_source "app/main.py" "main.py"
    ;;

  migrations)
    # Alembic migration workflow
    append_file "$DOC_DIR/11-handover.md"
    append_source "alembic/env.py" "alembic/env.py"
    ;;

  config)
    append_file "$DOC_DIR/05-config-env.md"
    ;;

  testing)
    append_file "$DOC_DIR/10-testing.md"
    ;;

  *)
    echo "❌ Unknown preset: $PRESET"
    echo "Available presets: full, search, bugcheck, auth, schema, api, migrations, config, testing"
    exit 1
    ;;
esac

LINE_COUNT=$(wc -l < "$OUT")
echo ""
echo "✅ Context bundle written: $OUT"
echo "   $LINE_COUNT lines | preset: $PRESET"
echo ""
echo "📋 To use with Claude: copy $OUT content into your session."

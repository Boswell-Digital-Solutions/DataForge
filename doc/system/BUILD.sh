#!/usr/bin/env bash
# BDS Documentation Protocol v1.0 — BUILD.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/../../context-bundle.md"

echo "# DataForge — Context Bundle" > "$OUT"
echo "_Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)_" >> "$OUT"
echo "" >> "$OUT"

for f in "$SCRIPT_DIR"/0*.md; do
  echo "" >> "$OUT"
  echo "---" >> "$OUT"
  echo "" >> "$OUT"
  cat "$f" >> "$OUT"
done

echo ""
echo "Context bundle written to: $OUT"
echo "   $(wc -l < "$OUT") lines"

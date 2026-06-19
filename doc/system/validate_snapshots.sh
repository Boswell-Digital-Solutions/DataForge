#!/usr/bin/env bash
set -euo pipefail

PARTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PARTS_DIR/../.." && pwd)"
ASSEMBLED_OUTPUT="${1:-$ROOT_DIR/doc/DTFSYSTEM.md}"

require_contains() {
  local file="$1" needle="$2" label="$3"
  if ! grep -Fq -- "$needle" "$file"; then
    echo "snapshot validation failed: $label missing in $file" >&2
    echo "expected: $needle" >&2
    exit 1
  fi
}

require_absent() {
  local file="$1" needle="$2" label="$3"
  if grep -Fq -- "$needle" "$file"; then
    echo "snapshot validation failed: $label still present in $file" >&2
    echo "unexpected: $needle" >&2
    exit 1
  fi
}

# canonical identity: _index.md must declare the designation-bound output
require_contains "$PARTS_DIR/_index.md" "**Designation:** DTF" "index designation"
require_contains "$PARTS_DIR/_index.md" "Primary output: \`doc/DTFSYSTEM.md\`" "index primary output"
require_absent  "$PARTS_DIR/_index.md" "Primary output: \`doc/SYSTEM.md\`" "index legacy primary output"

# assembled artifact must carry doctrine and not still declare legacy output
test -f "$ASSEMBLED_OUTPUT"
require_contains "$ASSEMBLED_OUTPUT" "Document version" "assembled document version header"
require_contains "$ASSEMBLED_OUTPUT" "**Designation:** DTF" "assembled designation"
require_contains "$ASSEMBLED_OUTPUT" "Primary output: \`doc/DTFSYSTEM.md\`" "assembled primary output"
require_absent  "$ASSEMBLED_OUTPUT" "Primary output: \`doc/SYSTEM.md\`" "assembled legacy primary output"

echo "snapshot validation passed: $ASSEMBLED_OUTPUT"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT="${DOC_DIR}/ftSYSTEM.md"

{
  cat "${SCRIPT_DIR}/_index.md"
  while IFS= read -r part; do
    printf '\n---\n\n'
    cat "${SCRIPT_DIR}/${part}"
  done < <(find "${SCRIPT_DIR}" -maxdepth 1 -type f -name '[0-9][0-9]-*.md' -printf '%f\n' | sort)
} > "${OUTPUT}"

echo "ftSYSTEM.md rebuilt ($(wc -l < "${OUTPUT}") lines)"

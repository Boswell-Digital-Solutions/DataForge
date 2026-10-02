#!/usr/bin/env bash
# Decide whether a change is code or documentation only (standing rule, 2026-10-01).
#
# Reads changed file paths on stdin, one per line. Prints `code=true` or `code=false`.
# A documentation-only change prints `code=false`. Anything else prints `code=true`,
# including an empty list: when the scope is unknown, the code scans run.
#
# Documentation is `docs/**`, `doc/**` and any `*.md`. A documentation path that a test reads is
# code. List each such path in REINCLUDE below. Keep the list equal to the `paths` re-includes in
# `test.yml` and `docker.yml`.
set -euo pipefail

# - docs/plans/DFG_GOV_01/: tests/test_dfg_gov_01.py loads the JSON fixtures in this directory.
# - docs/archive/TELEMETRY_INTEGRATION_STATUS.md: tests/test_dataforge_telemetry_caller.py
#   asserts that this file does not exist.
REINCLUDE='^(docs/plans/DFG_GOV_01/|docs/archive/TELEMETRY_INTEGRATION_STATUS\.md$)'
DOCUMENTATION='^(docs/|doc/)|\.md$'

seen=0
while IFS= read -r path; do
  [ -z "$path" ] && continue
  seen=1
  if [[ "$path" =~ $REINCLUDE ]] || ! [[ "$path" =~ $DOCUMENTATION ]]; then
    echo "code=true"
    exit 0
  fi
done

if [ "$seen" -eq 0 ]; then
  echo "code=true"
else
  echo "code=false"
fi

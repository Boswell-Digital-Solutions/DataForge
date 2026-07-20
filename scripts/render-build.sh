#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Full Render build for the DataForge web service.
#
# Exists so the Render dashboard "Build Command" can be a single,
# unmanglable token:
#
#     bash scripts/render-build.sh
#
# Render flattens newlines in the dashboard Build Command field, which
# breaks any multi-line shell (if/then/fi). Keeping the real build here
# — where formatting is preserved by git — sidesteps that entirely.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# Run from the repo root regardless of where the script is invoked.
cd "$(dirname "$0")/.."

python --version
python -m pip install --upgrade pip

# Provision token auth for the private forge-* git dependencies. On Render,
# FORGE_TELEMETRY_TOKEN is required and must have read access to both repos.
bash scripts/render-git-auth.sh

python -m pip install --no-cache-dir -r requirements.txt

chmod +x scripts/preflight.sh
bash scripts/preflight.sh

python -m alembic upgrade head

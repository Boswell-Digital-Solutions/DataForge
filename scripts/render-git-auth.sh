#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Render build-time git auth for the private forge-* dependencies (token).
#
# Render's build container has no git credentials, so an unauthenticated
# clone of the private forge-telemetry / forge_contract_core repos fails with
# "could not read Username" and aborts `pip install -r requirements.txt`.
#
# This configures a git `insteadOf` rewrite that injects a GitHub token with
# read access to the private Boswell-Digital-Solutions repos, so every
# github.com HTTPS clone (the git+https pins in requirements.txt) authenticates.
# The rewrite stays active for the whole build so BOTH private deps are covered.
# The token is written to git config (ephemeral build container) — never
# embedded in a pin URL and never echoed into the build logs.
#
# Token env, in priority order:
#   FORGE_TELEMETRY_TOKEN   (preferred)
#   GITHUB_TOKEN            (fallback)
# Use a fine-grained PAT with Contents:Read on forge-telemetry +
# forge_contract_core (or a classic PAT with `repo` scope).
#
# No-op when neither is set (local builds / other environments where the deps
# are already reachable via the developer's own credentials).
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

TOKEN="${FORGE_TELEMETRY_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "${TOKEN}" ]; then
  # On Render (RENDER=true) a missing token is fatal — without it pip's clone of
  # the private repos fails later with a cryptic "could not read Username". Fail
  # here with an actionable message instead. Locally it's a no-op (the developer's
  # own git credentials reach the repos).
  if [ -n "${RENDER:-}" ]; then
    echo "render-git-auth: ERROR — FORGE_TELEMETRY_TOKEN / GITHUB_TOKEN is not set on this Render service." >&2
    echo "  The private forge-* dependencies cannot be cloned without it. Add a GitHub token" >&2
    echo "  with Contents:Read on forge-telemetry + forge_contract_core as FORGE_TELEMETRY_TOKEN." >&2
    exit 1
  fi
  echo "render-git-auth: no FORGE_TELEMETRY_TOKEN / GITHUB_TOKEN set — skipping (local build; deps assumed reachable)."
  exit 0
fi

git config --global "url.https://x-access-token:${TOKEN}@github.com/.insteadOf" "https://github.com/"
echo "render-git-auth: token auth configured for github.com (private forge-* deps)."

#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Render build-time git auth for the private forge-* dependencies.
#
# Render's build container has no git credentials, so an unauthenticated
# clone of forge-telemetry / forge_contract_core fails with
# "could not read Username" and aborts `pip install -r requirements.txt`.
#
# This provisions the deploy key from the forge-telemetry-ssh env group
# (exposed as $SSH_KEY) and routes github.com clones over SSH. Auth is
# written to ~/.ssh/config + ~/.gitconfig (files), so it persists to the
# pip subprocess without relying on exported env vars.
#
# No-op when $SSH_KEY is unset (local builds / other environments).
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

if [ -z "${SSH_KEY:-}" ]; then
  echo "render-git-auth: SSH_KEY not set — skipping (assuming deps are reachable)."
  exit 0
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

printf '%s\n' "$SSH_KEY" > "$HOME/.ssh/forge_deploy_key"
chmod 600 "$HOME/.ssh/forge_deploy_key"

ssh-keyscan github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null || true

cat > "$HOME/.ssh/config" <<SSHCFG
Host github.com
  HostName github.com
  User git
  IdentityFile $HOME/.ssh/forge_deploy_key
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
SSHCFG
chmod 600 "$HOME/.ssh/config"

# Rewrite github.com HTTPS clones (as pinned in requirements.txt) to SSH so
# they authenticate with the deploy key above.
git config --global url."git@github.com:".insteadOf "https://github.com/"

echo "render-git-auth: SSH auth configured for github.com."

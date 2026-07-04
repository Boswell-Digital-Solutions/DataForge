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

key_file="$HOME/.ssh/forge_deploy_key"
# Write the key, tolerating common env-var mangling. A valid PEM/OpenSSH key
# needs REAL newlines; env storage sometimes flattens them (single line, or
# literal backslash-n) or adds CRLF. Normalise both cases; strip CR either way.
if [[ "$SSH_KEY" == *$'\n'* ]]; then
  printf '%s\n' "$SSH_KEY" | tr -d '\r' > "$key_file"     # already multi-line
else
  printf '%b\n' "$SSH_KEY" | tr -d '\r' > "$key_file"     # expand literal \n
fi
chmod 600 "$key_file"

# Fail fast with an actionable message instead of a cryptic "error in libcrypto"
# during the clone. Only validate when ssh-keygen is available, so a missing
# tool can never reject a good key. Never prints key material.
if command -v ssh-keygen >/dev/null 2>&1; then
  if ! ssh-keygen -y -f "$key_file" </dev/null >/dev/null 2>&1; then
    echo "render-git-auth: ERROR — SSH_KEY did not parse as a valid private key." >&2
    echo "  In the forge-telemetry-ssh env group, SSH_KEY must be the COMPLETE key:" >&2
    echo "  a '-----BEGIN ... PRIVATE KEY-----' line, the base64 body, and a" >&2
    echo "  '-----END ... PRIVATE KEY-----' line — each on its own line (real" >&2
    echo "  newlines), no surrounding quotes, unencrypted (no passphrase)." >&2
    exit 1
  fi
fi

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

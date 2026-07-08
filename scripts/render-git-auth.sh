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
# Write the key, tolerating the ways env storage mangles a PEM/OpenSSH key.
# A valid key needs REAL newlines around a base64 body, but the value that
# reaches us may be any of:
#   • already multi-line (correct)                — pass through
#   • one line with literal "\n" between segments — expand the escape
#   • one line with SPACES between segments       — Render/paste flattening
#   • wrapped in surrounding single/double quotes — strip them
#   • CRLF line endings                           — drop the CR
# The robust normaliser below reconstructs the header/body/footer regardless
# of which mangling happened: it isolates the "-----BEGIN X-----" header and
# matching footer, strips ALL whitespace from the base64 body, then re-wraps
# it at 64 columns. Python is guaranteed present in this build (render-build.sh
# runs `python --version` just before invoking us); fall back to the simpler
# literal-\n / passthrough handling if it is somehow unavailable.
if command -v python >/dev/null 2>&1; then
  SSH_KEY="$SSH_KEY" python - "$key_file" <<'PYNORM'
import os, re, sys, textwrap

raw = os.environ.get("SSH_KEY", "")
out_path = sys.argv[1]

# Strip surrounding whitespace and a single layer of matching quotes.
raw = raw.strip()
if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
    raw = raw[1:-1]

# Expand literal backslash escapes and normalise line endings.
raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
raw = raw.replace("\r\n", "\n").replace("\r", "\n")

# Reconstruct "-----BEGIN <LABEL>-----\n<body>\n-----END <LABEL>-----".
m = re.search(r"-----BEGIN ([A-Z0-9 ]+?)-----(.*?)-----END \1-----", raw, re.S)
if m:
    label, body = m.group(1), m.group(2)
    body = re.sub(r"\s+", "", body)  # collapse spaces/newlines the env introduced
    wrapped = "\n".join(textwrap.wrap(body, 64)) if body else ""
    text = "-----BEGIN %s-----\n%s\n-----END %s-----\n" % (label, wrapped, label)
else:
    # No recognisable envelope; write what we have and let validation report it.
    text = raw if raw.endswith("\n") else raw + "\n"

with open(out_path, "w") as fh:
    fh.write(text)
PYNORM
elif [[ "$SSH_KEY" == *$'\n'* ]]; then
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

#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Render build-time git auth for the private forge-* dependencies.
#
# Render's build container has no git credentials, so an unauthenticated
# clone of forge-telemetry / forge_contract_core fails with
# "could not read Username" and aborts `pip install -r requirements.txt`.
#
# This provisions the deploy key from the forge-telemetry-ssh env group
# and routes github.com clones over SSH. Auth is written to
# ~/.ssh/config + ~/.gitconfig (files), so it persists to the pip
# subprocess without relying on exported env vars.
#
# ── Key transport ──────────────────────────────────────────────────
# TWO env vars are accepted, in priority order:
#
#   SSH_KEY_B64  (RECOMMENDED — mangle-proof)
#       The base64 encoding of the ENTIRE key file:
#           base64 -w0 < deploy_key        # Linux
#           base64    < deploy_key | tr -d '\n'   # macOS
#       This is a single flat token with no newlines, quotes, or PEM
#       markers, so Render's env storage physically cannot corrupt it.
#       Decoded verbatim — the safest option and why the previous
#       raw-PEM approaches kept failing.
#
#   SSH_KEY      (legacy — raw PEM, best-effort normalised)
#       The raw "-----BEGIN ... PRIVATE KEY-----" block. Render tends
#       to flatten newlines into spaces, wrap the value in quotes, or
#       swap in literal "\n" — all of which corrupt a PEM. We reconstruct
#       it as best we can, and also auto-detect a base64 blob pasted here.
#
# No-op when neither is set (local builds / other environments).
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

if [ -z "${SSH_KEY_B64:-}" ] && [ -z "${SSH_KEY:-}" ]; then
  echo "render-git-auth: neither SSH_KEY_B64 nor SSH_KEY set — skipping (assuming deps are reachable)."
  exit 0
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

key_file="$HOME/.ssh/forge_deploy_key"

if [ -n "${SSH_KEY_B64:-}" ]; then
  # ── Preferred path: opaque base64 blob → decode verbatim. ──────────
  # Strip any incidental whitespace/quotes the env layer may have added
  # (base64 itself contains none), then decode straight to the key file.
  echo "render-git-auth: using SSH_KEY_B64 (base64 transport)."
  if command -v python >/dev/null 2>&1; then
    SSH_KEY_B64="$SSH_KEY_B64" python - "$key_file" <<'PYB64'
import base64, os, re, sys

raw = os.environ.get("SSH_KEY_B64", "").strip()
if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
    raw = raw[1:-1]
raw = re.sub(r"\s+", "", raw)  # base64 has no interior whitespace

data = base64.b64decode(raw)  # raises on truly invalid input → fail fast
text = data.decode("utf-8", "replace")
if not text.endswith("\n"):
    text += "\n"
with open(sys.argv[1], "w") as fh:
    fh.write(text)
PYB64
  else
    printf '%s' "$SSH_KEY_B64" | tr -d '[:space:]"'"'"'' | base64 -d > "$key_file"
  fi
else
  # ── Legacy path: raw PEM in $SSH_KEY, tolerating env mangling. ─────
  # A valid key needs REAL newlines around a base64 body, but the value
  # that reaches us may be any of:
  #   • already multi-line (correct)                — pass through
  #   • one line with literal "\n" between segments — expand the escape
  #   • one line with SPACES between segments       — Render/paste flattening
  #   • wrapped in surrounding single/double quotes — strip them
  #   • CRLF line endings                           — drop the CR
  #   • a base64 blob of the whole key (no envelope) — decode it
  # The robust normaliser below reconstructs the header/body/footer
  # regardless of which mangling happened. Python is guaranteed present
  # (render-build.sh runs `python --version` just before invoking us);
  # fall back to simpler literal-\n / passthrough handling otherwise.
  echo "render-git-auth: using SSH_KEY (raw-PEM transport; SSH_KEY_B64 is more robust)."
  if command -v python >/dev/null 2>&1; then
    SSH_KEY="$SSH_KEY" python - "$key_file" <<'PYNORM'
import base64, os, re, sys, textwrap

raw = os.environ.get("SSH_KEY", "")
out_path = sys.argv[1]

# Strip surrounding whitespace and a single layer of matching quotes.
raw = raw.strip()
if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
    raw = raw[1:-1]

# If there is no PEM envelope, the value may be a base64 blob of the whole
# key file. Try to decode it; use the result only if it looks like a PEM.
if "-----BEGIN" not in raw:
    candidate = re.sub(r"\s+", "", raw)
    try:
        decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
        if "-----BEGIN" in decoded:
            raw = decoded
    except Exception:
        pass

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
fi
chmod 600 "$key_file"

# Fail fast with an actionable message instead of a cryptic "error in libcrypto"
# during the clone. Only validate when ssh-keygen is available, so a missing
# tool can never reject a good key. Never prints key material.
if command -v ssh-keygen >/dev/null 2>&1; then
  if ! ssh-keygen -y -f "$key_file" </dev/null >/dev/null 2>&1; then
    echo "render-git-auth: ERROR — deploy key did not parse as a valid private key." >&2
    echo "  Fix (recommended): in the forge-telemetry-ssh env group, set SSH_KEY_B64" >&2
    echo "  to the base64 of the WHOLE key file — a single flat token Render cannot" >&2
    echo "  mangle:" >&2
    echo "      base64 -w0 < deploy_key      # Linux" >&2
    echo "      base64    < deploy_key | tr -d '\\n'   # macOS" >&2
    echo "  The key must be UNENCRYPTED (no passphrase). If you instead use SSH_KEY," >&2
    echo "  paste the COMPLETE PEM: a '-----BEGIN ... PRIVATE KEY-----' line, the" >&2
    echo "  base64 body, and a '-----END ... PRIVATE KEY-----' line, no quotes." >&2
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

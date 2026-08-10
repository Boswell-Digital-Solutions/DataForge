#!/usr/bin/env bash
# Configure build-only Git authentication for DataForge's private dependencies.
#
# Preferred credential source:
#   FORGE_PRIVATE_DEPS_APP_CLIENT_ID
#   FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY
#
# The pair identifies the BDS Fleet Operator GitHub App. A short-lived,
# repository-scoped installation token is minted for every Render build.
# FORGE_TELEMETRY_TOKEN remains a legacy fallback during migration only; it is
# unrelated to DataForge's runtime telemetry credentials.
set -euo pipefail

readonly GITHUB_ORG="Boswell-Digital-Solutions"
readonly API_VERSION="2026-03-10"
readonly -a PRIVATE_REPOS=("forge-telemetry" "forge_contract_core")

fail() {
  echo "render-git-auth: ERROR - $1" >&2
  exit 1
}

b64url() {
  openssl base64 -A | tr '+/' '-_' | tr -d '='
}

api_request() {
  local method="$1"
  local url="$2"
  local authorization="$3"
  local output_file="$4"
  local body="${5:-}"
  local args=(
    --silent --show-error --fail
    --request "$method"
    --url "$url"
    --header "Accept: application/vnd.github+json"
    --header "Authorization: Bearer $authorization"
    --header "X-GitHub-Api-Version: $API_VERSION"
    --output "$output_file"
  )

  if [[ -n "$body" ]]; then
    args+=(--header "Content-Type: application/json" --data "$body")
  fi

  curl "${args[@]}"
}

json_field() {
  local input_file="$1"
  local field="$2"
  python3 - "$input_file" "$field" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        value = json.load(handle)[sys.argv[2]]
except (OSError, KeyError, TypeError, ValueError):
    raise SystemExit(1)

if not isinstance(value, (str, int)) or value == "":
    raise SystemExit(1)
print(value)
PY
}

mint_installation_token() {
  local client_id="$1"
  local private_key="$2"
  local temp_dir key_file now issued_at expires_at header payload unsigned signature jwt
  local installation_file installation_id token_file repository_file repository token

  temp_dir="$(mktemp -d)"
  trap "rm -rf -- '$temp_dir'" EXIT
  key_file="$temp_dir/github-app.pem"
  installation_file="$temp_dir/installation.json"
  token_file="$temp_dir/token.json"
  repository_file="$temp_dir/repository.json"

  umask 077
  printf '%s\n' "$private_key" > "$key_file"
  openssl pkey -in "$key_file" -noout >/dev/null 2>&1 \
    || fail "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY is not a valid PEM private key."

  now="$(date +%s)"
  issued_at="$((now - 60))"
  expires_at="$((now + 540))"
  header="$(printf '%s' '{"typ":"JWT","alg":"RS256"}' | b64url)"
  payload="$(printf '{"iat":%s,"exp":%s,"iss":"%s"}' \
    "$issued_at" "$expires_at" "$client_id" | b64url)"
  unsigned="$header.$payload"
  signature="$(printf '%s' "$unsigned" \
    | openssl dgst -sha256 -sign "$key_file" \
    | b64url)"
  jwt="$unsigned.$signature"

  api_request GET \
    "https://api.github.com/orgs/$GITHUB_ORG/installation" \
    "$jwt" "$installation_file" \
    || fail "BDS Fleet Operator credentials were rejected by GitHub. Verify that this service received the complete existing credential pair."
  installation_id="$(json_field "$installation_file" id)" \
    || fail "GitHub returned no installation ID for $GITHUB_ORG."

  api_request POST \
    "https://api.github.com/app/installations/$installation_id/access_tokens" \
    "$jwt" "$token_file" \
    '{"repositories":["forge-telemetry","forge_contract_core"],"permissions":{"contents":"read"}}' \
    || fail "GitHub refused a read-only installation token for DataForge's private dependencies."
  token="$(json_field "$token_file" token)" \
    || fail "GitHub returned no installation token."

  for repository in "${PRIVATE_REPOS[@]}"; do
    api_request GET \
      "https://api.github.com/repos/$GITHUB_ORG/$repository" \
      "$token" "$repository_file" \
      || fail "the minted installation token cannot read $GITHUB_ORG/$repository. The App's organization-wide access is operator-confirmed; verify that this service received the complete existing credential pair."
  done

  rm -rf -- "$temp_dir"
  trap - EXIT
  printf '%s' "$token"
}

clear_legacy_url_rewrites() {
  local key

  # Older builds embedded their token in a url.*.insteadOf subsection. Cached
  # Render build homes can retain those keys, which take precedence over Git's
  # credential helpers. Remove only rewrites targeting GitHub's root or the BDS
  # organization; never print the token-bearing key.
  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    git config --global --unset-all "$key" >/dev/null 2>&1 || true
  done < <(
    git config --global --name-only --get-regexp \
      '^url\..*\.insteadof$' \
      "^https://github\\.com/(${GITHUB_ORG}/)?$" 2>/dev/null || true
  )
}

configure_git() {
  local token="$1"
  local credentials_file repository credential_scope helper_key

  credentials_file="$(mktemp "${TMPDIR:-/tmp}/dataforge-git-credentials.XXXXXX")" \
    || fail "could not create the temporary Git credential store."
  chmod 600 "$credentials_file"

  clear_legacy_url_rewrites

  # Keep the short-lived token out of Git's URL rewrite key and command-line
  # arguments. Each helper is reset and path-scoped so unrelated GitHub
  # credentials cannot be selected from a cached build home.
  git config --global "credential.https://github.com.useHttpPath" true
  for repository in "${PRIVATE_REPOS[@]}"; do
    credential_scope="https://github.com/${GITHUB_ORG}/${repository}.git"
    helper_key="credential.${credential_scope}.helper"

    # Cached Render build homes can accumulate this multi-valued key across
    # deploys. A plain assignment then fails with "cannot overwrite multiple
    # values". Remove every prior value before installing the deliberate empty
    # reset entry and the one build-scoped credential store.
    git config --global --unset-all "$helper_key" >/dev/null 2>&1 || true
    git config --global --add "$helper_key" ""
    git config --global --add \
      "$helper_key" \
      "store --file=$credentials_file"

    printf 'protocol=https\nhost=github.com\npath=%s/%s.git\nusername=x-access-token\npassword=%s\n\n' \
      "$GITHUB_ORG" "$repository" "$token" \
      | git credential approve >/dev/null
  done
}

app_client_id="$(printf '%s' "${FORGE_PRIVATE_DEPS_APP_CLIENT_ID:-}" | tr -d '[:space:]')"
app_private_key="${FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY:-}"
legacy_token="${FORGE_TELEMETRY_TOKEN:-${GITHUB_TOKEN:-}}"

if [[ -n "$app_client_id" || -n "$app_private_key" ]]; then
  [[ -n "$app_client_id" && -n "$app_private_key" ]] \
    || fail "the BDS Fleet Operator client ID and private key must be configured as one complete pair."
  token="$(mint_installation_token "$app_client_id" "$app_private_key")"
  configure_git "$token"
  echo "render-git-auth: short-lived BDS Fleet Operator auth configured for DataForge private dependencies."
elif [[ -n "$legacy_token" ]]; then
  configure_git "$legacy_token"
  echo "render-git-auth: legacy token auth configured; migrate this service to the BDS Fleet Operator pair."
elif [[ -n "${RENDER:-}" ]]; then
  fail "no private-dependency credential is configured. Add the BDS Fleet Operator client ID and private key pair."
else
  echo "render-git-auth: no build credential configured - skipping outside Render."
fi

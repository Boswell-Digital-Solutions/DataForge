#!/bin/sh
# Configure Git for the private forge-* dependencies inside a Docker build.
# Run in the same RUN step as `pip install`, with the BuildKit secrets mounted.
# The caller removes the Git config afterward, so no token stays in an image layer.
#
# BUILD_AUTH_MODE (default "legacy"):
#   legacy - one secret `github_token` serves every github.com URL (the existing path).
#   split  - two secrets, one per repository, each scoped to that repository's URL only:
#              telemetry_token       -> forge-telemetry
#              contract_core_token   -> forge_contract_core
#            Both are required. A missing secret stops the build. `github_token` is never read.
#
# DOCKER_SECRETS_DIR is the secrets directory (default /run/secrets). Tests point it elsewhere.
set -eu

secrets_dir="${DOCKER_SECRETS_DIR:-/run/secrets}"
mode="${BUILD_AUTH_MODE:-legacy}"
org_url="https://github.com/Boswell-Digital-Solutions"

fail() {
  echo "docker-git-auth: ERROR - $1" >&2
  exit 1
}

scope_token_to_repo() {
  secret_file="$1"
  repository="$2"
  [ -s "$secret_file" ] || fail "split mode needs the secret $(basename "$secret_file") for $repository. No fallback credential is used."
  git config --global \
    "url.https://x-access-token:$(cat "$secret_file")@github.com/Boswell-Digital-Solutions/${repository}.git.insteadOf" \
    "${org_url}/${repository}.git"
}

case "$mode" in
  split)
    scope_token_to_repo "$secrets_dir/telemetry_token" forge-telemetry
    scope_token_to_repo "$secrets_dir/contract_core_token" forge_contract_core
    ;;
  legacy)
    if [ -s "$secrets_dir/github_token" ]; then
      git config --global \
        "url.https://x-access-token:$(cat "$secrets_dir/github_token")@github.com/.insteadOf" \
        "https://github.com/"
    fi
    ;;
  *)
    fail "BUILD_AUTH_MODE must be 'legacy' or 'split', not '$mode'."
    ;;
esac

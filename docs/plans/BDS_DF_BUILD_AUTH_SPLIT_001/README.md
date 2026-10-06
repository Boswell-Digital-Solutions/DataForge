# BDS-DF-BUILD-AUTH-SPLIT-001 — one build credential per private repository

Status: IN PROGRESS. Slice 1 (DataForge, PR 101), slice 2 (NeuroForge, PRs 142 and 143), slice 3 (Rake, PR 123), slice 4 (Forge-Agents Render build, PR 146) and slice 5 (Forge-Agents CI, PR 148) are merged. Each Render service runs split mode. DataForge GitHub CI, the DataForge Render web service and the Forge-Agents CI are proven by run records. The other services are proven by operator-pasted build log lines. Open: the Render cron service evidence, the Docker push on `master`, the NeuroForge deploy-key secret file, the Forge-Agents `FORGE_TELEMETRY_DEPLOY_KEY` secret, and the legacy cleanup.
Authorized by Charlie on 2026-10-05: D1, D2 and D3 below, implementation and tests in review PRs only.
Not authorized: App creation, secret installation or rotation, Render configuration changes, live credential tests,
merges, and production deployments. Each needs a separate checkpoint.

## Problem

DataForge builds clone two private repositories: `forge-telemetry` and `forge_contract_core`. One GitHub App
(BDS Fleet Operator) mints one token that names both repositories. The token request is already narrow. The
exposure is the App itself: the build holds that App's private key, and the App's access is organization-wide.
A leak of that key, or of any copy of it, reaches more than two repositories.

Narrowing the token request does not narrow the App. The App installations must be narrow. So each repository
gets its own App, installed on that repository only.

## Decisions (authorized 2026-10-05)

- **D1.** A new build-only App for `forge_contract_core`, with `Contents: read`. Proposed name:
  `BDS Contract Core Build Reader`. The existing `BDS Contract Core Reader` (App 5194470) is not reused,
  widened or redistributed. Its key stays in the Forge_Command `pin-release` environment behind a required reviewer.
- **D2.** A separate build-only App for `forge-telemetry`, with `Contents: read`. Proposed name:
  `BDS Telemetry Build Reader`. The end state removes Fleet Operator and the broad legacy token from each migrated
  build path. No shared credential is revoked before every remaining consumer is accounted for.
- **D3.** First slice: DataForge's build-auth script, its Docker build, and its three CI workflows. The other services
  are inventoried, and not changed.

## Inventory

DataForge build consumers (all in this slice):

| Consumer | Needs | Credential path today | After this slice (split mode) |
|---|---|---|---|
| Render web build (`scripts/render-build.sh`) | both repositories | `scripts/render-git-auth.sh`, Fleet Operator pair | the same script, two Apps |
| Render cron build (`scripts/render-cron-build.sh`) | both repositories | the same script | the same script, two Apps |
| Docker build (`Dockerfile`) | both repositories | one BuildKit secret `github_token` rewrites all of github.com | `scripts/docker-git-auth.sh`, one secret per repository, each scoped to its URL |
| `.github/workflows/test.yml` | both repositories | one token, one global `insteadOf` | two tokens, two path-scoped `insteadOf` entries, plus a read check and a deny check |
| `.github/workflows/docker.yml` | both repositories | one token to the Docker build | two tokens to the Docker build |
| `.github/workflows/deploy.yml` | both repositories | one token to the Docker build | two tokens to the Docker build |

Other services (read only; not changed in this slice):

| Service | Needs | Where | Note |
|---|---|---|---|
| NeuroForge | both repositories | `scripts/render-git-auth.sh`, `scripts/render_build.sh`, `render.yaml`, governed-verification and release workflows | Slice 2. Code merged (NeuroForge PR 142, test fix PR 143). The Render service runs split mode and deployed green (operator-reported 2026-10-06). It has no Dockerfile. Its workflows clone nothing private. |
| Rake | `forge-telemetry` only | `scripts/render-git-auth.sh`, `render.yaml`, `Dockerfile`, `ci-cd.yml`, `quick-test.yml` | Slice 3. Code merged (Rake PR 123). The Render service runs split mode and its build passed preflight (operator-pasted log line, 2026-10-06). Needs no contract-core credential. Gains from D2 only. The Dockerfile uses its own `forge_deps_token` secret. CI strips the private requirement. |
| Forge-Agents | `forge-telemetry` only | `scripts/render-git-auth.sh`, `render-build.sh`, `Dockerfile`, `ci.yml` | Slice 4. Code merged (Forge-Agents PR 146). The Render service runs split mode (operator-pasted log line, 2026-10-06). `ci.yml` has its own mode switch (Forge-Agents PR 148). CI run 37437715387 passed in split mode on 2026-10-06, read from the GitHub run record. Needs no contract-core credential. |

## Credential matrix (split mode)

| Setting | Where | Kind | Holds |
|---|---|---|---|
| `FORGE_BUILD_AUTH_MODE` | Render service env; GitHub repository variable | value | `legacy` (default) or `split` |
| `FORGE_TELEMETRY_APP_CLIENT_ID` | Render env; GitHub repository variable | not secret | the telemetry build App's client ID |
| `FORGE_TELEMETRY_APP_PRIVATE_KEY` | Render env (secret); GitHub **repository** secret | secret | the telemetry build App's key |
| `FORGE_CONTRACT_CORE_APP_CLIENT_ID` | Render env; GitHub repository variable | not secret | the contract-core build App's client ID |
| `FORGE_CONTRACT_CORE_APP_PRIVATE_KEY` | Render env (secret); GitHub **repository** secret | secret | the contract-core build App's key |

Use repository-level GitHub secrets. Organization-level secrets did not inject for these Apps before.
Each App is installed on exactly one repository. No App key is shared between the build and the Forge_Command
`pin-release` environment.

## Migration mode

The mode is explicit. It is set per consumer, and never inferred.

- **legacy** (default). The path that exists today. An unmigrated consumer stays here on its approved credential.
- **split.** A migrated consumer. Split mode needs all four values. It never reads the legacy App, the legacy token,
  or `GITHUB_TOKEN`. A missing value, an invalid key, a refused token, a token that cannot read its own repository,
  or a token that can read the other repository stops the build. An authentication failure never selects a broader credential.
  In the Render script, nothing is configured until both tokens are minted and checked.
- An unknown mode value stops the build.

Legacy mode's own fallback to the old token (`FORGE_TELEMETRY_TOKEN`) is unchanged. It exists only until the consumer moves to split mode.

## Slice 1 — code and offline tests (this PR; review only)

- `scripts/render-git-auth.sh`: split mode, two tokens, a read probe per repository, a deny probe per repository,
  path-scoped credential entries, fail closed.
- `scripts/docker-git-auth.sh` and `Dockerfile`: split mode with one BuildKit secret per repository.
- `.github/actions/private-deps-token`: mints the right tokens by mode. `test.yml`, `docker.yml` and `deploy.yml` use it.
- Tests (all offline, with stubs): `tests/test_render_git_auth.py` (16), `tests/test_docker_git_auth.py` (6),
  `tests/test_private_deps_workflow_steps.py` (15). They cover token requests, credential routing, missing values, invalid keys,
  refused tokens, a token that reaches the other repository, no fallback to the legacy credential, no secret in output, and the
  CI step logic with a stub `git`.
- What offline tests cannot prove: how the real App installations are set up. That is checkpoint evidence below.

## Checkpoint — operator actions and rollout (not authorized; for Charlie)

1. Create the two Apps. Each has `Contents: read` only and is installed on its one repository. Generate one key per App.
2. In the DataForge GitHub repository, add the two client-ID variables and the two key secrets (repository level).
   The mode stays `legacy`. Nothing changes yet.
3. Set the repository variable `FORGE_BUILD_AUTH_MODE=split`. Run CI on a pull request. The `Verify the minted token can actually clone`
   step must pass: it checks that each token reads its own repository and is refused for the other.
4. Render: add the four values to the cron service first, with **Save only**. Set `FORGE_BUILD_AUTH_MODE=split` last.
   Then choose **Save, rebuild, and deploy** (or run a manual deploy). A build authentication change is proven only by a fresh build.
5. Repeat for the web service.
6. Run the Docker workflow on `master`, with the mode `split`.
7. Remove the legacy values only in a later checkpoint, after every consumer (including NeuroForge, Rake and Forge-Agents) is migrated or
   confirmed unaffected. Do not revoke a shared credential before then.
8. In the same cleanup checkpoint, account for the NeuroForge Render secret file `forge_telemetry_deploy_key_b64`. No script in the
   service repositories reads it (checked 2026-10-06). It looks like an older deploy key for `forge-telemetry`. Before removal, check the
   `forge-telemetry` repository's deploy keys. Find out whether the key is still registered and whether it has write access. Remove the
   secret file and the deploy key only when no consumer needs them.

## Shared Render environment groups (optional)

The build scripts read ordinary environment variables. So a Render environment group can supply the values to many services. Use two groups.
Link the telemetry group to every service that clones `forge-telemetry`. Link the contract-core group to DataForge and NeuroForge only.
Rake and Forge-Agents must not receive a contract-core key. A variable set on a service overrides the same name in a group. Set
`FORGE_BUILD_AUTH_MODE` on each service, not in a group, so each service cuts over and rolls back by itself.

A merge of the slice 1 code changes no mode. The mode stays `legacy` until step 3, so a merge does not change a build.

## Checkpoint evidence (recorded 2026-10-06)

Operator actions, done by Charlie: two build Apps created, a read-only scope check, the GitHub variables and secrets, the
repository variable `FORGE_BUILD_AUTH_MODE=split`, and the Render web service redeployed.

| Item | Evidence | Result |
|---|---|---|
| App installations | GitHub API, read-only: `bds-contract-core-build-reader` (App 5206033) and `bds-telemetry-build-reader` (App 5206064), each `contents: read` and `metadata: read`, no events, selected repositories | pass |
| Repository settings | Four names present (two variables, two secrets). The two client IDs match the Apps' public IDs. The mode variable was unset until the operator set `split`. | pass |
| GitHub CI in split mode | PR 103: the `Verify the minted token can actually clone` step printed `split mode: each token reaches its own repository only`. The install step cloned both repositories. The full Test Suite passed, including the Postgres proof. | pass |
| Docker build in split mode | The Docker workflow ran on PR 103 with `BUILD_AUTH_MODE=split` and succeeded | pass (pull-request run only) |
| Render web service (`dataforge`, commit `cde1ecac`) | Build log, operator-supplied: `render-git-auth: split-mode auth configured for DataForge private dependencies (one token per repository).` at 12:59:06 EDT. Both private repositories cloned. The build and deploy succeeded. No credential appears in the log. | pass |
| After the redeploy | `/health` 200; `/version` shows commit `cde1ecac` and `alembic_revision 20261005_01`; the receipt-ingest route still answers 401 without a key | pass |

Open items at this point:

- Render cron service (`dataforge-supabase-log-poll`): the operator reports that the four values and the mode are set and a fresh build ran (2026-10-06). The build-log line has not been supplied, so this is operator-reported, not log-verified.
- Docker workflow on a push to `master`: not yet run in split mode. Only a pull-request run is proven.
- A build-log note: the pre-flight check printed `Dirty: YES` for commit `cde1eca`. It reads the Render build directory, not the repository. It is not caused by this change and is not investigated.
- The legacy values (`FORGE_PRIVATE_DEPS_APP_*`, `FORGE_TELEMETRY_TOKEN`) are still present everywhere as the rollback path. Remove them only in a later checkpoint, after NeuroForge, Rake and Forge-Agents are migrated or confirmed unaffected.
- The two PEM files must be moved or deleted from the operator's Downloads folder.

## Rollback

Set `FORGE_BUILD_AUTH_MODE` back to `legacy` (Render env and the repository variable), then redeploy. The legacy credentials are not
touched until the last checkpoint, so rollback is immediate. Roll back when any split-mode build fails, a deny probe fails, or an App
reaches a repository outside its scope.

## Acceptance evidence

- The reviewed head of each pull request, and every expected check present and green.
- Offline test results for the three test files.
- At the checkpoint: a fresh Render build log per service that names split mode and ends with a successful install; a green CI run
  with the verify step passing in split mode; a successful Docker build; and the list of repositories each App's installation covers.
- A read-only check that each token reaches its own repository and is refused for the other. The scripts and the CI step run this check on every build.

## Merge rule

Merge only the exact authorized head, after every expected required check is present and successful. A skip counts only where the documented
scope policy permits it. A pending, missing, failed, cancelled, or timed-out check is not acceptance. A job skipped because its dependency
failed is not acceptance. Merge-queue or test-merge checks must also pass. Evaluate the expected checks and their causes, not only red marks.

## Not in this work

Receipt-producer key creation, candidate decision writes, the other 48 absent tables, and the root-cause investigation. The Forge_Command
review key is not widened into a receipt-producer key.

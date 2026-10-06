# BDS-DF-BUILD-AUTH-SPLIT-001 — one build credential per private repository

Status: IN PROGRESS. Slice 1 (code and offline tests) is merged. Slice 2 (live rollout) is held and not authorized.
Authorized by Charlie on 2026-10-05: D1, D2 and D3 below, implementation and tests in review PRs only.
Not authorized: App creation, secret installation or rotation, Render configuration changes, live credential tests,
further merges, and production deployments. Each needs a separate checkpoint.

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
| NeuroForge | both repositories | `scripts/render-git-auth.sh`, `scripts/render_build.sh`, `render.yaml`, governed-verification and release workflows | Same two-repository script. Later slice. |
| Rake | `forge-telemetry` only | `scripts/render-git-auth.sh`, `render.yaml`, `Dockerfile`, `ci-cd.yml`, `quick-test.yml` | Needs no contract-core credential. Gains from D2 only. |
| Forge-Agents | `forge-telemetry` only | `scripts/render-git-auth.sh`, `render-build.sh`, `Dockerfile`, `ci.yml` | Needs no contract-core credential. Gains from D2 only. |

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

## Slice 1 — code and offline tests (merged; live proof outstanding)

- `scripts/render-git-auth.sh`: split mode, two tokens, a read probe per repository, a deny probe per repository,
  path-scoped credential entries, fail closed.
- `scripts/docker-git-auth.sh` and `Dockerfile`: split mode with one BuildKit secret per repository.
- `.github/actions/private-deps-token`: mints the right tokens by mode. `test.yml`, `docker.yml` and `deploy.yml` use it.
- Tests (all offline, with stubs): `tests/test_render_git_auth.py` (16), `tests/test_docker_git_auth.py` (6),
  `tests/test_private_deps_workflow_steps.py` (15). They cover token requests, credential routing, missing values, invalid keys,
  refused tokens, a token that reaches the other repository, no fallback to the legacy credential, no secret in output, and the
  CI step logic with a stub `git`.
- What offline tests cannot prove: how the real App installations are set up. That is checkpoint evidence below.

## Reconciliation receipt (2026-10-06 UTC)

- [DataForge PR #101](https://github.com/Boswell-Digital-Solutions/DataForge/pull/101) is merged as
  `00422b8bba28f6f4b114d3441e1c873af17d2448`; reviewed head `efaccffba5df96879bf43b65e8ee601ab8c8bf63`.
- [Portfolio PR #244](https://github.com/Boswell-Digital-Solutions/forge/pull/244) is merged as
  `3e918f1dee9570277ed60c1d80d5d94c21806cdf`. Registration does not authorize rollout.
- The PR #101 record reports 39 passing offline tests including the Render telemetry configuration tests,
  and three caught mutation checks. Those are historical reported results, not a new test run in this reconciliation.
- One of two slices is complete at the code/offline level. Overall evidence remains partial; no live split-mode
  acceptance is recorded here. Related PR records, the #101 discussion and current plan contain no newer rollout authorization.
  A code merge does not prove the deployed revision, current variable values, or real installation scope.

## Next bounded operator checkpoint — CP2 preflight (read only)

Prepare a redacted go/no-go packet for Charlie before requesting any live action. This checkpoint permits
inspection and documentation only: no App creation, key generation, secret installation, token minting,
workflow dispatch, variable changes, rebuilds, deploys or credential revocation.

Required evidence:

1. Pin current DataForge `master`, the merged Slice 1 head and merge commit, and portfolio registration.
   Capture expected check names, conclusions and run links for the exact reviewed head; do not infer green checks from a merge.
2. Record existing App installation metadata and selected-repository permissions without reading key values.
   Distinguish the Fleet Operator from the protected Forge_Command reader. Proposed Apps must each select exactly
   one repository with `Contents: read` and only GitHub's required implicit permissions. Token deny probes alone
   cannot prove the App/key has no broader installation access.
3. Record DataForge GitHub variable names and effective mode, secret names/presence only, and the exact Render
   web/cron service IDs, deployed revisions and effective mode. An absent mode defaults to legacy; an unreadable
   setting is unknown, not evidence of legacy. Confirm existing approved rollback credentials remain available without exposing them.
4. Inspect workflow triggers and side effects before any future repository-wide mode switch: `docker.yml` and
   `deploy.yml` can publish images. Record whether saving Render environment values or auto-deploy settings would
   trigger a deployment. Define a build-only validation path or explicitly include publishing/deployment in the later authorization.
5. Name each proposed live stage, consumer, operator, proof and rollback scope. Submit the packet with unresolved
   facts marked unknown and an explicit decision request. CP2 completion grants no live stage.

Stop CP2 if the source head changed in relevant code, authorization is ambiguous, settings cannot be inspected,
rollback availability is unknown, App scope is broader than intended, checks are missing or unsuccessful, or
a supposed read-only action would mint credentials, publish or deploy. Record the gap; do not widen access or repair live settings.
CP2 rollback is to discard/revise the packet; it changes no live state.

### Later live stages (all held; each requires separate explicit authorization)

The sequence below is a proposed runbook, not an executable authorization. Authorize each named stage and its
side effects independently: (A) App creation/installation and key custody; (B) GitHub repository settings with
mode retained as legacy; (C) controlled CI mode switch and fresh build proof; (D) Render cron; (E) Render web;
(F) Docker build proof and any image publication. Do not advance automatically after a successful stage.
Legacy credential cleanup/revocation is a separate final checkpoint with the complete cross-service consumer inventory.

For every live stage, retain redacted installation evidence, exact revision, run/deploy ID and timestamps,
effective mode, own-repository read successes, cross-repository denial evidence, dependency-install/build result,
and service health where deployed. Cached dependency success is insufficient. A denial must be attributable
to access control; timeout, transport failure or service outage is inconclusive. Never put key/token values in the packet.

Stop progression on a failed or inconclusive probe/build, secret exposure, broader App installation scope,
unexpected workflow publishing/deployment, absent required checks, or service regression. Do not bypass the probe,
weaken fail-closed behavior, fall back automatically, or migrate another consumer.

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

A merge of the slice 1 code changes no mode. The mode stays `legacy` until step 3, so a merge does not change a build.

## Rollback

For an authorized live stage, restore the recorded pre-stage mode on the affected consumer only.
For GitHub, restore the repository variable and stop further split-mode runs; verify a fresh legacy build under the approved
workflow scope. For Render, set `FORGE_BUILD_AUTH_MODE=legacy` on the affected service and rebuild/redeploy within the
stage's rollback authorization, then verify build success and service health. Do not change unaffected consumers. The legacy credentials must remain available
until the final cleanup checkpoint. Rollback requires an explicit operator change and a fresh successful build;
it is not immediate and is never an automatic fallback. Roll back when any split-mode build fails, a deny probe fails, or an App
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

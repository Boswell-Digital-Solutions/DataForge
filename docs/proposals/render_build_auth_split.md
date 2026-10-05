# Render build-auth split — proposal

Status: PROPOSED 2026-10-05. Not approved. No change is made.

## What is true today

- Four cloud services use a copy of `scripts/render-git-auth.sh`: DataForge, NeuroForge, Rake and Forge-Agents.
  DataForge and NeuroForge list two private dependencies: `forge-telemetry` and `forge_contract_core`.
  Forge-Agents lists `forge-telemetry` only. Rake was not read for this proposal.
- The script mints one short-lived installation token from the BDS Fleet Operator App. The request names both
  repositories. The script then stores that one token under a path-scoped Git credential for each repository.
- The script itself says that the App's access is organization-wide. So the build credential is broader than the two
  repositories it needs.
- DataForge CI (`test.yml`, `deploy.yml`, `docker.yml`) mints the same two-repository token with the same App.
- `FORGE_TELEMETRY_TOKEN` stays as a legacy fallback that reads both repositories.

## The problem

A new GitHub App, `BDS Contract Core Reader` (App ID 5194470), has `contents: read` on `forge_contract_core` only.
The old script cannot use it. The token request names `forge-telemetry` too, and GitHub refuses it.
Widening the new App to make the old script work would remove its value.

## Goal

Each private repository gets its own credential. No token can read the other repository.
The build then no longer needs one credential with access to both.

## Design

1. The script mints two tokens. One comes from the existing App for `forge-telemetry`. One comes from the contract-core App
   for `forge_contract_core`. Each request names one repository only.
2. Each token goes into its own path-scoped Git credential entry. This is the structure the script already has. Only the
   token source changes.
3. New configuration: `FORGE_CONTRACT_CORE_APP_CLIENT_ID` and `FORGE_CONTRACT_CORE_APP_PRIVATE_KEY`, per service.
   A service that needs only one repository sets only that pair.
4. The build fails closed. A missing pair, an invalid key, or a refused token stops the build. No token appears in a log.
5. The legacy token stays as a migration fallback for `forge-telemetry` only, with a log line that says so.
   It does not serve `forge_contract_core` any more.
6. Apply the same change to DataForge, NeuroForge and Rake. Forge-Agents needs no change until the telemetry credential is narrowed.
   Apply the same split to the DataForge CI workflows.

## Tests

For each changed script, with a stub GitHub API (the existing tests in Rake and NeuroForge show the pattern):
- The contract-core token is requested for `forge_contract_core` only, and never for `forge-telemetry`.
- Each credential entry is path-scoped and holds its own token.
- A missing pair, an invalid key and a refused token each fail the build with a clear message.
- No token value appears in output.
- The legacy token serves `forge-telemetry` and not `forge_contract_core`.

## Rollout order

1. Merge the code in each repository. It accepts the new pair and keeps the old path as a fallback.
2. Add the new pair to each Render service and to CI. Render saves a variable without a restart, so redeploy after.
3. Build once per service. Confirm the log names the split path.
4. Remove the old two-repository path only after every service builds on the split path.

## Decisions for Charlie

- D1: Reuse App 5194470 for builds, or create a second App for them? Recommendation: a second App, named for its build use. The
  existing App's private key lives in the `pin-release` environment in Forge_Command, behind a required reviewer. Copying
  that key into Render service variables and CI would remove that gate.
- D2: Narrow the `forge-telemetry` credential too, with its own App scoped to that repository? This is what removes the
  organization-wide App from the build path. It needs one more App and one more pair of variables.
- D3: Which services and CI jobs are in the first change?

## Do not

- Widen an App's repository access to make the old script work.
- Change Render variables before the code reads the new pair.
- Put an App private key in chat.

# Render build-auth split — proposal (superseded by a plan)

Status: AUTHORIZED 2026-10-05 for implementation and review PRs. Superseded by
[BDS-DF-BUILD-AUTH-SPLIT-001](../plans/BDS_DF_BUILD_AUTH_SPLIT_001/README.md). Rollout is not authorized.

Charlie answered the three decisions: D1 a separate contract-core build App, D2 a separate telemetry-only build App,
D3 DataForge's script and its CI first. The plan holds the inventory, credential matrix, migration mode, rollout
sequence, rollback, and acceptance evidence.

## Corrections to the first version of this proposal

1. **The exposure is the App, not the token.** The first version said the build credential was broader than the two
   repositories it needs. The token request is already narrow (two repositories, read only). The broad part is the
   App and its private key, which the script records as organization-wide. Narrowing the token request does not narrow
   the App. The fix has to narrow the App installations.
2. **The legacy token is not a reduction.** Keeping the old two-repository token for telemetry only would not reduce
   its permissions. It would remain temporary security debt.
3. **Migration mode must be explicit.** The first version stopped on a missing credential and also kept a legacy
   fallback. Now a consumer is either in `legacy` mode or in `split` mode. In split mode, no failure ever selects a broader credential.
4. **Render saves are not all alike.** The first version said Render saves a variable without a restart. Render offers
   Save only, Save and deploy, and Save, rebuild, and deploy. The rollout names the action. A build-authentication change
   is proven only by a fresh build.
5. **The merge rule was too weak.** "Pass or skipping" is not enough. See the plan's merge rule.
6. **Mocked tests are not operational proof.** The offline tests prove the code. Only the checkpoint evidence proves the real App installations.
7. **Rake was read.** Rake and Forge-Agents need `forge-telemetry` only. They gain from D2 and need no contract-core credential.

# DataForge — Compiled System Reference

**Designation:** DTF
**Document role:** Canonical compiled technical reference for the DataForge durable-truth service
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 2.3 (2026-07-23) — DataForge search producer cut over to canonical ForgeEvent.v1 transport
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/DTFSYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Primary output: `doc/DTFSYSTEM.md`

This `doc/system/` tree is the canonical source of truth for DataForge. It uses
explicit **truth classes**: *canonical facts* define the source-of-truth
contract, persistence/retrieval authority, write-boundary invariants, fail-closed
posture, and ecosystem contracts; *snapshot facts* are dated, audit-derived
counts (mounted routers, Alembic migrations, Python/test files, collected tests).
See §11 for the scope and authority boundary and §12 for ownership and
designation doctrine. The sibling `../forge-telemetry/` repo is documented separately.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `00_overview/01-overview-philosophy.md` | Service identity, source-of-truth contract, current role, what it is not |
| §2 | `00_overview/02-architecture.md` | Architecture, persistence + hybrid retrieval, governance surfaces |
| §3 | `00_overview/03-project-structure.md` | Repository tree, module layout |
| §4 | `10_service-contract/04-api-layer.md` | Mounted API families, endpoints, auth |
| §5 | `10_service-contract/05-proving-slice-schema.md` | Proving-slice schema contract |
| §6 | `10_service-contract/06-pressforge-automation-schema.md` | PressForge automation schema contract |
| §7 | `20_runtime/07-backend-internals.md` | CRUD, search, embeddings, lifecycle internals |
| §8 | `20_runtime/08-error-handling.md` | Error handling, lifecycle & access control |
| §9 | `30_dependencies/09-tech-stack.md` | Dependencies, versions, runtime requirements |
| §10 | `30_dependencies/10-ecosystem-integration.md` | Cross-service persistence contracts |
| §11 | `40_governance/11-scope.md` | Service authority boundary, write-boundary, truth classes |
| §12 | `40_governance/12-governance.md` | Ownership, designation doctrine, authority hierarchy |
| §13 | `40_governance/13-change-control.md` | Change classes, evidence, verification commands |
| §14 | `50_operations/14-config-env.md` | Configuration and environment variables |
| §15 | `50_operations/15-testing.md` | Test structure, markers, coverage posture |
| §16 | `50_operations/16-handover.md` | Critical constraints, invariants, migration runbook |
| §17 | `99_appendices/17-appendices.md` | Glossary, cross-references, revision history |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

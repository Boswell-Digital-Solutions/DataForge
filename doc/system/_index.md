# DataForge System Documentation

**Document version:** 1.2 (2026-04-03) — Canonical docs reconciled against live mounted routes and modular schema layout
**Protocol:** Forge Documentation Protocol v1

This `doc/system/` tree uses explicit truth classes:
- Canonical facts define DataForge's durable-truth role, service boundary, port, lifecycle invariants, and auth semantics.
- Snapshot facts define audit-derived router, endpoint, schema, test, coverage, or inventory totals.

Assembly contract:
- Command: `bash doc/system/BUILD.sh`
- Primary output: root `SYSTEM.md`
- Additional mirrored outputs: `doc/SYSTEM.md`, legacy `doc/dfSYSTEM.md`

| Part | File | Contents |
|------|------|----------|
| §1 | [01-overview-philosophy.md](01-overview-philosophy.md) | Service purpose, source-of-truth philosophy, ecosystem role |
| §2 | [02-architecture.md](02-architecture.md) | Component map, hybrid search, vector pipeline, multi-tenant model |
| §3 | [03-tech-stack.md](03-tech-stack.md) | Exact dependencies and versions |
| §4 | [04-project-structure.md](04-project-structure.md) | Directory tree, key files, ORM models |
| §5 | [05-config-env.md](05-config-env.md) | All environment variables with types and defaults |
| §6 | [06-api-layer.md](06-api-layer.md) | Live mounted API surface, auth posture, and source-present vs mounted boundaries |
| §7 | [07-backend-internals.md](07-backend-internals.md) | Vector search, chunking, encryption, anomaly detection |
| §8 | [08-ecosystem-integration.md](08-ecosystem-integration.md) | Current mounted integration contracts per service and operator surface |
| §9 | [09-error-handling.md](09-error-handling.md) | Lifecycle state machine, access control matrix, 409 rules |
| §10 | [10-testing.md](10-testing.md) | Current test inventory, audited counts, and execution posture |
| §11 | [11-handover.md](11-handover.md) | Critical constraints, access control matrix, migration runbook |
| §12 | [12-pressforge-automation-schema.md](12-pressforge-automation-schema.md) | PressForge Automation Schema — 11 new pf_* tables, column additions, indexes, CRUD endpoints |

## Quick Assembly

```bash
bash doc/system/BUILD.sh   # Assembles all parts into SYSTEM.md (+ mirrored legacy outputs)
```

*Last updated: 2026-04-03*

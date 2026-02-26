# DataForge System Documentation

> BDS Documentation Protocol v1.0 — modular reference for AI-assisted development

| Part | File | Contents |
|------|------|----------|
| §1 | [01-overview-philosophy.md](01-overview-philosophy.md) | Service purpose, source-of-truth philosophy, ecosystem role |
| §2 | [02-architecture.md](02-architecture.md) | Component map, hybrid search, vector pipeline, multi-tenant model |
| §3 | [03-tech-stack.md](03-tech-stack.md) | Exact dependencies and versions |
| §4 | [04-project-structure.md](04-project-structure.md) | Directory tree, key files, ORM models |
| §5 | [05-config-env.md](05-config-env.md) | All environment variables with types and defaults |
| §6 | [06-api-layer.md](06-api-layer.md) | All 29 routers, 80+ endpoints, auth requirements |
| §7 | [07-backend-internals.md](07-backend-internals.md) | Vector search, chunking, encryption, anomaly detection |
| §8 | [08-ecosystem-integration.md](08-ecosystem-integration.md) | Integration contracts per service (BugCheck, NeuroForge, etc.) |
| §9 | [09-error-handling.md](09-error-handling.md) | Lifecycle state machine, access control matrix, 409 rules |
| §10 | [10-testing.md](10-testing.md) | Test suite structure, coverage, compliance tests |
| §11 | [11-handover.md](11-handover.md) | Critical constraints, access control matrix, migration runbook |
| §12 | [12-pressforge-automation-schema.md](12-pressforge-automation-schema.md) | PressForge Automation Schema — 11 new pf_* tables, column additions, indexes, CRUD endpoints |

## Quick Assembly

```bash
bash doc/system/BUILD.sh   # Assembles all parts into doc/dfSYSTEM.md
```

*Last updated: 2026-02-25*

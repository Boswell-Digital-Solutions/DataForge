# §1 — Overview & Philosophy

## Service Identity

**DataForge** is the resident FastAPI service that owns durable ecosystem truth. It is
the persistence, retrieval, and governance evidence boundary behind the rest of Forge,
not a bootstrap repo or passive library.

- **Runtime posture:** Resident HTTP service
- **Default port:** `8001`
- **Authority boundary:** Postgres-backed durable state, hybrid retrieval, policy/runtime evidence, and scoped write enforcement
- **Mounted router objects:** `35` from `app/main.py` (audit: 2026-04-03)
- **Router modules in source:** `39`
- **Alembic migrations:** `47`
- **Python files under `app/`:** `175`
- **Pytest files:** `39`
- **Collected tests:** `565` via `PYTHONPATH=. ./.venv/bin/pytest --collect-only -q`
- **Nested repo boundary:** `forge-telemetry/` is a separate git repo with its own documentation stack

## The Source-of-Truth Contract

DataForge is not a convenience mirror. Durable state written here is the canonical record
for the ecosystem.

Every major Forge runtime writes authoritative records into DataForge:

- **NeuroForge** persists inference records, model-routing evidence, and learning data.
- **VibeForge** persists projects, sessions, outcomes, analytics, and preferences.
- **AuthorForge** persists project, chapter, scene, manuscript, map, and asset state.
- **ForgeAgents / BugCheck** persist agent definitions, run evidence, findings, enrichments, and lifecycle events.
- **Forge:SMITH** persists planning sessions, deliverables, portfolio projects, and evaluations.
- **ForgeCommand** depends on DataForge for execution evidence, key control, secret sync, and governance-adjacent state.
- **Sentinel / Press / private-source / runtime-governance surfaces** persist sweep records, automation records, profile state, policy envelopes, and promotion receipts.

If a service cannot persist required durable state to DataForge, the operation is not complete.
That fail-closed posture is intentional.

## Current Service Role

### 1. Durable Persistence
PostgreSQL remains the authority boundary for documents, runs, findings, planning state,
authoring assets, pricing data, policy ledgers, press automation records, and private-source
profiles.

### 2. Hybrid Retrieval
DataForge stores chunked documents with vector embeddings and full-text indexes, then
serves semantic, keyword, and fused search through the mounted search routers.

### 3. Scoped Authentication and Write Boundaries
The live mounted surface exposes JWT/token compatibility routes, admin key rotation,
service-key validation, run-scoped write flows, and admin-token protected control surfaces.
The repo also contains a richer secure auth stack in source, but that stack is not mounted
by default and therefore is not part of the live surface contract.

### 4. Runtime Governance Evidence
DataForge now persists policy envelopes, policy ledgers, reward records, runtime-promotion
receipts, candidate approvals/rejections, rate-limit state, and execution evidence for
operator review.

### 5. Platform and Operator Surfaces
The mounted app includes control surfaces for secret sync/read, compression dictionaries,
Sentinel sweep/healing record persistence, PressForge automation tables, FPVS health/version
probes, diligence workflows, and private-source ingestion profiles.

### 6. Fail-Closed Readiness
Redis is derived state only. Database and pgvector readiness drive the authoritative ready
signal. Startup will surface dependency problems through readiness instead of silently
downgrading authority decisions.

## What DataForge Is Not

- **Not a cache authority.** Redis accelerates reads and rate limits; it does not own truth.
- **Not an orchestrator.** ForgeCommand remains the ecosystem operator/control plane.
- **Not an autonomous healer.** Sentinel data is persisted here, but DataForge does not itself perform autonomous repair.
- **Not the live OAuth2/TOTP gateway on the default mounted surface.** Those secure auth modules exist in source only until explicitly wired in `app/main.py`.
- **Not the `forge-telemetry` codebase.** The nested repo is versioned and documented separately.

*See §11 for the invariants that must remain true across future changes.*

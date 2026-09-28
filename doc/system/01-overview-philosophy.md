# §1 — Overview & Philosophy

## Service Identity

**DataForge** is the resident FastAPI service that owns approved durable ecosystem truth. It is
the persistence, retrieval, and governance evidence boundary behind the rest of Forge,
not a bootstrap repo or passive library.

- **Runtime posture:** Resident HTTP service
- **Default port:** `8001`
- **Authority boundary:** Postgres-backed durable state, hybrid retrieval, policy/runtime evidence, and scoped write enforcement
- **Mounted router objects:** `45` from `app/main.py` (audit: 2026-07-20)
- **Router modules in source:** `50`
- **Alembic migrations:** `66`
- **Python files under `app/`:** `215`
- **Pytest files:** `60`
- **Collected tests:** `791` via `python -m pytest --collect-only -q --no-cov`
- **Sibling repo boundary:** `../forge-telemetry/` is a separate git repo with its own documentation stack

## The Source-of-Truth Contract

DataForge is not a convenience mirror. Durable state written here is the canonical record
for the ecosystem.

Every major Forge runtime writes authoritative records into DataForge:

- **NeuroForge** persists inference records, model-routing evidence, and learning data.
- **VibeForge** persists projects, sessions, outcomes, analytics, and preferences.
- **AuthorForge is the explicit local-authority exception.** Its embedded database is the
  exclusive source of truth for projects and all user-authored content. DataForge may persist
  only the strict, minimized `AuthorForgeAnalyticsEnvelope.v1` telemetry contract.
- **ForgeAgents / BugCheck** persist agent definitions, run evidence, findings, enrichments, and lifecycle events.
- **Forge:SMITH** persists planning sessions, deliverables, portfolio projects, and evaluations.
- **ForgeCommand** depends on DataForge for execution evidence, key control, secret sync, and governance-adjacent state.
- **Sentinel / Press / private-source / runtime-governance surfaces** persist sweep records, automation records, profile state, policy envelopes, and promotion receipts.

If a service cannot persist DataForge-owned durable state to DataForge, the operation is not
complete. That fail-closed posture is intentional. It must never be interpreted as authority
to copy AuthorForge content out of AuthorForge's embedded database.

## Current Service Role

### 1. Durable Persistence
PostgreSQL remains the authority boundary for DataForge corpus documents, runs, findings,
planning state, pricing data, policy ledgers, press automation records, and private-source
profiles. AuthorForge manuscripts, chapters, scenes, notes, research, worldbuilding,
attachments, embeddings, prompts, responses, and identity are outside this boundary.

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
- **Not the `forge-telemetry` codebase.** The sibling repo is versioned and documented separately.
- **Not AuthorForge's cloud content backend.** `/api/projects` is a fail-closed `410` tombstone;
  it does not parse, serve, sync, or persist AuthorForge content.

*See §11 for the invariants that must remain true across future changes.*

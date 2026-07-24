<p align="center">
  <img src="https://firebasestorage.googleapis.com/v0/b/endless-fire-467204-n2.firebasestorage.app/o/Forge%2FDataForge_icon.avif?alt=media&token=1e81b1bd-9cf2-4e56-9f3a-e9aa14b9cd0a"
       alt="DataForge Logo"
       width="180"
       style="border-radius: 12px;" />
</p>

<h1 align="center">DataForge</h1>
<h3 align="center">Core Data & Knowledge Engine</h3>
<h4 align="center">Unified intelligence layer for the Forge Ecosystem</h4>

## Documentation Contract

- **Repo type:** Resident HTTP service
- **Authority boundary:** Durable truth ownership, persistence, search, and lifecycle enforcement for the Forge ecosystem
- **Deep reference:** `doc/system/_index.md`, root `SYSTEM.md` (legacy `doc/dfSYSTEM.md` mirror), `../docs/canonical/ecosystem_canonical.md`
- **README role:** Service overview and operator entrypoint
- **Truth note:** Snapshot numbers in this README are audit facts; when this file conflicts with generated `SYSTEM.md`, generated `SYSTEM.md` wins
- **Nested repo note:** `forge-telemetry/` is a separate git repo inside this tree and maintains its own documentation stack

<p align="center">
  <img src="https://img.shields.io/badge/Status-Resident%20Service-brightgreen" />
  <img src="https://img.shields.io/badge/License-Commercial-red" />
  <img src="https://img.shields.io/badge/Mounted%20Routers-35-blue" />
  <img src="https://img.shields.io/badge/Router%20Modules-39-blue" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" />
  <img src="https://img.shields.io/badge/Alembic%20Migrations-47-blue" />
  <img src="https://img.shields.io/badge/Collected%20Tests-565-blue" />
</p>

---

> **License (Commercial)**
> This product is commercial, closed-source software owned by **Boswell Digital Solutions LLC (BDS)**.
> See [LICENSE.md](./LICENSE.md) and [LEGAL.md](./LEGAL.md) for complete terms.

---

> **Ecosystem context**
> Service topology, canonical ports, and cross-service doctrine are centralized in `../docs/canonical/ecosystem_canonical.md`.

## Overview

**DataForge** is the live resident data service for the Forge ecosystem. It owns durable
truth for documents, runs, planning state, findings, provider governance, runtime promotion
receipts, policy envelopes, Sentinel records, press automation records, and other shared
state that the surrounding products depend on.

The current contract is defined by:

- the mounted FastAPI surface in `app/main.py`
- the modular schema layout under `app/models/`
- the generated system documentation assembled from `doc/system/`

## Current Snapshot

| Surface | Current truth |
|---------|---------------|
| Runtime posture | Resident FastAPI service |
| Default port | `8001` |
| Mounted router objects | `46` |
| Python modules under `app/api/` | `62` |
| Alembic migrations | `63` |
| Python files under `app/` | `210` |
| Pytest files | `54` |
| Collected tests | `730` via `pytest --collect-only -q` on 2026-07-14 |
| Canonical docs | `doc/system/` plus generated `doc/DTFSYSTEM.md` |
| Nested repo boundary | `forge-telemetry/` is a separate git repo with its own docs stack |
| Forge Telemetry ingress | Canonical `POST /api/v1/telemetry/events`; one `ForgeEvent.v1` per request, 65,536 RFC 8785 bytes maximum, fail-closed writer |
| DataForge telemetry producer | Search outcomes use the pinned canonical async HTTP transport with explicit self-ingest URL and exact-bound producer key |
| Forge Telemetry validation | Authority-pinned expected-error profile; code-only 422 responses with no submitted values |

## What DataForge Owns

- Durable persistence for product state across NeuroForge, VibeForge, AuthorForge, ForgeAgents, BugCheck, Forge:SMITH, and operator workflows.
- Hybrid semantic and keyword retrieval through the mounted `/api/search` family.
- Scoped auth and operator-control surfaces such as `/auth`, `/api/auth`, `/admin/api-keys`, `/admin/token`, and `/secrets`.
- Governance evidence for runtime promotion, deterministic policy envelopes, reward ledgers, rate limits, and execution history.
- Platform state for Sentinel, PressForge automation, pricing/catalog/cost ledgers, and private-source profiles.
- Authenticated canonical `ForgeEvent.v1` ingestion and separate durable
  `forge_events_v1` storage, with content-bound identities, sink-owned
  `received_at`, and the authority-pinned 65,536-byte producer projection ceiling.

## Live Control Surfaces

Representative mounted families:

- Search and content admin: `/api/search`, `/admin/documents`, `/admin/domains`, `/admin/tags`
- Auth and key control: `/auth/token`, `/api/auth/*`, `/auth/whoami`, `/admin/api-keys/*`, `/admin/token/*`
- Product persistence: `/api/neuroforge/*`, `/api/vibeforge/*`, `/api/projects/*`, `/api/v1/smithy/*`, `/api/teams/*`
- Agent and run persistence: `/api/v1/agents/*`, `/api/v1/forge-run/*`, `/api/v1/bugcheck/*`, `/api/v1/runs/*`, `/api/v1/experience/*`
- Governance and operator data: `/api/v1/runtime-promotion/*`, `/api/v1/policy-*`, `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/rate-limits`, `/api/v1/sentinel`, `/api/compression/dictionaries`, `/api/v1/press`, `/api/v1/private-source-profiles`
- Canonical operational telemetry: `GET /api/v1/telemetry/capabilities/forge-event-v1`
  and `POST /api/v1/telemetry/events`
- HTML and probes: `/`, `/admin`, `/admin-ui`, `/diligence*`, `/health`, `/health/render`, `/ready`, `/version`, `/docs`, `/redoc`

Important boundary notes:

- There is **no root `/metrics` route mounted by default** in the current app.
- ForgeEvent.v1 size validation applies to the complete RFC 8785 producer
  projection, not to `attributes` and `metrics` independently; violations report
  `event_size_exceeded`.
- The exact invalid producer fixtures and stable value-free codes are pinned
  from `forge_contract_core` snapshot
  `1b84d2d666d4bfaa64aaf76ca0b323c78e99f84d`.
- The canonical writer is disabled unless
  `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED=true`. The capability endpoint reports
  that live state. There is no pre-v1 API fallback, compatibility alias, or dual-write.
- DataForge's own search producer is `app/telemetry_client.py`. It emits only
  `search.completed` and `search.failed` with an allowlisted search kind and
  aggregate timing/count metrics. Query text, tags, domain identifiers, and raw
  exception values never enter the event.
- Producer admission requires `DATAFORGE_TELEMETRY_BASE_URL` and a dedicated
  `DATAFORGE_TELEMETRY_API_KEY` bound to `service_name=dataforge`, the exact
  `ENVIRONMENT`, `tenant_ref=null`, and `telemetry:write`. It does not reuse the
  broad `DATAFORGE_API_KEY` or infer a deployment URL.
- `/health/telemetry` reports non-secret capability, bounded-worker state, and
  delivery counters. Application shutdown closes admission and observes the
  transport's finite drain deadline.
- `auth_secure_router.py`, `tracing_router.py`, `api_deployment_router.py`, `replication_router.py`, `cache_replication_router.py`, `dlq_router.py`, and similar modules are source-present only until mounted.
- `forge-telemetry/` is not part of the DataForge runtime tree for documentation or ownership purposes.

## Quick Start

```bash
cd /home/charlie/Forge/ecosystem/DataForge

.venv/bin/pip install -r requirements.txt
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge \
  .venv/bin/alembic upgrade head

PYTHONPATH=. ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Basic verification:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/ready
curl http://127.0.0.1:8001/version
PYTHONPATH=. ./.venv/bin/pytest --collect-only -q
```

## Documentation

Use these in order:

- Canonical implementation reference: [SYSTEM.md](./SYSTEM.md)
- Source docs that generate `SYSTEM.md`: [doc/system/_index.md](./doc/system/_index.md)
- Repo-local working instructions: [CLAUDE.md](./CLAUDE.md)
- Repo architecture summary: [dataforge_architecture_spec.md](./docs/dataforge_architecture_spec.md)

Historical guides and archive material still exist in `docs/`, but when they conflict with the
generated system docs, the generated system docs win.

## Boundaries and Non-Goals

- DataForge is the durable-truth and retrieval boundary, not the ecosystem orchestrator.
- Redis is derived state only; authoritative decisions must remain derivable from Postgres-backed state or signed evidence.
- Sentinel healing logic is not performed by DataForge itself; DataForge persists sweep and healing-event records.
- The richer OAuth2/TOTP auth stack exists in source, but it is not part of the default mounted runtime surface until wired into `app/main.py`.

## License

DataForge is commercial software owned by Boswell Digital Solutions LLC.

- License terms: [LICENSE.md](./LICENSE.md)
- Legal protections: [LEGAL.md](./LEGAL.md)

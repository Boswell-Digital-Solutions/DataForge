# §4 — API Layer

*Last updated: 2026-04-04*

The live API contract is whatever `app.main:app` mounts. A route audit against `app.routes`
on 2026-04-04 confirmed `36` mounted router objects plus app-level docs, HTML views, and
probe routes. `app/api/` contains additional routers, but they are not part of the live
surface until explicitly included in `app/main.py`.

This service exposes both JSON APIs and a small HTML surface. It is incorrect to treat the
entire mounted surface as JSON-only.

## Canonical Probe and HTML Routes

| Surface | Paths | Notes |
|---------|-------|-------|
| Root info | `/` | Basic service entrypoint |
| Health | `/health`, `/health/render` | Liveness and rendered health surface |
| Readiness | `/ready` | Dependency-aware readiness |
| Version | `/version` | FPVS version/build metadata |
| Admin HTML | `/admin`, `/admin-ui` | Server-rendered operator view |
| Diligence HTML | `/diligence`, `/diligence/dashboard`, `/diligence/new`, `/diligence/projects/{project_id}`, `/diligence/reviews/{review_id}` | Server-rendered diligence views |
| OpenAPI docs | `/docs`, `/redoc`, `/openapi.json` | Development/operator documentation |

There is **no root `/metrics` route mounted by default** in the current app.

## Mounted Router Families

| Family | Key prefixes | Representative mounted routes | Notes |
|--------|--------------|-------------------------------|-------|
| Search and document admin | `/api/search`, `/admin/documents`, `/admin/domains`, `/admin/tags` | `POST /api/search`, `POST /api/search/hybrid`, `GET /api/search/stats`, `POST /admin/documents` | Hybrid retrieval plus document/domain/tag CRUD |
| Auth compatibility and operator key control | `/auth`, `/api/auth`, `/auth/whoami`, `/admin/api-keys`, `/admin/token` | `POST /auth/token`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /admin/api-keys/generate`, `POST /admin/token/rotate` | Live mounted auth is JWT/login compatibility plus admin key/token tooling |
| NeuroForge and learning | `/api/neuroforge`, `/api/v1/runs`, `/api/v1/learning` | `POST /api/neuroforge/inferences`, `POST /api/neuroforge/routing-decisions`, `POST /api/v1/runs`, `GET /api/v1/learning/model-performance` | Inference, routing, run logging, and learning feedback |
| VibeForge and team state | `/api/vibeforge`, `/api/teams` | `POST /api/vibeforge/projects`, `POST /api/vibeforge/sessions`, `GET /api/teams/{team_id}`, `GET /api/teams/{team_id}/insights` | Project/session persistence and team insights |
| AuthorForge content graph | `/api/projects` | `POST /api/projects`, `POST /api/projects/{project_id}/chapters`, `POST /api/projects/manuscripts`, `GET /api/projects/{project_id}/map/settings` | Large mounted authoring/content surface with chapters, scenes, maps, assets, collections, arcs, and alerts |
| Forge:SMITH | `/api/v1/smithy/planning`, `/api/v1/smithy/portfolio` | `POST /api/v1/smithy/planning/sessions`, `POST /api/v1/smithy/planning/sessions/{session_id}/start`, `POST /api/v1/smithy/portfolio/projects` | Planning session state, deliverables, and portfolio/evaluation records |
| Agents, runs, and BugCheck | `/api/v1/agents`, `/api/v1/forge-run`, `/api/v1/bugcheck`, `/api/v1/experience` | `POST /api/v1/agents`, `POST /api/v1/forge-run/persist`, `POST /api/v1/bugcheck/runs/{run_id}/findings`, `POST /api/v1/experience` | Agent registry, execution evidence, BugCheck persistence, experience store |
| Governance and runtime shaping | `/api/v1/runtime-promotion`, `/api/v1/policy-envelopes`, `/api/v1/policy-runs`, `/api/v1/policy-routing` | `POST /api/v1/runtime-promotion/receipts/local-failure-pattern`, `POST /api/v1/runtime-promotion/candidates/{candidate_id}/approve`, `PUT /api/v1/policy-envelopes/{policy_key}`, `POST /api/v1/policy-runs/ledger` | Promotion receipts, candidate review, deterministic policy envelopes, bandit state, reward records |
| Diligence and event persistence | `/api/diligence`, `/api/v1/events`, `/ingest/tarcie` | `POST /api/diligence/reviews`, `POST /api/diligence/findings`, `POST /api/v1/events`, `POST /ingest/tarcie` | Compliance review workflows, append-only event ingest, Tarcie friction ingest |
| Platform and operator data surfaces | `/secrets`, `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/batch`, `/api/v1/rate-limits`, `/api/v1/sentinel`, `/api/compression/dictionaries`, `/api/v1/press`, `/api/v1/private-source-profiles` | `POST /secrets/sync`, `POST /api/v1/rate-limits/check`, `POST /api/v1/sentinel/sweeps`, `POST /api/compression/dictionaries`, `POST /api/v1/private-source-profiles`, `POST /api/v1/press/automation/runs` | Secrets relay, catalog/pricing/costs, rate-limit governance, Sentinel persistence, compression dictionaries, private-source profiles, and PressForge automation |
| Proving-slice intake | `/api/v1/proving-slice` | `POST /api/v1/proving-slice/intake`, `GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}` | Governed artifact intake from DataForge Local: validate via forge-contract-core, persist, emit promotion_receipt. Three intake outcomes: `accepted`, `rejected`, `duplicate_reconciled`. |

## Authentication Posture

Credential requirements vary by router. The live mounted service currently uses these categories:

| Credential type | Examples |
|-----------------|----------|
| No auth | `/`, `/docs`, `/redoc`, `/openapi.json`, `/health`, `/health/render`, `/ready`, `/version`, HTML dashboards |
| Form or JSON login payload | `/auth/token`, `/api/auth/login`, `/api/auth/register` |
| JWT bearer | `/api/auth/me` and many user-facing CRUD surfaces |
| Admin token / emergency key / admin headers | `/admin/api-keys/*`, `/admin/token/*`, `/secrets/*` |
| Service API keys / scoped run credentials | BugCheck, event, policy, promotion, pricing, rate-limit, and integration surfaces as enforced by their handlers |

The repo contains a richer secure auth stack in `auth_secure_router.py`, but that router is
not mounted and therefore is not part of the live contract.

## Source-Present but Not Mounted by Default

These routers exist in `app/api/`, but the route audit confirmed they are absent from the
live app surface:

| Router module | Intended surface |
|---------------|------------------|
| `api_deployment_router` | deployment/load-balancer control |
| `auth_revocation_router` | token revocation and metrics |
| `auth_secure_router` | OAuth2/OIDC, MFA, and secure auth flows |
| `cache_replication_router` | cache failover and replication |
| `dlq_router` | dead-letter queue management |
| `rate_limit_router` | alternate/internal rate-limit management surface |
| `replication_router` | database replication/failover control |
| `tracing_router` | tracing and metrics ingestion/query |

## Contract Invariants

- Do not document a router as live unless it appears in `app.main`.
- Do not document `/metrics` as a supported root route until a mounted route actually exposes it.
- Preserve the distinction between HTML operator pages and JSON APIs.
- Keep prefixes exact: the current live service uses both legacy `/api/auth` style routes and newer `/api/v1/*` families.

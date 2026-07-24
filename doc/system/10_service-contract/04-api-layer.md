# §4 — API Layer

*Last updated: 2026-07-24*

The live API contract is whatever `app.main:app` mounts. A route audit against `app.routes`
on 2026-07-20 confirmed `45` mounted router objects plus app-level docs, HTML views, and
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
| AuthorForge boundary | `/api/projects`, `/api/v1/events/authorforge-analytics` | All `/api/projects` methods return `410`; `POST /api/v1/events/authorforge-analytics` accepts only `AuthorForgeAnalyticsEnvelope.v1` | AuthorForge content stays in its embedded DB; only minimized analytics can enter DataForge |
| Forge:SMITH | `/api/v1/smithy/planning`, `/api/v1/smithy/portfolio` | `POST /api/v1/smithy/planning/sessions`, `POST /api/v1/smithy/planning/sessions/{session_id}/start`, `POST /api/v1/smithy/portfolio/projects` | Planning session state, deliverables, and portfolio/evaluation records |
| Agents, runs, and BugCheck | `/api/v1/agents`, `/api/v1/forge-run`, `/api/v1/bugcheck`, `/api/v1/experience` | `POST /api/v1/agents`, `POST /api/v1/forge-run/persist`, `POST /api/v1/bugcheck/runs/{run_id}/findings`, `POST /api/v1/experience` | Agent registry, execution evidence, BugCheck persistence, experience store |
| Governance and runtime shaping | `/api/v1/runtime-promotion`, `/api/v1/policy-envelopes`, `/api/v1/policy-runs`, `/api/v1/policy-routing` | `POST /api/v1/runtime-promotion/receipts/local-failure-pattern`, `POST /api/v1/runtime-promotion/candidates/{candidate_id}/approve`, `PUT /api/v1/policy-envelopes/{policy_key}`, `POST /api/v1/policy-runs/ledger` | Promotion receipts, candidate review, deterministic policy envelopes, bandit state, reward records |
| Diligence and event persistence | `/api/diligence`, `/api/v1/events`, `/api/v1/telemetry`, `/ingest/tarcie` | `POST /api/diligence/reviews`, `POST /api/diligence/findings`, `POST /api/v1/events`, `GET /api/v1/telemetry/capabilities/forge-event-v1`, `POST /api/v1/telemetry/events`, `POST /ingest/tarcie` | Compliance review workflows, BuildGuard event ingest, canonical ForgeEvent.v1 capability and ingest, Tarcie friction ingest |
| Platform and operator data surfaces | `/secrets`, `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/batch`, `/api/v1/rate-limits`, `/api/v1/sentinel`, `/api/compression/dictionaries`, `/api/v1/press`, `/api/v1/private-source-profiles` | `POST /secrets/sync`, `POST /api/v1/rate-limits/check`, `POST /api/v1/sentinel/sweeps`, `POST /api/compression/dictionaries`, `POST /api/v1/private-source-profiles`, `POST /api/v1/press/automation/runs` | Secrets relay, catalog/pricing/costs, rate-limit governance, Sentinel persistence, compression dictionaries, private-source profiles, and PressForge automation |
| Proving-slice intake | `/api/v1/proving-slice` | `POST /api/v1/proving-slice/intake`, `GET /api/v1/proving-slice/receipts/by-artifact/{artifact_id}` | Governed artifact intake from DataForge Local: validate via forge-contract-core, persist, emit promotion_receipt. Three intake outcomes: `accepted`, `rejected`, `duplicate_reconciled`. |

## Authentication Posture

Credential requirements vary by router. The live mounted service currently uses these categories:

- `GET /api/v1/telemetry/capabilities/forge-event-v1` requires a DataForge API key
  and returns the authority-pinned sink contract plus the live writer state.
- `POST /api/v1/telemetry/events` requires a durable DataForge service key whose
  metadata includes `telemetry:write` and exactly matches the event's
  `service_name`, `environment`, and `tenant_ref`. The endpoint accepts exactly one
  `ForgeEvent.v1` producer projection. It rejects aliases, sink-owned fields, and
  unrecognized fields.
- Each producer projection is RFC 8785-canonicalized and must fit the
  authority-pinned 65,536-byte ceiling. The limit is not applied separately to
  `attributes` and `metrics`; an oversized event fails with
  `event_size_exceeded`.
- The request boundary pins
  `forge.telemetry.expected_errors.v1` at SHA-256
  `4dd477babf8c5c83bc02daf2c1951778d01294f307bb50a551f7160129669dbd`.
  Its exact invalid producer fixtures return `unsupported_sink_schema` or
  `event_schema_violation`; validation responses contain the stable code
  without payload values.
- A first insert returns `201`; an exact content-bound replay returns `200` with
  the original sink-owned `received_at`; reuse of an `event_id` with different
  canonical content returns `409 event_identity_conflict`.
- `DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED` defaults to `false`. Disabled writes
  return `503 telemetry_disabled`. No pre-v1 API alias, fallback, or dual-write is
  mounted.
- Enabled writes require the isolated `DATAFORGE_TELEMETRY_DATABASE_URL`.
  Runtime preflight requires a distinct non-superuser/non-`BYPASSRLS` login
  inheriting only the migration-owned `dataforge_telemetry_ingest` group role.
  The route has no fallback to the business pool.
- Each process admits at most 20 telemetry events/second with a 40-event burst
  before connection checkout. The telemetry pool is two connections with zero
  overflow and finite checkout/connect/statement/lock/transaction timeouts.

## DataForge Producer Contract

DataForge's search path is also a canonical producer. `app/telemetry_client.py`
submits `ForgeEvent.v1` through the immutable SDK pin in `requirements.txt`; it
does not write to telemetry tables directly.

- The only search event types are `search.completed` and `search.failed`.
- Attributes contain only `search_kind` (`semantic`, `keyword`, or `hybrid`).
- Metrics are an explicit allowlist of aggregate durations, result counts, and
  aggregate ranks/scores. Query text, tags, domain identifiers, limits,
  thresholds, raw exceptions, and exception types are excluded.
- Transport and validation failures are represented by stable code-only state;
  event values and credentials are never copied into health output or logs.
- Direct HTTP remains the default. Setting `DATAFORGE_TELEMETRY_SPOOL_PATH`
  explicitly enables the CP2 pilot: validated canonical bytes commit to a
  private 512-entry/32 MiB SQLite spool and one application-owned worker drains
  batches of four.
- Determinate availability failures receive at most five attempts with
  exponential 1–30 second backoff. Three consecutive downstream failures open
  a 15-second process-local circuit. Acknowledgement-loss and expired-inflight
  outcomes become `indeterminate` and are never retried automatically.
- Queue admission returns truthful `accepted_not_persisted` evidence. Only an
  inserted or exact-replay content-bound sink receipt deletes the row. Capacity
  overflow drops the newest event truthfully; corrupt rows quarantine without
  blocking healthy rows.
- `/health/telemetry` returns the capability identity, the 65,536-byte canonical
  event ceiling, delivery/queue counters, and non-secret async-worker state.

Production emission is intentionally unproved until the sink migration and
writer switch are complete and a dedicated key is bound to
`service_name=dataforge`, the exact environment, `tenant_ref=null`, and
`telemetry:write`.

`service_name=authorforge` is always rejected from the canonical telemetry
route, even for an otherwise correctly bound key. AuthorForge may use only its
dedicated strict, content-free `/api/v1/events/authorforge-analytics`
contract.

| Credential type | Examples |
|-----------------|----------|
| No auth | `/`, `/docs`, `/redoc`, `/openapi.json`, `/health`, `/health/render`, `/ready`, `/version`, HTML dashboards |
| Form or JSON login payload | `/auth/token`, `/api/auth/login`, `/api/auth/register` |
| JWT bearer | `/api/auth/me` and many user-facing CRUD surfaces |
| Admin token / emergency key / admin headers | `/admin/api-keys/*`, `/admin/token/*`, `/secrets/*` |
| Service API keys / scoped run credentials | BugCheck, event, policy, promotion, pricing, rate-limit, and integration surfaces as enforced by their handlers |

AuthorForge analytics requires a database-backed Bearer key whose metadata has
`service=authorforge` and a `scopes` list containing `analytics:write`. A general event key or
JWT is insufficient.

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
- Do not restore the removed telemetry batch route; ForgeEvent.v1 is the sole
  telemetry ingestion contract.
- Do not restore the pre-v1 direct-database producer or its example scripts.
- Never remount `projects_router` or `authorforge_v2_router`. The `/api/projects` tombstone must
  reject before body parsing, and rejected analytics payloads must not be echoed or logged.
- `AuthorForgeAnalyticsEnvelope.v1` is strict and closed: no arbitrary metadata, user content,
  raw logs, paths, identity, prompts/responses, attachments, or embeddings.

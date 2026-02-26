# §6 — API Layer

DataForge exposes 34 API routers covering 100+ endpoints. All endpoints return JSON. All write endpoints require authentication. The base URL is `http://localhost:8001` in development.

## Authentication Requirements

| Auth Type | Used For |
|-----------|---------|
| JWT Bearer token | User-facing endpoints, admin operations |
| API Key header | Service-to-service calls (NeuroForge, BugCheck, etc.) |
| run_token | BugCheck finding writes, enrichment writes |
| user_token | BugCheck lifecycle transitions (triage, approve, dismiss) |
| No auth | `/health`, `/`, `/metrics` |

## Router Index

### Infrastructure & Health

| Router | Prefix | Key Endpoints |
|--------|--------|--------------|
| Root | `/` | `GET /` — service info and version |
| Health | `/health` | `GET /health` — liveness probe; checks DB + Redis connectivity |
| Metrics | `/metrics` | `GET /metrics` — Prometheus metrics endpoint |

---

### Authentication & Authorization

#### `/auth` — Primary Auth Router
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | JWT login (username + password) |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/oauth/{provider}` | Initiate OAuth2 code flow (google, github, microsoft) |
| `GET` | `/auth/oauth/{provider}/callback` | OAuth2 callback + token exchange |
| `POST` | `/auth/refresh` | Refresh access token |

#### `/auth/mfa` — Multi-Factor Authentication
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/mfa/setup` | Initialize TOTP (returns QR code seed) |
| `POST` | `/auth/mfa/verify` | Verify TOTP code during login |
| `GET` | `/auth/mfa/backup-codes` | Issue 10 backup codes |
| `POST` | `/auth/mfa/backup-codes/use` | Consume a backup code |

#### `/api/v1/auth-secure` — Encrypted Auth
Encrypted variants of auth endpoints for high-security contexts. Request and response bodies use field-level encryption.

#### `/admin/api-keys` — Service API Key Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/api-keys` | Create new service API key |
| `GET` | `/admin/api-keys` | List all active keys |
| `DELETE` | `/admin/api-keys/{key_id}` | Revoke a key |

#### `/admin/token` — Token Operations
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/token` | Issue admin token |
| `POST` | `/admin/token/rotate` | Rotate signing key + invalidate old tokens |

---

### Core Data Access

#### `POST /api/search` — Hybrid Search
Primary search endpoint. Accepts query text, optional domain filter, limit, and similarity threshold. Returns ranked chunks with document metadata.

**Request:**
```json
{
  "query": "string",
  "domain_id": "uuid | null",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

**Response:** Array of `SearchResult` objects with chunk text, document metadata, similarity score, and BM25 rank.

#### `GET /api/search/stats` — Search Statistics
Returns aggregate search usage: total queries, average latency, top domains, cache hit rates.

#### `/admin/documents` — Document Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/documents` | Create document + trigger auto-chunk + embed |
| `GET` | `/admin/documents` | List documents (paginated, filterable by domain/tag) |
| `GET` | `/admin/documents/{id}` | Get document with chunk count |
| `PATCH` | `/admin/documents/{id}` | Update document + re-chunk if content changed |
| `DELETE` | `/admin/documents/{id}` | Delete document + cascade delete chunks |

#### `/admin/domains` — Domain Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/domains` | Create domain |
| `GET` | `/admin/domains` | List all domains |
| `GET` | `/admin/domains/{id}` | Get domain with document count |
| `PATCH` | `/admin/domains/{id}` | Update domain metadata |
| `DELETE` | `/admin/domains/{id}` | Delete domain (fails if documents exist) |

#### `/admin/tags` — Tag Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/tags` | List all tags |
| `POST` | `/admin/tags` | Create tag |

---

### Service Integration Routers

#### `/api/neuroforge` — NeuroForge Integration
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/neuroforge/runs` | Log LLM run |
| `GET` | `/api/neuroforge/runs/{run_id}` | Get run record |
| `POST` | `/api/neuroforge/runs/{run_id}/results` | Log model results |
| `POST` | `/api/neuroforge/inferences` | Log inference record |
| `GET` | `/api/neuroforge/performance` | Query model performance metrics |
| `GET` | `/api/neuroforge/context` | Retrieve relevant context for a query |
| `POST` | `/api/neuroforge/routing-decisions` | Log routing decision record |
| `GET` | `/api/neuroforge/routing-decisions` | Query routing decisions (task_type, provider, tier filters) |

#### `/api/vibeforge` — VibeForge Integration
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/vibeforge/projects` | Create project |
| `POST` | `/api/vibeforge/sessions` | Create session |
| `GET` | `/api/vibeforge/sessions/{session_id}` | Get session |
| `POST` | `/api/vibeforge/stack-outcomes` | Record stack analysis outcome |
| `POST` | `/api/vibeforge/code-analysis` | Store code analysis result |

#### `/api/projects` — AuthorForge V2
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects` | Create book project |
| `GET` | `/api/projects/{project_id}` | Get project with chapter list |
| `POST` | `/api/projects/{project_id}/chapters` | Create chapter |
| `POST` | `/api/projects/{project_id}/chapters/{chapter_id}/scenes` | Create scene |
| `POST` | `/api/projects/{project_id}/manuscripts` | Compile manuscript |
| `POST` | `/api/projects/{project_id}/characters` | Create character |
| `POST` | `/api/projects/{project_id}/arcs` | Create story arc |
| `POST` | `/api/projects/{project_id}/locations` | Create location |
| `GET` | `/api/projects/{project_id}/knowledge-graph` | Get knowledge graph |

#### `/api/bugcheck` — BugCheck Agent Integration
Full details in §8. Key endpoints:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/bugcheck/runs` | admin token | Create run record (ForgeCommand only) |
| `POST` | `/api/bugcheck/runs/{run_id}/findings` | run_token | Ingest finding |
| `GET` | `/api/bugcheck/runs/{run_id}/findings` | JWT | List findings for run |
| `POST` | `/api/bugcheck/runs/{run_id}/progress` | run_token | Post progress event |
| `POST` | `/api/bugcheck/findings/{finding_id}/lifecycle` | user_token | Transition lifecycle state |
| `POST` | `/api/bugcheck/findings/{finding_id}/enrichments` | run_token | Store enrichment artifact |
| `POST` | `/api/bugcheck/runs/{run_id}/finalize` | admin token | Finalize run (ForgeCommand only) |

#### `/api/agents-registry` — Agent Registry
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agents-registry` | Register agent definition |
| `GET` | `/api/agents-registry` | List all registered agents |
| `GET` | `/api/agents-registry/{agent_id}` | Get agent config |
| `PATCH` | `/api/agents-registry/{agent_id}` | Update agent config |

#### `/forge-runs` — Execution Index
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/forge-runs` | Create execution index record |
| `GET` | `/forge-runs/{run_id}` | Get run status (fast, denormalized) |
| `PATCH` | `/forge-runs/{run_id}` | Update status/outcome |
| `POST` | `/forge-runs/{run_id}/evidence` | Store full evidence blob (JSONB) |
| `GET` | `/forge-runs/{run_id}/evidence` | Retrieve evidence blob |

#### `/api/v1/smithy/planning` — SMITH Planning
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/smithy/planning/sessions` | Create planning session |
| `GET` | `/api/v1/smithy/planning/sessions/{id}` | Get session |
| `PATCH` | `/api/v1/smithy/planning/sessions/{id}` | Update session |

#### `/api/v1/smithy/portfolio` — Portfolio Tracking
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/smithy/portfolio/projects` | Create portfolio project |
| `GET` | `/api/v1/smithy/portfolio/projects` | List projects |
| `POST` | `/api/v1/smithy/portfolio/evaluations` | Store evaluation snapshot |

#### `/api/v1/learning` — Learning Metrics
Stores model performance metrics and surfaces improvement recommendations for NeuroForge.

#### `/api/teams` — Team Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/teams` | Create team |
| `GET` | `/api/teams/{team_id}` | Get team |
| `POST` | `/api/teams/{team_id}/members` | Invite member |
| `PATCH` | `/api/teams/{team_id}/members/{user_id}` | Update member role |
| `DELETE` | `/api/teams/{team_id}/members/{user_id}` | Remove member |
| `GET` | `/api/teams/{team_id}/insights` | Get team insights aggregate |

#### `/api/events` — Immutable Audit Log
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/events` | Append event (HMAC-signed) |
| `GET` | `/api/events` | Query events (filterable, read-only) |

Events are append-only. There is no update or delete endpoint. The HMAC-SHA256 signature on each event enables tamper detection.

#### `/api/v1/model-catalog` — Multi-Provider Model Catalog

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/model-catalog` | List all models (filterable by tier, provider) |
| `GET` | `/api/v1/model-catalog/{model_id}` | Get model details with current pricing |
| `POST` | `/api/v1/model-catalog` | Register a new model |
| `PUT` | `/api/v1/model-catalog/{model_id}` | Update model metadata |
| `DELETE` | `/api/v1/model-catalog/{model_id}` | Remove model from catalog |

#### `/api/v1/pricing` — Pricing Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/pricing/snapshots` | List pricing snapshots (filterable by model, date range) |
| `POST` | `/api/v1/pricing/snapshots` | Store a pricing snapshot |
| `GET` | `/api/v1/pricing/alerts` | List pricing alerts (filterable by status, type) |
| `POST` | `/api/v1/pricing/alerts` | Create a pricing alert |
| `PATCH` | `/api/v1/pricing/alerts/{alert_id}` | Acknowledge or update an alert |
| `GET` | `/api/v1/pricing/runs` | List pricing monitor runs |
| `POST` | `/api/v1/pricing/runs` | Record a pricing monitor run |
| `PATCH` | `/api/v1/pricing/runs/{run_id}` | Update run status |

#### `/api/v1/cost-ledger` — Cost Tracking

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/cost-ledger` | Record a cost entry (per-inference) |
| `GET` | `/api/v1/cost-ledger` | Query cost entries (filterable by run, model, provider, date range) |
| `GET` | `/api/v1/cost-ledger/aggregations` | Aggregated cost data (by provider, by model, by period) |

#### `/api/v1/sentinel` — Sentinel Health Sweeps & Healing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sentinel/sweeps` | Create a sweep record |
| `GET` | `/api/v1/sentinel/sweeps` | List sweeps (filterable by type, status) |
| `GET` | `/api/v1/sentinel/sweeps/{sweep_id}` | Get sweep details with dimension results |
| `PATCH` | `/api/v1/sentinel/sweeps/{sweep_id}` | Update sweep status/findings |
| `POST` | `/api/v1/sentinel/healing` | Record a healing event |
| `GET` | `/api/v1/sentinel/healing` | List healing events (filterable by tier, outcome) |
| `GET` | `/api/v1/sentinel/healing/{event_id}` | Get healing event details |
| `PATCH` | `/api/v1/sentinel/healing/{event_id}` | Update healing event status |

#### `/api/v1/press` — PressForge Automation Tables

CRUD endpoints for 11 automation tables. All follow standard DataForge patterns (pagination, filtering, FK cascade).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/press/automation-jobs` | List automation job definitions |
| `GET` | `/api/v1/press/automation-jobs/{id}` | Get job definition |
| `POST` | `/api/v1/press/automation-jobs` | Create job definition |
| `PATCH` | `/api/v1/press/automation-jobs/{id}` | Update job definition |
| `GET` | `/api/v1/press/automation-runs` | List execution runs (filterable by job_key, status) |
| `GET` | `/api/v1/press/automation-runs/{id}` | Get run details |
| `POST` | `/api/v1/press/automation-runs` | Create run record |
| `PATCH` | `/api/v1/press/automation-runs/{id}` | Update run status/summary |
| `GET` | `/api/v1/press/automation-alerts` | List alerts (filterable by severity, job_key) |
| `GET` | `/api/v1/press/automation-alerts/{id}` | Get alert details |
| `POST` | `/api/v1/press/automation-alerts` | Create alert |
| `PATCH` | `/api/v1/press/automation-alerts/{id}` | Dismiss alert |
| `GET` | `/api/v1/press/automation-overrides` | List active overrides |
| `POST` | `/api/v1/press/automation-overrides` | Create override (TTL-enforced, max 7 days) |
| `GET` | `/api/v1/press/agent-logs` | List agent logs (filterable by job_key, run_id) |
| `GET` | `/api/v1/press/agent-logs/{id}` | Get agent log entry |
| `POST` | `/api/v1/press/agent-logs` | Append agent log (**no UPDATE/DELETE — append-only**) |
| `GET` | `/api/v1/press/provider-configs` | List provider configurations |
| `POST` | `/api/v1/press/provider-configs` | Create provider config |
| `PATCH` | `/api/v1/press/provider-configs/{id}` | Update provider config |
| `GET` | `/api/v1/press/geo-probes` | List GEO probes (filterable by campaign_id, provider) |
| `POST` | `/api/v1/press/geo-probes` | Record probe result |
| `GET` | `/api/v1/press/geo-probe-templates` | List probe templates |
| `POST` | `/api/v1/press/geo-probe-templates` | Create template |
| `PATCH` | `/api/v1/press/geo-probe-templates/{id}` | Update template |
| `DELETE` | `/api/v1/press/geo-probe-templates/{id}` | Delete template |
| `GET` | `/api/v1/press/social-draftsets` | List social draftsets |
| `POST` | `/api/v1/press/social-draftsets` | Create draftset |
| `PATCH` | `/api/v1/press/social-draftsets/{id}` | Update draftset status |
| `GET` | `/api/v1/press/prompt-packs` | List prompt packs |
| `POST` | `/api/v1/press/prompt-packs` | Create prompt pack |
| `PATCH` | `/api/v1/press/prompt-packs/{id}` | Update prompt pack |
| `GET` | `/api/v1/press/campaign-outcomes` | List campaign outcomes |
| `POST` | `/api/v1/press/campaign-outcomes` | Record campaign outcome |

Full schema details in [§12 PressForge Automation Schema](12-pressforge-automation-schema.md).

#### `/api/v1/private-source-profiles` — Private Source Ingestion Profiles (PSIM)

CRUD endpoints for operator-curated private source configurations. Each profile defines a crawl scope (base_url + allowed_paths), authentication method, and quality gate overrides. Credentials live in the OS keyring via ForgeCommand — never in DataForge.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/private-source-profiles` | Create profile (201) |
| `GET` | `/api/v1/private-source-profiles/{id}` | Get profile by ID |
| `GET` | `/api/v1/private-source-profiles?workspace_id=...` | List profiles (workspace-scoped, paginated) |
| `PUT` | `/api/v1/private-source-profiles/{id}` | Update profile (partial) |
| `DELETE` | `/api/v1/private-source-profiles/{id}` | Delete profile (204) |

**Query parameters (list):** `workspace_id` (required), `source_type`, `active_only` (default true), `limit`, `offset`

**Duplicate prevention:** Unique constraint on `(workspace_id, name)` — returns 409 on conflict.

---

### Infrastructure Routers

| Router | Prefix | Purpose |
|--------|--------|---------|
| Tracing | `/api/tracing` | OpenTelemetry span ingestion |
| Deployment | `/api-deployment` | Load balancer, instance health, graceful drain |
| Cache | `/cache` | Redis cache sync operations |
| Cache Replication | `/cache-replication` | Cache failover management |
| Secrets | `/secrets` | LLM API key vault (synced from ForgeCommand) |
| Diligence | `/api/diligence` | Security/compliance assessment |
| Rate Limiting | `/rate-limit` | Distributed rate limit management |
| FPVS | `/fpvs` | FPVS Phase 1 endpoints |
| Tarcie | `/tarcie` | DX friction event capture |
| DLQ | `/dlq` | Dead letter queue inspection + replay |

#### `/admin-ui` — Admin Interface
`GET /admin-ui` serves the Jinja2-rendered admin HTML template. Provides a browser-based interface for document management, search testing, and domain administration. No JavaScript framework required.

# §8 — Ecosystem Integration Contracts

This section defines the integration contract between DataForge and each Forge service. Each service has exactly defined authorization scope, write permissions, and prohibited operations.

## Integration Principles

1. **Every service authenticates.** No endpoint accepts unauthenticated writes.
2. **Scope is enforced, not suggested.** A service attempting to write outside its authorized scope receives 403 Forbidden.
3. **DataForge is the record.** Services may cache reads locally for performance but must never treat their cache as authoritative.
4. **Fail loudly.** When DataForge is unavailable, services must fail, not degrade silently.

---

## BugCheck Agent

BugCheck is the most tightly governed integration. The access control matrix is enforced at the API layer.

### Access Control Matrix

| Component | Authorized Writes | Auth Token Required |
|-----------|------------------|-------------------|
| ForgeCommand | run records, lifecycle transitions, run finalization | admin token |
| BugCheck Agent | findings, progress events, check telemetry | run_token (scoped) |
| XAI (Grok) | enrichment artifacts only | run_token |
| MAID (Claude) | enrichment artifacts only | run_token |
| VibeForge | user decisions (lifecycle transitions) only | user_token |

### run_token Contract

```
run_token = JWT signed with SECRET_KEY
Claims:
  - run_id: UUID (exact match required)
  - targets: list[str] (exact match required)
  - mode: "quick" | "standard" | "deep"
  - scope: "changed_files" | "package" | "full_repo"
  - commit_sha: str (exact match required)
  - nonce: str (replay protection, single-use)
  - iat: int
  - exp: int (iat + 1800 to iat + 3600)
```

A run_token is bound to its run. A BugCheck agent with a valid run_token for run A cannot write findings to run B. The nonce prevents replay attacks — each token is single-use for write operations.

### Finding Ingestion Flow

```
BugCheck Agent
    │
    ├── POST /api/bugcheck/runs/{run_id}/findings
    │   Headers: Authorization: Bearer {run_token}
    │   Body: FindingCreate schema
    │   │
    │   └── DataForge validates:
    │       1. run_token signature + expiry
    │       2. run_token.run_id == path run_id
    │       3. Run status is "running" (not finalized)
    │       4. Finding fingerprint uniqueness
    │       5. Severity + category enum membership
    │       │
    │       └── Writes BugCheckFindingModel
    │           lifecycle_state = "NEW"
    │           autofix_available = False (updated by enrichment)
    │           created_at = utcnow()
```

### Lifecycle Transition Flow

```
VibeForge (user decision)
    │
    ├── POST /api/bugcheck/findings/{finding_id}/lifecycle
    │   Headers: Authorization: Bearer {user_token}
    │   Body: { "to_state": "TRIAGED", "reason": "..." }
    │   │
    │   └── DataForge validates:
    │       1. user_token signature + expiry
    │       2. Transition is valid (see §9 state machine)
    │       3. Finding is not in terminal state
    │       │
    │       └── Writes BugCheckLifecycleEventModel (append-only)
    │           Updates BugCheckFindingModel.lifecycle_state
```

**Invariants:**
- BugCheck Agent NEVER writes lifecycle transitions.
- VibeForge NEVER writes findings.
- After a run is finalized (status = "finalized"), POST to findings returns 409.

### Severity Levels

| Level | Name | Gating Behavior |
|-------|------|----------------|
| S0 | Release Blocker | Blocks all merges and deployments |
| S1 | High | Blocks PR merge |
| S2 | Medium | Warning only, no block |
| S3 | Low | Informational |
| S4 | Info | Advisory only |

---

## NeuroForge

NeuroForge logs all LLM run state to DataForge. It never maintains its own authoritative run history.

### Integration Points

| Operation | DataForge Endpoint | Writes |
|-----------|-------------------|--------|
| Log run start | `POST /api/neuroforge/runs` | NeuroForgeRun record |
| Log model results | `POST /api/neuroforge/runs/{run_id}/results` | ModelResult records |
| Log performance | `POST /api/neuroforge/runs/{run_id}/performance` | ModelPerformance record |
| Log inference | `POST /api/neuroforge/inferences` | Inference record |
| Retrieve context | `GET /api/neuroforge/context?query=...` | Read-only |

Context retrieval uses the hybrid search engine to find relevant document chunks for the query. NeuroForge uses this to build RAG context before LLM inference.

**Auth:** NeuroForge uses service API keys. No run_token scoping applies.

---

## VibeForge

VibeForge persists all project-level state and code analysis results.

### Integration Points

| Operation | DataForge Endpoint | Writes |
|-----------|-------------------|--------|
| Create project | `POST /api/vibeforge/projects` | VibeForgeProject |
| Create session | `POST /api/vibeforge/sessions` | ProjectSession |
| Log stack outcome | `POST /api/vibeforge/stack-outcomes` | StackOutcome |
| Store code analysis | `POST /api/vibeforge/code-analysis` | Analysis result |
| BugCheck decisions | `POST /api/bugcheck/findings/{id}/lifecycle` | Lifecycle transition only |

**Auth:** VibeForge uses service API keys for project/session writes. For BugCheck lifecycle transitions, it uses a user_token issued on behalf of the authenticated user.

---

## AuthorForge V2

AuthorForge is the most content-intensive integration. All narrative content — including manuscripts that may exceed 100k tokens — is persisted to DataForge.

### Integration Points

| Resource | Endpoint Pattern | Notes |
|----------|-----------------|-------|
| Projects | `/api/projects` | Book-level metadata |
| Chapters | `/api/projects/{id}/chapters` | Ordered chapter list |
| Scenes | `/api/projects/{id}/chapters/{id}/scenes` | Scene text + metadata |
| Characters | `/api/projects/{id}/characters` | Character definitions |
| Story Arcs | `/api/projects/{id}/arcs` | Narrative arc tracking |
| Locations | `/api/projects/{id}/locations` | Setting definitions |
| Knowledge Graph | `/api/projects/{id}/knowledge-graph` | Relationship graph |
| Manuscripts | `/api/projects/{id}/manuscripts` | Compiled full manuscript |

**Chunking:** Scene and chapter content is automatically chunked and embedded on write. This enables semantic search across all narrative content within a project.

**Auth:** Service API keys.

---

## ForgeAgents

ForgeAgents (the agent runtime) uses DataForge for agent configuration persistence and execution record keeping.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Register agent | `POST /api/agents-registry` |
| Get agent config | `GET /api/agents-registry/{agent_id}` |
| Log execution | `POST /forge-runs` |
| Update execution status | `PATCH /forge-runs/{run_id}` |
| Store evidence | `POST /forge-runs/{run_id}/evidence` |

**Auth:** Admin token for registry writes. Service API key for run logging.

---

## ForgeCommand

ForgeCommand is the orchestration plane. It has elevated privileges:

### Exclusive Operations (admin token only)

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create BugCheck run | `POST /api/bugcheck/runs` |
| Finalize BugCheck run | `POST /api/bugcheck/runs/{id}/finalize` |
| Write lifecycle transitions | (via ForgeCommand authority) |
| Token rotation | `POST /admin/token/rotate` |
| API key management | `POST /admin/api-keys` |
| Secrets sync | `POST /secrets` (sync from ForgeCommand vault) |

**ForgeCommand is the only component authorized to finalize runs.** BugCheck agent cannot self-finalize.

---

## Forge:SMITH

SMITH uses DataForge for planning sessions, portfolio tracking, and evaluation snapshots.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create planning session | `POST /api/v1/smithy/planning/sessions` |
| Update session | `PATCH /api/v1/smithy/planning/sessions/{id}` |
| Create portfolio project | `POST /api/v1/smithy/portfolio/projects` |
| Store evaluation snapshot | `POST /api/v1/smithy/portfolio/evaluations` |
| Log governance events | `POST /api/events` |

Governance events written by SMITH to the audit log are HMAC-signed and immutable. SMITH reads run state from `/forge-runs` for its authority layer operations.

**Auth:** Service API key. Governance event writes use a dedicated SMITH service key with elevated signing privileges.

---

## Teams

The Teams subsystem is service-agnostic; any Forge service can query team membership and insights.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create team | `POST /api/teams` |
| Add member | `POST /api/teams/{id}/members` |
| Query insights | `GET /api/teams/{id}/insights` |
| Update member role | `PATCH /api/teams/{id}/members/{user_id}` |

---

## Sentinel Agent

The Sentinel Agent monitors ecosystem health and performs autonomous healing. It uses DataForge to persist sweep results and healing event records.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Create sweep | `POST /api/v1/sentinel/sweeps` |
| Update sweep | `PATCH /api/v1/sentinel/sweeps/{sweep_id}` |
| Record healing | `POST /api/v1/sentinel/healing` |
| Update healing | `PATCH /api/v1/sentinel/healing/{event_id}` |
| Query sweep history | `GET /api/v1/sentinel/sweeps` |

**Auth:** Service API key. Healing events at Tier B require ForgeCommand approval metadata.

**Sweep Types:**
- **Light sweep** (D1+D3+D6): Runs every 5 minutes, <10s execution
- **Deep sweep** (D1-D6): On-demand or triggered by anomaly, 30-60s execution

---

## Pricing Monitor Agent

The Pricing Monitor Agent periodically scrapes provider pricing pages and compares against stored catalog data.

### Integration Points

| Operation | DataForge Endpoint |
|-----------|-------------------|
| Fetch model catalog | `GET /api/v1/model-catalog` |
| Store pricing snapshot | `POST /api/v1/pricing/snapshots` |
| Create pricing alert | `POST /api/v1/pricing/alerts` |
| Record monitor run | `POST /api/v1/pricing/runs` |
| Update run status | `PATCH /api/v1/pricing/runs/{run_id}` |

**Auth:** Service API key. Alert types: PRICE_INCREASE, PRICE_DECREASE, NEW_MODEL, MODEL_DEPRECATED, CAPABILITY_CHANGE.

---

## Common Integration Patterns

### Health Check Before Run Start

Every service that starts a long-running operation MUST verify DataForge availability first:

```python
async def check_dataforge_health() -> bool:
    try:
        response = await http_client.get(
            "http://localhost:8001/ready",
            timeout=5.0
        )
        return response.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False

if not await check_dataforge_health():
    raise DataForgeUnavailableError("DataForge readiness check failed; run aborted")
```

### Structured Error Handling

```python
class DataForgeError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DataForge returned {status_code}: {detail}")

# In service code:
response = await dataforge_client.post(...)
if response.status_code == 409:
    raise DataForgeError(409, response.json()["detail"])
elif response.status_code >= 500:
    raise DataForgeUnavailableError(f"DataForge server error: {response.status_code}")
```

### Audit Event Pattern

All significant cross-service operations should produce an audit event:

```python
await dataforge_client.post(
    "/api/events",
    json={
        "event_type": "bugcheck.finding.created",
        "actor_id": run_id,
        "resource_type": "bugcheck_finding",
        "resource_id": str(finding_id),
        "payload": {"severity": "S1", "category": "security"}
    }
)
```

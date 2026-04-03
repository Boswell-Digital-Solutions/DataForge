# §8 — Ecosystem Integration Contracts

This section describes the current mounted integration boundary, not every historical router
module present in the repo.

## Integration Principles

1. **Every durable-write caller authenticates.** Unauthenticated writes are not part of the contract.
2. **Scope is enforced, not implied.** Run-scoped and admin-scoped flows remain explicit.
3. **DataForge is the record.** Downstream services may cache, but they do not own truth.
4. **Unavailable means unavailable.** Readiness failure should block authority-dependent work.

## Current Integration Map

| Service or function | Current mounted prefixes | Primary responsibility in DataForge |
|---------------------|--------------------------|-------------------------------------|
| NeuroForge | `/api/neuroforge`, `/api/v1/runs`, `/api/v1/learning` | Inference persistence, routing decisions, execution logs, learning feedback |
| VibeForge | `/api/vibeforge`, `/api/teams` | Project/session/outcome persistence plus team insights |
| AuthorForge | `/api/projects` | Project, chapter, scene, manuscript, map, asset, collection, and story structure persistence |
| ForgeAgents | `/api/v1/agents`, `/api/v1/forge-run`, `/api/v1/experience` | Agent registry, run evidence, execution history, experience store |
| BugCheck | `/api/v1/bugcheck` | Run creation, finding ingest, enrichments, lifecycle events, progress |
| Forge:SMITH | `/api/v1/smithy/planning`, `/api/v1/smithy/portfolio` | Planning session state, deliverables, portfolio, evaluation evidence |
| ForgeCommand / operator control | `/admin/api-keys`, `/admin/token`, `/secrets`, governance/promotion routes | Key rotation, secret sync, runtime governance, operator-controlled approvals |
| Sentinel | `/api/v1/sentinel` | Persist sweep records and healing-event records |
| PressForge | `/api/v1/press` | Automation jobs, runs, logs, overrides, media workflows, campaign state |
| Pricing / provider governance | `/api/v1/models`, `/api/v1/pricing`, `/api/v1/costs`, `/api/v1/batch`, `/api/v1/rate-limits` | Catalog, pricing snapshots, cost ledgers, batch queue, rate-limit state |
| Policy and runtime shaping | `/api/v1/policy-envelopes`, `/api/v1/policy-runs`, `/api/v1/policy-routing`, `/api/v1/runtime-promotion` | Deterministic policy envelopes, ledgers, reward records, runtime-promotion receipts/candidates |
| Diligence / events / Tarcie | `/api/diligence`, `/api/v1/events`, `/ingest/tarcie` | Compliance review records, append-only events, friction ingest |
| Private source ingestion | `/api/v1/private-source-profiles` | Operator-curated source profile persistence |

## BugCheck Contract

BugCheck remains the most tightly governed integration surface.

| Operation | Current mounted endpoint shape | Expected authority |
|-----------|--------------------------------|--------------------|
| Create run | `POST /api/v1/bugcheck/runs` | operator/admin-controlled |
| Ingest finding | `POST /api/v1/bugcheck/runs/{run_id}/findings` | run-scoped |
| Batch ingest findings | `POST /api/v1/bugcheck/runs/{run_id}/findings/batch` | run-scoped |
| Append progress | `POST /api/v1/bugcheck/runs/{run_id}/progress` | run-scoped |
| Append enrichment | `POST /api/v1/bugcheck/findings/{finding_id}/enrichments` | run-scoped |
| Append lifecycle event | `POST /api/v1/bugcheck/findings/{finding_id}/lifecycle` | user/operator-scoped |

Invariants:

- BugCheck findings remain run-scoped.
- Lifecycle events remain separate from finding creation.
- Finalized or otherwise closed run-state enforcement stays fail-closed at the API layer.

## NeuroForge and Learning

NeuroForge writes inference and routing evidence through `/api/neuroforge/*`, while broader
execution and learning records land under `/api/v1/runs` and `/api/v1/learning`.

Representative mounted routes:

- `POST /api/neuroforge/inferences`
- `POST /api/neuroforge/routing-decisions`
- `POST /api/v1/runs`
- `GET /api/v1/learning/model-performance`
- `GET /api/v1/learning/recommendations/*`

## Authoring, Planning, and Portfolio State

Mounted authoring and planning surfaces now span:

- `POST /api/projects` and the broader `/api/projects/{project_id}/...` family
- `POST /api/vibeforge/projects` and `/api/vibeforge/sessions`
- `POST /api/v1/smithy/planning/sessions`
- `POST /api/v1/smithy/portfolio/projects`

These surfaces are no longer "future integrations"; they are part of the live mounted app.

## Operator Control and Governance

ForgeCommand and other operator-controlled flows interact with DataForge through mounted
control surfaces, including:

- `POST /admin/api-keys/generate`
- `POST /admin/token/rotate`
- `POST /secrets/sync`
- `POST /api/v1/runtime-promotion/candidates/{candidate_id}/approve`
- `PUT /api/v1/policy-envelopes/{policy_key}`
- `POST /api/v1/policy-runs/ledger`

DataForge persists governance evidence and operator decisions; it does not replace the
external orchestration/control surface that decides when those endpoints are called.

## Sentinel Contract

Sentinel currently uses DataForge as a persistence boundary for sweeps and healing-event
records. The mounted DataForge router does **not** perform autonomous healing itself.

Representative mounted routes:

- `POST /api/v1/sentinel/sweeps`
- `PATCH /api/v1/sentinel/sweeps/{sweep_id}`
- `POST /api/v1/sentinel/healing`
- `PATCH /api/v1/sentinel/healing/{event_id}`

## Common Integration Pattern

Clients that depend on DataForge authority should check readiness first:

```python
async def check_dataforge_ready(http_client) -> bool:
    try:
        response = await http_client.get("http://localhost:8001/ready", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False
```

For append-only or governed writes, callers should treat `409` and `403` as contract
responses, not transient transport failures.

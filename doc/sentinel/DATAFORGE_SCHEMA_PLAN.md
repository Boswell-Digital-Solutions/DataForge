# DataForge Schema Plan -- Sentinel Agent

## 1. Overview

DataForge provides persistent storage for the Sentinel health monitoring and self-healing system. Two tables store sweep records and healing events. All Sentinel Agent state is written here as the single source of truth.

**Source files:**

| File | Purpose |
|------|---------|
| `app/models/sentinel_models.py` | SQLAlchemy ORM models |
| `app/models/sentinel_schemas.py` | Pydantic request/response schemas |
| `app/api/sentinel_router.py` | FastAPI CRUD router |

---

## 2. Enums

### SweepType

| Value | Description |
|-------|-------------|
| `light` | D1 + D3 + D6 dimensions, < 10 seconds |
| `deep` | D1--D6 all dimensions, 30--60 seconds |

### SweepStatus

| Value | Description |
|-------|-------------|
| `running` | Sweep in progress |
| `completed` | Sweep finished successfully |
| `failed` | Sweep encountered an error |

### OverallStatus

| Value | Description |
|-------|-------------|
| `healthy` | All checked dimensions passed |
| `degraded` | One or more non-critical dimensions failed |
| `critical` | D1 (liveness) or D6 (token authority) failed |
| `unknown` | Status not yet determined (default) |

### SweepTrigger

| Value | Description |
|-------|-------------|
| `scheduled` | Periodic automated sweep |
| `manual` | Operator-initiated sweep |
| `anomaly` | Triggered by anomaly detection |

### HealingTier

| Value | Description |
|-------|-------------|
| `A` | Autonomous -- executes without approval |
| `B` | Supervised -- requires ForgeCommand approval |
| `C` | Escalation -- requires human intervention |

### HealingOutcome

| Value | Description |
|-------|-------------|
| `pending` | Action created, not yet executed |
| `success` | Action executed and verified |
| `failure` | Action executed but failed or verification failed |
| `escalated` | Action escalated to higher tier |
| `skipped` | Preconditions not met, action skipped |

---

## 3. Tables

### sentinel_sweeps

A health sweep (diagnostic run) across ecosystem services.

| Column | Type | Nullable | Default | Constraint | Description |
|--------|------|----------|---------|------------|-------------|
| `id` | `UUID` | No | `uuid4()` | **PK** | Sweep identifier |
| `sweep_type` | `VARCHAR(20)` | No | -- | `ck_sentinel_sweep_type` | `light` or `deep` |
| `status` | `VARCHAR(20)` | No | `'running'` | `ck_sentinel_sweep_status` | `running`, `completed`, `failed` |
| `dimensions_checked` | `JSONB` | No | `[]` | -- | List of dimension IDs checked (e.g., `["D1","D3","D6"]`) |
| `findings` | `JSONB` | No | `[]` | -- | Array of `DimensionResult` objects |
| `overall_status` | `VARCHAR(20)` | No | `'unknown'` | `ck_sentinel_sweep_overall` | `healthy`, `degraded`, `critical`, `unknown` |
| `trigger` | `VARCHAR(30)` | No | `'scheduled'` | -- | `scheduled`, `manual`, `anomaly` |
| `duration_ms` | `INTEGER` | Yes | `NULL` | -- | Sweep wall-clock duration in milliseconds |
| `error` | `TEXT` | Yes | `NULL` | -- | Error message if sweep failed |
| `started_at` | `DATETIME` | No | `utcnow()` | -- | Sweep start timestamp |
| `completed_at` | `DATETIME` | Yes | `NULL` | -- | Sweep completion timestamp |

**Relationships:**
- `healing_events` -- one-to-many to `sentinel_healing_events` (`cascade="all, delete-orphan"`)

### sentinel_healing_events

A healing action taken (or escalated) by Sentinel, always linked to a parent sweep.

| Column | Type | Nullable | Default | Constraint | Description |
|--------|------|----------|---------|------------|-------------|
| `id` | `UUID` | No | `uuid4()` | **PK** | Healing event identifier |
| `sweep_id` | `UUID` | No | -- | **FK** `sentinel_sweeps.id` (ON DELETE CASCADE), **indexed** | Parent sweep |
| `playbook` | `VARCHAR(60)` | No | -- | -- | Playbook name (e.g., `cache_flush`, `breaker_reset`, `job_retry`) |
| `tier` | `VARCHAR(1)` | No | -- | `ck_sentinel_healing_tier` | `A`, `B`, or `C` |
| `action` | `VARCHAR(200)` | No | -- | -- | Human-readable action description |
| `target_service` | `VARCHAR(60)` | Yes | `NULL` | -- | Service affected by the action |
| `outcome` | `VARCHAR(20)` | No | `'pending'` | `ck_sentinel_healing_outcome` | `pending`, `success`, `failure`, `escalated`, `skipped` |
| `governed` | `BOOLEAN` | No | `False` | -- | Whether governance approval was required |
| `approval_id` | `VARCHAR(100)` | Yes | `NULL` | -- | Governance event ID if governed |
| `details` | `JSONB` | No | `{}` | -- | Structured details (tool results, errors, etc.) |
| `duration_ms` | `INTEGER` | Yes | `NULL` | -- | Action wall-clock duration in milliseconds |
| `created_at` | `DATETIME` | No | `utcnow()` | -- | Event creation timestamp |
| `completed_at` | `DATETIME` | Yes | `NULL` | -- | Event completion timestamp |

**Relationships:**
- `sweep` -- many-to-one back to `sentinel_sweeps`

---

## 4. Check Constraints

| Name | Table | Expression |
|------|-------|------------|
| `ck_sentinel_sweep_type` | `sentinel_sweeps` | `sweep_type IN ('light', 'deep')` |
| `ck_sentinel_sweep_status` | `sentinel_sweeps` | `status IN ('running', 'completed', 'failed')` |
| `ck_sentinel_sweep_overall` | `sentinel_sweeps` | `overall_status IN ('healthy', 'degraded', 'critical', 'unknown')` |
| `ck_sentinel_healing_tier` | `sentinel_healing_events` | `tier IN ('A', 'B', 'C')` |
| `ck_sentinel_healing_outcome` | `sentinel_healing_events` | `outcome IN ('pending', 'success', 'failure', 'escalated', 'skipped')` |

---

## 5. Relationships

```
sentinel_sweeps (1) ──< (N) sentinel_healing_events
                              FK: sweep_id -> sentinel_sweeps.id
                              ON DELETE CASCADE
```

Deleting a sweep cascades to all its healing events.

---

## 6. Pydantic Schemas

### Shared Model

**DimensionResult** -- Result from a single diagnostic dimension:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dimension` | `str` | Yes | D1--D6 identifier |
| `dimension_name` | `str` | Yes | Human-readable dimension name |
| `status` | `OverallStatus` | Yes | `healthy`, `degraded`, `critical`, `unknown` |
| `details` | `str` | No | Free-text details (default `""`) |
| `metrics` | `dict[str, Any]` | No | Dimension-specific metrics (default `{}`) |
| `duration_ms` | `int` | No | Dimension check duration (default `0`) |

### Sweep Schemas

**SweepCreate** -- `POST /api/v1/sentinel/sweeps`

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `sweep_type` | `SweepType` | Yes | -- |
| `trigger` | `SweepTrigger` | No | `MANUAL` |

**SweepUpdate** -- `PATCH /api/v1/sentinel/sweeps/{sweep_id}`

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `status` | `SweepStatus \| None` | No | `None` |
| `findings` | `list[DimensionResult] \| None` | No | `None` |
| `overall_status` | `OverallStatus \| None` | No | `None` |
| `duration_ms` | `int \| None` | No | `None` |
| `error` | `str \| None` | No | `None` |
| `completed_at` | `datetime \| None` | No | `None` |

When `findings` is provided in an update, the `dimensions_checked` column is automatically derived from the `dimension` field of each finding.

**SweepResponse** -- Returned by all sweep endpoints

| Field | Type |
|-------|------|
| `id` | `UUID` |
| `sweep_type` | `str` |
| `status` | `str` |
| `dimensions_checked` | `list[str]` |
| `findings` | `list[dict[str, Any]]` |
| `overall_status` | `str` |
| `trigger` | `str` |
| `duration_ms` | `int \| None` |
| `error` | `str \| None` |
| `started_at` | `datetime` |
| `completed_at` | `datetime \| None` |

Config: `from_attributes = True`

**SweepListResponse** -- Returned by `GET /api/v1/sentinel/sweeps`

| Field | Type |
|-------|------|
| `items` | `list[SweepResponse]` |
| `total` | `int` |

### Healing Event Schemas

**HealingEventCreate** -- `POST /api/v1/sentinel/healing`

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `sweep_id` | `UUID` | Yes | -- |
| `playbook` | `str` | Yes | -- |
| `tier` | `HealingTier` | Yes | -- |
| `action` | `str` | Yes | -- |
| `target_service` | `str \| None` | No | `None` |
| `governed` | `bool` | No | `False` |
| `details` | `dict[str, Any]` | No | `{}` |

**HealingEventUpdate** -- `PATCH /api/v1/sentinel/healing/{event_id}`

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `outcome` | `HealingOutcome \| None` | No | `None` |
| `approval_id` | `str \| None` | No | `None` |
| `duration_ms` | `int \| None` | No | `None` |
| `completed_at` | `datetime \| None` | No | `None` |
| `details` | `dict[str, Any] \| None` | No | `None` |

**HealingEventResponse** -- Returned by all healing endpoints

| Field | Type |
|-------|------|
| `id` | `UUID` |
| `sweep_id` | `UUID` |
| `playbook` | `str` |
| `tier` | `str` |
| `action` | `str` |
| `target_service` | `str \| None` |
| `outcome` | `str` |
| `governed` | `bool` |
| `approval_id` | `str \| None` |
| `details` | `dict[str, Any]` |
| `duration_ms` | `int \| None` |
| `created_at` | `datetime` |
| `completed_at` | `datetime \| None` |

Config: `from_attributes = True`

**HealingEventListResponse** -- Returned by `GET /api/v1/sentinel/healing`

| Field | Type |
|-------|------|
| `items` | `list[HealingEventResponse]` |
| `total` | `int` |

---

## 7. API Endpoints

All endpoints are prefixed with `/api/v1/sentinel` and tagged `sentinel`. Router is defined in `app/api/sentinel_router.py`.

### Sweep Endpoints

| Method | Path | Request Body | Response | Status | Description |
|--------|------|-------------|----------|--------|-------------|
| `POST` | `/sweeps` | `SweepCreate` | `SweepResponse` | 201 | Create a new sweep record |
| `GET` | `/sweeps` | -- | `SweepListResponse` | 200 | List sweeps with optional filters |
| `GET` | `/sweeps/{sweep_id}` | -- | `SweepResponse` | 200 | Get a single sweep by UUID |
| `PATCH` | `/sweeps/{sweep_id}` | `SweepUpdate` | `SweepResponse` | 200 | Update sweep with results/status |
| `GET` | `/sweeps/latest/status` | -- | `SweepResponse \| None` | 200 | Get the most recent sweep |

**GET /sweeps query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str \| None` | `None` | Filter by sweep status |
| `sweep_type` | `str \| None` | `None` | Filter by sweep type |
| `limit` | `int` | `20` | Max results |
| `offset` | `int` | `0` | Pagination offset |

Results are ordered by `started_at` descending.

### Healing Event Endpoints

| Method | Path | Request Body | Response | Status | Description |
|--------|------|-------------|----------|--------|-------------|
| `POST` | `/healing` | `HealingEventCreate` | `HealingEventResponse` | 201 | Create a healing event (validates sweep exists, 404 if not) |
| `GET` | `/healing` | -- | `HealingEventListResponse` | 200 | List healing events with optional filters |
| `PATCH` | `/healing/{event_id}` | `HealingEventUpdate` | `HealingEventResponse` | 200 | Update healing event outcome/details |

**GET /healing query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sweep_id` | `UUID \| None` | `None` | Filter by parent sweep |
| `outcome` | `str \| None` | `None` | Filter by outcome |
| `tier` | `str \| None` | `None` | Filter by healing tier |
| `limit` | `int` | `50` | Max results |
| `offset` | `int` | `0` | Pagination offset |

Results are ordered by `created_at` descending.

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Sweep or healing event not found |
| 404 | `POST /healing` with nonexistent `sweep_id` |

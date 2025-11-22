# DataForge Runs Router

API endpoints for storing and analyzing prompt execution runs from VibeForge/NeuroForge.

## Overview

The runs router provides a complete system for:

- **Logging runs** - Store prompt execution details from NeuroForge
- **Run history** - List and filter past runs
- **Analytics** - Usage metrics and cost tracking

## Architecture

```
VibeForge Frontend → NeuroForge Execution → DataForge Logging
                                   ↓
                            (runs_router.py)
                                   ↓
                            [Database Models]
                                   ↓
                            [TimescaleDB/PostgreSQL]
```

## Endpoints

### POST /api/v1/runs

Log a run to DataForge after execution.

**Request:**

```json
{
  "run_id": "run_abc123",
  "workspace_id": "ws_default",
  "prompt_snapshot": "Explain quantum entanglement...",
  "context_block_ids": ["ctx_physics"],
  "results": [
    {
      "model_id": "claude-3.5-sonnet",
      "provider": "anthropic",
      "output": "Quantum entanglement is...",
      "prompt_tokens": 150,
      "completion_tokens": 300,
      "total_tokens": 450,
      "latency_ms": 1850.5,
      "status": "success"
    }
  ],
  "total_latency_ms": 1850.5,
  "tags": ["physics", "quantum"],
  "notes": "Testing quantum explanation"
}
```

**Response:**

```json
{
  "status": "success",
  "run_id": "run_abc123",
  "message": "Run logged successfully"
}
```

### GET /api/v1/runs

List runs with optional filters.

**Query Parameters:**

- `workspace_id` - Filter by workspace
- `model_id` - Filter by model
- `status` - Filter by status (success/error)
- `tags` - Filter by tags (comma-separated)
- `start_date` - Start date (ISO format)
- `end_date` - End date (ISO format)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

**Response:**

```json
{
  "runs": [
    {
      "run_id": "run_abc123",
      "workspace_id": "ws_default",
      "prompt_snapshot": "Explain quantum entanglement...",
      "model_ids": ["claude-3.5-sonnet"],
      "total_tokens": 450,
      "total_cost_usd": 0.0135,
      "status": "success",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

### GET /api/v1/runs/{run_id}

Get detailed information about a specific run.

**Response:**

```json
{
  "run_id": "run_abc123",
  "workspace_id": "ws_default",
  "prompt_snapshot": "Explain quantum entanglement...",
  "context_block_ids": ["ctx_physics"],
  "results": [...],
  "total_latency_ms": 1850.5,
  "total_tokens": 450,
  "total_cost_usd": 0.0135,
  "tags": ["physics", "quantum"],
  "notes": "Testing quantum explanation",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### DELETE /api/v1/runs/{run_id}

Delete a run from history.

### GET /api/v1/runs/analytics/usage

Get usage metrics for a workspace.

**Query Parameters:**

- `workspace_id` (required) - Workspace ID
- `start_date` - Start date (ISO format)
- `end_date` - End date (ISO format)

**Response:**

```json
{
  "workspace_id": "ws_default",
  "total_runs": 150,
  "total_tokens": 67500,
  "total_cost_usd": 2.025,
  "runs_by_model": {
    "claude-3.5-sonnet": 100,
    "gpt-4": 50
  },
  "tokens_by_model": {
    "claude-3.5-sonnet": 45000,
    "gpt-4": 22500
  },
  "date_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-15T23:59:59Z"
  }
}
```

## Current Implementation Status

✅ **COMPLETED:**

- Router created with all endpoints defined
- Pydantic models for request/response validation
- Error handling and logging
- Registered in main.py
- Health check endpoint

⏳ **TODO:**

- Database models (SQLAlchemy)
- Database service layer
- Cost calculation logic
- Analytics aggregation queries
- TimescaleDB integration for time-series data

## Data Flow

```
1. User executes prompt in VibeForge
   ↓
2. VibeForge calls NeuroForge /api/v1/workbench/execute
   ↓
3. NeuroForge executes prompt on selected models
   ↓
4. NeuroForge calls DataForge POST /api/v1/runs to log results
   ↓
5. DataForge stores run in database
   ↓
6. User views history in VibeForge (calls GET /api/v1/runs)
```

## Database Schema (Planned)

```python
class Run(Base):
    """Prompt execution run."""
    run_id = Column(String, primary_key=True)
    workspace_id = Column(String, index=True)
    prompt_snapshot = Column(Text)
    context_block_ids = Column(JSON)
    total_latency_ms = Column(Float)
    total_tokens = Column(Integer)
    total_cost_usd = Column(Float)
    tags = Column(JSON)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ModelResult(Base):
    """Result from a single model execution."""
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey('runs.run_id'))
    model_id = Column(String, index=True)
    provider = Column(String)
    output = Column(Text)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    latency_ms = Column(Float)
    status = Column(String)
    error_message = Column(Text, nullable=True)
```

## Cost Calculation

Costs are calculated based on token usage and provider pricing:

```python
PRICING = {
    "anthropic": {
        "claude-3.5-sonnet": {
            "input": 0.003 / 1000,  # $3 per 1M tokens
            "output": 0.015 / 1000   # $15 per 1M tokens
        }
    },
    "openai": {
        "gpt-4": {
            "input": 0.03 / 1000,
            "output": 0.06 / 1000
        }
    }
}
```

## Integration

### From NeuroForge

After successful execution, NeuroForge should call:

```python
import httpx

async def log_run_to_dataforge(run_id: str, results: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DATAFORGE_API_BASE}/api/v1/runs",
            json={
                "run_id": run_id,
                "workspace_id": results["workspace_id"],
                "prompt_snapshot": results["prompt"],
                "context_block_ids": results.get("context_ids", []),
                "results": results["model_results"],
                "total_latency_ms": results["total_latency"],
                "tags": results.get("tags", []),
                "notes": results.get("notes")
            }
        )
        return response.json()
```

### From VibeForge

VibeForge can retrieve history:

```typescript
// List recent runs
const response = await fetch(
  `${DATAFORGE_API_BASE}/api/v1/runs?workspace_id=ws_default&page=1&page_size=20`
);
const data = await response.json();

// Get specific run details
const runDetail = await fetch(`${DATAFORGE_API_BASE}/api/v1/runs/${runId}`);
```

## Testing

```bash
# Test health check
curl http://localhost:8001/api/v1/runs/health

# Log a test run
curl -X POST http://localhost:8001/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "test_run_001",
    "workspace_id": "ws_test",
    "prompt_snapshot": "Hello, world!",
    "results": [],
    "total_latency_ms": 100
  }'

# List runs
curl "http://localhost:8001/api/v1/runs?workspace_id=ws_test"
```

## Next Steps

1. **Create database models** - SQLAlchemy models for Run and ModelResult
2. **Implement database service** - CRUD operations with repository pattern
3. **Add cost calculation** - Pricing logic for different providers/models
4. **Implement analytics queries** - Aggregation and metrics
5. **Add TimescaleDB** - Time-series optimization for run data
6. **Add tests** - Unit and integration tests for all endpoints

## Related Files

- `/app/api/runs_router.py` - This router
- `/app/main.py` - FastAPI app (router registered)
- `/NeuroForge/neuroforge_backend/workbench/service.py` - Should call log endpoint
- `/vibeforge/src/lib/stores/runStore.ts` - Frontend integration

---

Created: 2025-01-22
Status: Router scaffolded, database implementation pending

# FORGE ECOSYSTEM - PROJECT CONTEXT FOR CLAUDE

**Owner:** Charles Boswell, AI Engineer  
**Updated:** December 3, 2025  
**Upload this file to Claude at the start of every conversation**

---

## WHAT IS FORGE?

The Forge Ecosystem is a suite of 4 interconnected AI infrastructure services:

### 1. DataForge (Port 8001) - Vector Memory
- **Status:** ✅ Production (needs telemetry)
- **Tech:** Python, FastAPI, PostgreSQL + pgvector, Redis
- **Purpose:** Vector storage and semantic search for all Forge apps
- **Has:** 296 tests, 82% coverage, audit logs, Prometheus metrics
- **Needs:** Structured telemetry events for Command Central

### 2. NeuroForge (Port 8000) - AI Orchestration  
- **Status:** ✅ Production (needs telemetry)
- **Tech:** Python, FastAPI, Multi-provider LLM routing
- **Purpose:** Intelligent model selection across GPT, Claude, Ollama, Grok
- **Has:** 5-stage pipeline, 100+ tests, 89% coverage, Prometheus metrics
- **Needs:** Structured telemetry events for Command Central

### 3. Rake (Port 8002) - Ingestion Pipeline
- **Status:** 🚧 In Development (greenfield)
- **Tech:** Python, AsyncIO
- **Purpose:** Fetch → Clean → Chunk → Embed → Store pipeline
- **Will Have:** Telemetry built-in from day one

### 4. Forge Command - Observability Dashboard
- **Status:** 🚧 Planning Complete (ready to build)
- **Tech:** Tauri (Rust) + SvelteKit
- **Purpose:** Unified dashboard for all services
- **Will Have:** System tray, native notifications, real-time metrics

---

## CRITICAL ARCHITECTURE DECISIONS

### Database: Shared PostgreSQL
- **ONE database** (DataForge's PostgreSQL) for everything
- All services write telemetry to `events` table
- Single-user system (Charles only)
- Localhost-only, no authentication

### Security: Single-User
- No 2FA needed (only one user)
- No network exposure (Tauri app, zero ports)
- Focus: Parameterized SQL queries, input validation

### App Type: Tauri Desktop
- NOT a web app
- Native desktop with system tray
- ~30MB RAM, <100ms startup
- Zero network attack surface

---

## TELEMETRY SCHEMA (MOST IMPORTANT)

### Events Table
```sql
CREATE TABLE events (
  event_id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  service VARCHAR(50) NOT NULL,        -- 'dataforge' | 'neuroforge' | 'rake'
  event_type VARCHAR(100) NOT NULL,    -- 'query', 'model_request', 'job_completed'
  severity VARCHAR(20) NOT NULL,       -- 'info' | 'warning' | 'error' | 'critical'
  correlation_id UUID,                 -- FOR DISTRIBUTED TRACING (ALWAYS INCLUDE)
  metadata JSONB,
  metrics JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Event Types by Service

**DataForge:**
- `query` - Search completed
- `ingestion` - Documents added
- `query_error` - Failed

**NeuroForge:**
- `model_request` - LLM call completed (include: model, tokens, cost, latency)
- `model_error` - Failed

**Rake:**
- `job_started` - Job began
- `job_completed` - Job finished (include: phase_timings, docs_processed)
- `job_failed` - Job failed (include: failed_stage, error)
- `phase_completed` - Stage done (fetch/clean/chunk/embed/store)

### Telemetry Pattern (USE THIS ALWAYS)
```python
from forge_telemetry import TelemetryClient
import uuid, time

telemetry = TelemetryClient(os.getenv("DATABASE_URL"))
correlation_id = str(uuid.uuid4())
start_time = time.time()

try:
    result = await do_work()
    
    # SUCCESS EVENT
    await telemetry.emit({
        "service": "rake",  # or dataforge, neuroforge
        "event_type": "job_completed",
        "severity": "info",
        "correlation_id": correlation_id,  # CRITICAL
        "metadata": {"source": "sec_filings"},
        "metrics": {
            "duration_ms": (time.time() - start_time) * 1000,
            "items_processed": len(result)
        }
    })
except Exception as e:
    # ERROR EVENT
    await telemetry.emit({
        "service": "rake",
        "event_type": "job_failed",
        "severity": "error",
        "correlation_id": correlation_id,
        "metadata": {"error": str(e)}
    })
    raise
```

---

## BRAND COLORS (NEVER DEVIATE)

```css
DataForge  = Blue    #00A3FF
NeuroForge = Violet  #A855F7
Rake       = Cyan    #2DD4BF
Background = Black   #0D0D0F
Accent     = Ember   #D97706
```

**Rules:**
- DataForge charts/UI MUST be blue
- NeuroForge charts/UI MUST be violet
- Rake charts/UI MUST be cyan
- Dark mode always (forge-black background)

---

## CODE STANDARDS

### Python (DataForge, NeuroForge, Rake)
```python
# ALWAYS include:
- Type hints: def func(x: str) -> dict:
- Async/await: async def fetch_data() -> List[Doc]:
- Telemetry: await telemetry.emit({...})
- Correlation IDs: correlation_id = str(uuid.uuid4())
- Parameterized SQL: "WHERE id = :id", {"id": user_id}

# NEVER:
- String SQL: f"WHERE id = '{user_id}'"  # INJECTION RISK
- Missing types: def func(x):
- Blocking I/O: requests.get()  # Use aiohttp
- Missing telemetry
```

### Rust (Forge Command Tauri)
```rust
#[tauri::command]
async fn get_metrics() -> Result<Metrics, String> {
    sqlx::query_as!(Metrics, "SELECT * FROM events")
        .fetch_all(&pool)
        .await
        .map_err(|e| e.to_string())
}
```

### TypeScript/Svelte (Forge Command UI)
```typescript
import { invoke } from '@tauri-apps/api/tauri';

const metrics = await invoke<Metrics>('get_metrics');
```

---

## DEVELOPMENT ENVIRONMENT

### 4 Terminals
```bash
# 1. DataForge
cd DataForge && source venv/bin/activate
python -m uvicorn app.main:app --port 8001

# 2. NeuroForge  
cd NeuroForge/neuroforge_backend && source .venv/bin/activate
python -m uvicorn main:app --port 8000

# 3. Rake
cd Rake && source venv/bin/activate
python -m rake.main

# 4. Forge Command
cd ForgeCommand
npm run tauri dev
```

### Environment Variables
```bash
DATABASE_URL=postgresql://localhost:5432/dataforge
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## IMPLEMENTATION STATUS (4 WEEKS)

### Week 1: Foundation (CURRENT)
- [ ] Add `events` table to DataForge PostgreSQL
- [ ] Build `forge-telemetry` Python package
- [ ] Initialize Tauri project

### Week 2: Instrumentation
- [ ] Add telemetry to Rake (greenfield)
- [ ] Add telemetry to DataForge (retrofit)
- [ ] Add telemetry to NeuroForge (retrofit)

### Week 3: Dashboards
- [ ] Overview dashboard
- [ ] DataForge dashboard (blue)
- [ ] NeuroForge dashboard (violet)
- [ ] Rake dashboard (cyan)

### Week 4: Polish
- [ ] System tray
- [ ] Notifications
- [ ] Alerting
- [ ] Production build

---

## WHEN WRITING CODE

### Always Include:
1. ✅ **Telemetry emission** - Every operation emits events
2. ✅ **Correlation IDs** - Track requests across services
3. ✅ **Type hints** - Python, TypeScript, Rust
4. ✅ **Error handling** - Try/except with error events
5. ✅ **Async/await** - For all I/O operations
6. ✅ **Tests** - Unit tests for all functions

### Never:
1. ❌ String interpolation in SQL (use parameterized)
2. ❌ Missing correlation_id (breaks tracing)
3. ❌ Wrong service colors (blue/violet/cyan)
4. ❌ Skipping telemetry emission
5. ❌ Hard-coded credentials
6. ❌ Blocking I/O in async functions

---

## EXAMPLE GOOD QUESTIONS

**✅ Good:**
> "Write the Rake fetch stage for SEC EDGAR filings. Include telemetry emission 
> with correlation_id, error handling, type hints, and unit tests. Use cyan color 
> for any UI references."

**✅ Good:**
> "Add telemetry to DataForge's query endpoint at app/api/v1/vector_router.py. 
> Emit 'query' events with latency metrics, propagate correlation_id from the 
> request, and emit error events on failure. Include tests."

**✅ Good:**
> "Design the NeuroForge dashboard showing model latency P50/P90/P99. Use violet 
> theme. Show the Svelte component, Rust IPC command, and SQL query for percentiles."

**❌ Bad:**
> "How do I add logging?"  
> (Too vague - which service? Need telemetry, not logging)

**❌ Bad:**
> "Write a Python function to fetch data"  
> (No context - which service? What telemetry? What types?)

---

## REFERENCE DOCUMENTS

In the project root:
- `FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md` - All architectural decisions
- `RAKE_DEVELOPMENT_GUIDE.md` - Complete Rake implementation
- `Stage1-10` documents - Detailed specs for each phase

---

## CRITICAL REMINDERS

**Security:**
- ✅ Parameterized SQL ALWAYS
- ✅ Validate input
- ❌ Never string interpolate SQL

**Telemetry:**
- ✅ Every operation emits events
- ✅ Include correlation_id
- ✅ Track timing metrics
- ❌ Never skip telemetry

**Design:**
- ✅ Use correct service colors
- ✅ Dark mode always
- ❌ Never mix colors arbitrarily

**Testing:**
- ✅ Unit tests for all functions
- ✅ Verify telemetry in tests
- ✅ Test correlation_id propagation

---

## PROJECT GOALS

1. **Unified Observability** - Single dashboard for all services
2. **Predictive Intelligence** - Anomaly detection, cost forecasting
3. **Operational Control** - Trigger jobs, flush caches from UI
4. **Data Lineage** - Track data flow across services

**Success:** 95%+ telemetry coverage, <2s dashboard load, <5% false alerts

---

**MOST IMPORTANT:** Always emit telemetry events with correlation_id. Always use parameterized SQL. Always follow service colors (blue/violet/cyan).

---

**End of Context**  
Upload this file at the start of every Claude conversation about Forge.

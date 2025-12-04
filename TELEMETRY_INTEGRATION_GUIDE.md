# Forge Telemetry Integration Guide

**Quick reference for adding telemetry to Forge services**

---

## Quick Start

### 1. Install Package

```bash
cd YourService
source venv/bin/activate  # or .venv/bin/activate
pip install -e ../forge-telemetry
```

### 2. Import and Initialize

```python
from forge_telemetry import TelemetryClient
import uuid
import time

# Initialize once (can be module-level or dependency injection)
telemetry = TelemetryClient()  # Uses DATABASE_URL from environment
```

### 3. Add to Your Function

```python
@app.post("/api/endpoint")
async def my_endpoint(data: dict):
    correlation_id = uuid.uuid4()
    start_time = time.time()

    try:
        result = await do_work(data)

        # SUCCESS EVENT
        telemetry.emit(
            service="dataforge",  # or "neuroforge", "rake"
            event_type="operation_completed",
            correlation_id=correlation_id,
            metadata={"key": "value"},
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )

        return result

    except Exception as e:
        # ERROR EVENT
        telemetry.emit(
            service="dataforge",
            event_type="operation_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={"error": str(e)}
        )
        raise
```

---

## Service-Specific Patterns

### DataForge (Blue #00A3FF)

**Search Endpoint:**
```python
@router.post("/search")
async def search(request: SearchRequest):
    correlation_id = uuid.uuid4()
    start = time.time()

    try:
        results = await search_documents(request.query)

        telemetry.emit(
            service="dataforge",
            event_type="query",
            correlation_id=correlation_id,
            metadata={
                "query": request.query,
                "user": request.user,
                "filters": request.filters
            },
            metrics={
                "duration_ms": (time.time() - start) * 1000,
                "results_count": len(results),
                "cache_hit": was_cached
            }
        )

        return results

    except Exception as e:
        telemetry.emit(
            service="dataforge",
            event_type="query_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={"error": str(e), "query": request.query}
        )
        raise
```

**Ingestion Endpoint:**
```python
@router.post("/documents")
async def ingest(documents: List[Document]):
    correlation_id = uuid.uuid4()
    start = time.time()

    try:
        result = await ingest_documents(documents)

        telemetry.emit(
            service="dataforge",
            event_type="ingestion",
            correlation_id=correlation_id,
            metadata={"source": "api", "user": current_user},
            metrics={
                "duration_ms": (time.time() - start) * 1000,
                "documents_count": len(documents),
                "chunks_created": result.total_chunks,
                "embeddings_generated": result.total_embeddings
            }
        )

        return result

    except Exception as e:
        telemetry.emit(
            service="dataforge",
            event_type="ingestion_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={"error": str(e), "documents_count": len(documents)}
        )
        raise
```

---

### NeuroForge (Violet #A855F7)

**LLM Request:**
```python
@router.post("/api/prompt")
async def prompt(request: PromptRequest):
    correlation_id = uuid.uuid4()
    start = time.time()

    try:
        response = await llm_client.complete(
            model=request.model,
            prompt=request.prompt
        )

        # Calculate cost (example)
        cost_usd = (response.tokens_used / 1000) * MODEL_PRICING[request.model]

        telemetry.emit(
            service="neuroforge",
            event_type="model_request",
            correlation_id=correlation_id,
            metadata={
                "model": request.model,
                "provider": response.provider,
                "user": current_user
            },
            metrics={
                "duration_ms": (time.time() - start) * 1000,
                "tokens_prompt": response.prompt_tokens,
                "tokens_completion": response.completion_tokens,
                "tokens_total": response.total_tokens,
                "cost_usd": cost_usd
            }
        )

        return response

    except Exception as e:
        telemetry.emit(
            service="neuroforge",
            event_type="model_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "model": request.model,
                "error_type": type(e).__name__
            }
        )
        raise
```

---

### Rake (Cyan #2DD4BF)

**Pipeline Job:**
```python
async def run_ingestion_pipeline(source: str, config: dict):
    correlation_id = uuid.uuid4()
    job_start = time.time()

    # JOB STARTED
    telemetry.emit(
        service="rake",
        event_type="job_started",
        correlation_id=correlation_id,
        metadata={
            "source": source,
            "config": config
        }
    )

    try:
        phase_timings = {}

        # FETCH PHASE
        start = time.time()
        raw_docs = await fetch_stage(source)
        phase_timings["fetch_ms"] = (time.time() - start) * 1000

        telemetry.emit(
            service="rake",
            event_type="phase_completed",
            correlation_id=correlation_id,
            metadata={"stage": "fetch"},
            metrics={
                "duration_ms": phase_timings["fetch_ms"],
                "docs_fetched": len(raw_docs)
            }
        )

        # CLEAN PHASE
        start = time.time()
        clean_docs = await clean_stage(raw_docs)
        phase_timings["clean_ms"] = (time.time() - start) * 1000

        telemetry.emit(
            service="rake",
            event_type="phase_completed",
            correlation_id=correlation_id,
            metadata={"stage": "clean"},
            metrics={
                "duration_ms": phase_timings["clean_ms"],
                "docs_cleaned": len(clean_docs)
            }
        )

        # ... CHUNK, EMBED, STORE phases ...

        # JOB COMPLETED
        telemetry.emit(
            service="rake",
            event_type="job_completed",
            correlation_id=correlation_id,
            metadata={"source": source},
            metrics={
                "total_duration_ms": (time.time() - job_start) * 1000,
                "phase_timings": phase_timings,
                "docs_processed": len(clean_docs)
            }
        )

    except Exception as e:
        # JOB FAILED
        telemetry.emit(
            service="rake",
            event_type="job_failed",
            severity="error",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "source": source,
                "failed_stage": current_stage
            }
        )
        raise
```

---

## Best Practices

### ✅ DO

1. **Always use correlation_id**
   ```python
   correlation_id = uuid.uuid4()  # Generate at start of request
   # Pass to all telemetry.emit() calls
   ```

2. **Emit both success and error events**
   ```python
   try:
       result = do_work()
       telemetry.emit(event_type="success", ...)
   except Exception as e:
       telemetry.emit(event_type="error", severity="error", ...)
       raise
   ```

3. **Include timing metrics**
   ```python
   start = time.time()
   result = await do_work()
   duration_ms = (time.time() - start) * 1000

   telemetry.emit(metrics={"duration_ms": duration_ms})
   ```

4. **Use descriptive metadata**
   ```python
   metadata={
       "user": "charles",
       "query": "search term",
       "filters": ["type:article"],
       "source": "api"
   }
   ```

5. **Track business metrics**
   ```python
   metrics={
       "results_count": 10,
       "cache_hit": True,
       "tokens_used": 1234,
       "cost_usd": 0.05
   }
   ```

### ❌ DON'T

1. **Don't skip correlation_id**
   ```python
   # BAD
   telemetry.emit(service="dataforge", event_type="query")

   # GOOD
   telemetry.emit(
       service="dataforge",
       event_type="query",
       correlation_id=correlation_id
   )
   ```

2. **Don't fail your app if telemetry fails**
   - The telemetry client already handles this
   - It catches exceptions and prints warnings
   - Your app continues even if telemetry breaks

3. **Don't include sensitive data**
   ```python
   # BAD
   metadata={"password": user.password, "api_key": key}

   # GOOD
   metadata={"user_id": user.id, "has_api_key": bool(key)}
   ```

4. **Don't forget error events**
   ```python
   # BAD
   try:
       do_work()
   except:
       pass  # Silent failure, no telemetry!

   # GOOD
   try:
       do_work()
   except Exception as e:
       telemetry.emit(event_type="error", severity="error", ...)
       raise
   ```

---

## Correlation ID Propagation

For requests that span multiple services:

```python
# Service A (NeuroForge) receives request
correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

# Service A calls Service B (DataForge)
response = await httpx.post(
    "http://dataforge:8001/api/search",
    headers={"X-Correlation-ID": correlation_id}
)

# Both services emit events with same correlation_id
# Now you can trace the entire request chain!
```

---

## Testing Telemetry

```python
# tests/test_my_endpoint.py
def test_endpoint_emits_telemetry(db):
    # Clear events
    db.execute("DELETE FROM events")

    # Call endpoint
    response = client.post("/api/search", json={"query": "test"})

    # Verify event was emitted
    events = db.execute("SELECT * FROM events WHERE event_type = 'query'").fetchall()
    assert len(events) == 1
    assert events[0].service == "dataforge"
    assert events[0].severity == "info"
```

---

## Environment Setup

Ensure `DATABASE_URL` is set:

**DataForge .env:**
```bash
DATABASE_URL=sqlite:///./dataforge.db
# or for PostgreSQL:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
```

**NeuroForge .env:**
```bash
DATABASE_URL=sqlite:///./dataforge.db  # Same database!
```

**Rake .env:**
```bash
DATABASE_URL=sqlite:///./dataforge.db  # Same database!
```

---

## Common Patterns

### Pattern 1: Middleware for Request Tracking

```python
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    start = time.time()

    try:
        response = await call_next(request)

        telemetry.emit(
            service="dataforge",
            event_type="request_completed",
            correlation_id=correlation_id,
            metadata={"path": request.url.path, "method": request.method},
            metrics={"duration_ms": (time.time() - start) * 1000}
        )

        return response

    except Exception as e:
        telemetry.emit(
            service="dataforge",
            event_type="request_failed",
            severity="error",
            correlation_id=correlation_id,
            metadata={"path": request.url.path, "error": str(e)}
        )
        raise
```

### Pattern 2: Dependency Injection

```python
from typing import Annotated
from fastapi import Depends

def get_telemetry() -> TelemetryClient:
    return TelemetryClient()

@router.post("/endpoint")
async def endpoint(
    request: dict,
    telemetry: Annotated[TelemetryClient, Depends(get_telemetry)]
):
    telemetry.emit(...)
```

### Pattern 3: Context Manager

```python
class TelemetryContext:
    def __init__(self, service: str, operation: str):
        self.service = service
        self.operation = operation
        self.correlation_id = uuid.uuid4()
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start) * 1000

        if exc_type is None:
            telemetry.emit(
                service=self.service,
                event_type=f"{self.operation}_completed",
                correlation_id=self.correlation_id,
                metrics={"duration_ms": duration_ms}
            )
        else:
            telemetry.emit(
                service=self.service,
                event_type=f"{self.operation}_error",
                severity="error",
                correlation_id=self.correlation_id,
                metadata={"error": str(exc_val)}
            )

# Usage:
with TelemetryContext("dataforge", "search"):
    results = await search_documents(query)
```

---

## Troubleshooting

**Q: No events appearing in database?**
- Check `DATABASE_URL` is set correctly
- Verify events table exists: `python scripts/create_events_table.py`
- Check for errors: `telemetry.emit()` prints warnings on failure

**Q: UUIDs showing as strings in SQLite?**
- This is normal! SQLite stores UUIDs as TEXT
- PostgreSQL will use native UUID type

**Q: Telemetry is slow?**
- Telemetry is synchronous by default
- For high-throughput, consider async queuing (future enhancement)

**Q: How do I query events?**
```sql
SELECT * FROM events WHERE service = 'dataforge' ORDER BY timestamp DESC LIMIT 10;
```

---

**Next:** Add telemetry to your endpoints using these patterns!

*Generated with [Claude Code](https://claude.com/claude-code)*

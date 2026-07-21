# DataForge Telemetry Integration Status

> **ARCHIVED SNAPSHOT:** Any `/api/projects` manuscript ingestion below is retired and prohibited.
> AuthorForge telemetry uses only `AuthorForgeAnalyticsEnvelope.v1`.

**Updated:** December 3, 2025

## ✅ Completed Endpoints

### 1. Search Endpoint (`/api/search`)

**File:** [app/api/search_router.py:24](app/api/search_router.py#L24)
**Implementation:** [app/api/search.py:17](app/api/search.py#L17)
**Status:** ✅ COMPLETE

**What was added:**
- Correlation ID support (via `X-Correlation-ID` header)
- Success event emission with detailed metrics
- Error event emission on failures
- Timing breakdown (embedding, database query, total)

**Telemetry events emitted:**
- `query` (success) - Emitted on successful search
- `query_error` (error) - Emitted on failure

**Metrics tracked:**
- `duration_ms` - Total search duration
- `embedding_duration_ms` - Time to generate query embedding
- `db_query_duration_ms` - Time for database query
- `results_count` - Number of results returned
- `avg_similarity` - Average similarity score of results

**Metadata tracked:**
- `query` - Search query (truncated to 100 chars)
- `domain_id` - Domain filter (if provided)
- `tags` - Tag filters (if provided)
- `limit` - Results limit
- `similarity_threshold` - Minimum similarity score

**Example usage:**
```bash
# Without correlation ID
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "limit": 10,
    "similarity_threshold": 0.7
  }'

# With correlation ID for distributed tracing
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "query": "machine learning",
    "limit": 10
  }'
```

**Telemetry query:**
```sql
-- View all search events
SELECT
    event_id,
    timestamp,
    correlation_id,
    json_extract(metadata, '$.query') as query,
    json_extract(metrics, '$.duration_ms') as duration_ms,
    json_extract(metrics, '$.results_count') as results
FROM events
WHERE service = 'dataforge' AND event_type = 'query'
ORDER BY timestamp DESC
LIMIT 10;

-- Calculate average search performance
SELECT
    COUNT(*) as total_searches,
    AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_duration_ms,
    AVG(CAST(json_extract(metrics, '$.results_count') AS INTEGER)) as avg_results,
    AVG(CAST(json_extract(metrics, '$.avg_similarity') AS FLOAT)) as avg_similarity
FROM events
WHERE service = 'dataforge' AND event_type = 'query';

-- Error rate
SELECT
    COUNT(*) FILTER (WHERE event_type = 'query') as successful,
    COUNT(*) FILTER (WHERE event_type = 'query_error') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE event_type = 'query_error') / COUNT(*), 2) as error_rate_pct
FROM events
WHERE service = 'dataforge' AND event_type IN ('query', 'query_error');
```

---

## ⏸️ Pending Endpoints

### 2. Document Ingestion (`/api/projects/manuscripts`)

**File:** [app/api/projects_router.py:107](app/api/projects_router.py#L107)
**Status:** ⏸️ PENDING

**Telemetry events to add:**
- `ingestion` (success)
- `ingestion_error` (error)

**Metrics to track:**
- `duration_ms`
- `documents_count`
- `chunks_created`
- `embeddings_generated`
- `total_tokens`

---

## 📊 Telemetry Coverage

**Current status:**
- ✅ Search endpoint: 100% instrumented
- ⏸️ Ingestion endpoints: 0%
- ⏸️ Admin endpoints: 0%
- ⏸️ Error handlers: 0%

**Overall coverage:** ~5% (1 out of ~20 major endpoints)

**Goal:** 95% coverage by end of Week 2

---

## 🎯 Next Steps

1. **Add telemetry to ingestion endpoint**
   - Track document uploads
   - Track chunking and embedding generation
   - Track storage operations

2. **Add telemetry to project endpoints**
   - Project creation
   - Character/location creation
   - Manuscript operations

3. **Add global error handler with telemetry**
   - Catch unhandled exceptions
   - Emit error events for all failures

4. **Test telemetry in production-like load**
   - Verify performance impact is minimal
   - Verify events are written correctly
   - Check correlation ID propagation

---

## 🧪 Testing

### Manual Test

```bash
# 1. Start DataForge
cd DataForge
source venv/bin/activate
python -m uvicorn app.main:app --port 8001 --reload

# 2. Make a search request
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "limit": 5}'

# 3. Check telemetry events
sqlite3 dataforge.db "SELECT * FROM events WHERE event_type = 'query' ORDER BY timestamp DESC LIMIT 1;"
```

### Expected telemetry event:

```json
{
  "event_id": "uuid-here",
  "timestamp": "2025-12-04T00:30:00.000000",
  "service": "dataforge",
  "event_type": "query",
  "severity": "info",
  "correlation_id": "uuid-here",
  "metadata": {
    "query": "test search",
    "domain_id": null,
    "tags": null,
    "limit": 5,
    "similarity_threshold": 0.7
  },
  "metrics": {
    "duration_ms": 45.2,
    "embedding_duration_ms": 20.1,
    "db_query_duration_ms": 15.3,
    "results_count": 3,
    "avg_similarity": 0.85
  }
}
```

---

## 📝 Implementation Notes

### Pattern Used

```python
# 1. Import telemetry at module level
from forge_telemetry import TelemetryClient
telemetry = TelemetryClient()

# 2. Accept correlation_id parameter
async def my_function(..., correlation_id: Optional[uuid.UUID] = None):
    # Generate if not provided
    if correlation_id is None:
        correlation_id = uuid.uuid4()

    start_time = time.time()

    try:
        # ... do work ...

        # Emit success event
        telemetry.emit(
            service="dataforge",
            event_type="operation",
            correlation_id=correlation_id,
            metadata={...},
            metrics={"duration_ms": (time.time() - start_time) * 1000, ...}
        )

        return result

    except Exception as e:
        # Emit error event
        telemetry.emit(
            service="dataforge",
            event_type="operation_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={"error": str(e), ...},
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )
        raise
```

### Correlation ID Propagation

```python
# Router accepts X-Correlation-ID header
@router.post("/endpoint")
async def endpoint(
    ...,
    x_correlation_id: Optional[str] = Header(None)
):
    # Parse or generate correlation ID
    correlation_id = uuid.UUID(x_correlation_id) if x_correlation_id else uuid.uuid4()

    # Pass to service function
    return await service_function(..., correlation_id=correlation_id)
```

---

**Status:** Week 2 in progress - 1 endpoint complete, ~19 to go!

*Generated with [Claude Code](https://claude.com/claude-code)*

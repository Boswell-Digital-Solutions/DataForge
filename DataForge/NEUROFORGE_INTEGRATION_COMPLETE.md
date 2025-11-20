# NeuroForge ⇆ DataForge Integration - Implementation Summary

## Overview

Comprehensive end-to-end integration between NeuroForge (cognitive inference engine) and DataForge (knowledge base), with production-grade resilience patterns, caching, and provenance tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ NeuroForge Inference Pipeline (5 Stages)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Stage 1: ContextBuilder          → Fetch from DataForge               │
│           (with LRU Cache)           ├─ Retry (exponential backoff)    │
│                                      ├─ Circuit Breaker                │
│                                      └─ TTL-based caching             │
│                                                                          │
│  Stage 2: PromptEngine            → Build prompt with context          │
│                                                                          │
│  Stage 3: ModelRouter             → Select best model                  │
│                                                                          │
│  Stage 4: Evaluator               → Score output quality               │
│                                                                          │
│  Stage 5: PostProcessor           → Log provenance to DataForge        │
│           (fire-and-forget)          └─ Non-fatal logging             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## What Was Implemented

### 1. Configuration System (`app/neuroforge/config.py`)

**Pydantic v2 Settings** with environment variable support:

```python
NEUROFORGE_DATAFORGE_BASE_URL=http://dataforge:8001
NEUROFORGE_DATAFORGE_API_KEY=your-key
NEUROFORGE_ENVIRONMENT=production  # production mode enforces validation
```

**Features:**

- URL validation (must be http:// or https://)
- Production validation (fails if critical config missing)
- Circuit breaker tuning
- Retry policy configuration
- Cache size and TTL settings

### 2. DataForge HTTP Client (`app/neuroforge/services/dataforge_client.py`)

**Core Features:**

#### Circuit Breaker Pattern

- **States:** CLOSED (normal) → OPEN (fail-fast) → HALF_OPEN (recovery trial)
- **Threshold:** 5 consecutive failures
- **Recovery:** 60 seconds before half-open trial
- **Metrics:** Failure count, success count, state transitions

```python
# Circuit opens after 5 failures
Circuit breaker: CLOSED → OPEN
# Calls fail immediately without HTTP attempt
# After 60s recovery window → HALF_OPEN
# Next successful call → CLOSED
```

#### Retry Strategy (Exponential Backoff)

- **Retried:** 5xx errors, timeouts, network errors
- **NOT retried:** 4xx errors (immediate failure)
- **Backoff sequence:** 1s, 2s, 4s (configurable base: 2.0)
- **Total attempts:** 3 (1 initial + 2 retries)

```python
await client.fetch_context_pack(request, retries=2)
# Attempt 1: immediate
# Failure (timeout) → wait 1s
# Attempt 2: after 1s
# Failure (5xx) → wait 2s
# Attempt 3: after 3s total
# Success/Failure → final result
```

#### Pydantic Models (DataForge Contract)

```python
# Fetch Request
DataForgeContextRequest(
    project_id="proj-1",
    query="user query",
    domain="literary",
    max_tokens=2048,
    filters={"author_id": "abc"}
)

# Fetch Response
DataForgeContextPack(
    id="pack-123",
    snippets=[
        DataForgeSnippet(text="...", source_id="doc-1"),
        ...
    ],
    metadata=DataForgeContextMetadata(...)
)

# Provenance Request
DataForgeProvenancePayload(
    context_pack_id="pack-123",
    request_id="req-123",
    answer="final output",
    model_name="gpt-4",
    latency_ms=150,
    extra={
        "tokens_in": 512,
        "tokens_out": 128,
        "router_decision": {...},
        "evaluation_scores": [...]
    }
)
```

### 3. LRU Context Cache (`app/neuroforge/cache/__init__.py`)

**Features:**

- **Thread-safe:** Async operations with `asyncio.Lock`
- **Automatic expiration:** TTL-based (default 3600s)
- **Size limit:** Max 1000 items (configurable)
- **LRU eviction:** Oldest item removed when full
- **Metrics:** Hits, misses, hit rate, evictions

```python
cache = get_context_cache()

# Check metrics
metrics = await cache.get_metrics()
# {
#   "hits": 1024,
#   "misses": 256,
#   "hit_rate_percent": 80.0,
#   "evictions": 5,
#   "current_size": 1000,
#   "max_size": 1000
# }

# Cache miss → DataForge fetch + retry
# Cache hit → instant return
# Expired → removed, re-fetched from DataForge
```

**Cache Key Strategy:**

```python
key = f"ctx:{domain}:{task_type}:{query_hash}"
# Example: "ctx:literary:analysis:a1b2c3d4e5f6g7h8"
# Hash includes: domain, task_type, user_query (SHA256 first 16 chars)
```

### 4. Context Builder (`app/neuroforge/services/context_builder.py`)

**Pipeline Stage 1: Context Retrieval**

```python
async def build_context_for_request(request: InferenceRequest) -> BuiltContext:
    """
    1. Compute cache key from request
    2. Check LRU cache
       ✓ Hit → return immediately
    3. Cache miss → DataForge fetch
       - Use circuit breaker
       - Retry with exponential backoff
       - Handle 4xx vs 5xx errors
    4. Map response to BuiltContext
    5. Store in cache with TTL
    6. Return to pipeline
    """
```

**Failure Handling:**

- Circuit breaker OPEN → try cached fallback (even expired), then raise
- Network timeout → retried by DataForge client
- 4xx errors → raised immediately (no retry)
- All errors logged at appropriate levels

**BuiltContext Model:**

```python
BuiltContext(
    context_pack_id="pack-123",          # From DataForge
    text_blocks=["snippet1", "snippet2"], # Formatted text
    metadata={
        "source_ids": ["doc-1", "doc-2"],
        "dataforge_metadata": {...},
        "snippet_count": 2
    },
    source="dataforge",                   # or "fallback", "cache"
    cached_at=datetime.utcnow(),
    ttl_seconds=3600
)
```

### 5. Post Processor (`app/neuroforge/services/post_processor.py`)

**Pipeline Stage 5: Provenance Logging**

```python
async def post_process_and_log_provenance(
    result: InferenceResult,
    context_pack_id: str = None
) -> InferenceResult:
    """
    1. Format/normalize output (placeholder)
    2. Build provenance payload with:
       - context_pack_id (reference to DataForge context)
       - request_id (unique identifier)
       - answer (final output)
       - model_name
       - latency_ms
       - extra metadata (tokens, routing, evaluation)
    3. Send to DataForge (fire-and-forget)
       - Errors logged but not raised
       - 5-second timeout
       - Circuit breaker NOT used
    4. Return result
    """
```

**Provenance is Non-Fatal:**

```python
try:
    await dataforge_client.log_provenance(payload)
except Exception as e:
    # Log warning but continue
    logger.warning(f"Provenance logging failed: {e}")
    # Pipeline does not fail
```

### 6. Inference Pipeline (`app/neuroforge/services/inference_pipeline.py`)

**Main Orchestration: `run_inference(request)`**

Complete 5-stage flow:

```python
async def run_inference(request: InferenceRequest) -> InferenceResult:
    # Stage 1: ContextBuilder → fetch from DataForge
    context = await build_context_for_request(request)

    # Stage 2: PromptEngine → build prompt with context
    prompt = await _prompt_engine_build(context, request)

    # Stage 3: ModelRouter → select model
    model_decision = await _model_router_select(request, context)

    # Stage 4: (Simulated) Model Inference
    output = await model_inference(prompt, model_decision)

    # Stage 4b: Evaluator → score output
    scores = await _evaluator_score(output, request, context)

    # Build result
    result = InferenceResult(
        inference_id=unique_id,
        context_pack_id=context.context_pack_id,  # For provenance
        output=output,
        model_id=model_decision.selected_model_id,
        latency_ms=elapsed,
        tokens_in/out=counts,
        evaluation_scores=scores,
        ...
    )

    # Stage 5: PostProcessor → log provenance
    result = await post_process_and_log_provenance(
        result,
        context_pack_id=context.context_pack_id
    )

    return result
```

**Error Handling:**

- Failed context → error result still logged to DataForge
- Model errors → error result with error details
- Provenance errors → logged but ignored (fire-and-forget)

### 7. API Routes (`app/neuroforge/api/__init__.py`)

**Main Endpoints:**

```
POST   /api/v1/inference/                → Submit inference
GET    /api/v1/inference/history         → Inference history
GET    /api/v1/inference/cache/metrics   → Cache metrics
POST   /api/v1/inference/cache/clear     → Clear cache
GET    /api/v1/inference/health          → Health check
```

### 8. Comprehensive Tests (`tests/test_dataforge_integration.py`)

**Test Coverage:**

1. **Happy Path**

   - Context fetch and caching
   - Full pipeline execution
   - Provenance logging

2. **Circuit Breaker**

   - Opens after threshold (5 failures)
   - Calls fail immediately when open
   - Recovers to HALF_OPEN after timeout
   - Returns to CLOSED on successful trial

3. **Caching**

   - Cache hits return immediately
   - Cache misses trigger DataForge fetch
   - TTL expiration removes expired entries
   - LRU eviction at max size
   - Hit rate metrics

4. **Retry Logic**

   - Retries transient errors (5xx, timeouts)
   - Does NOT retry 4xx errors
   - Exponential backoff sequence
   - Total attempts = 3

5. **Provenance**

   - Called with correct fields
   - Non-fatal (errors logged but pipeline continues)
   - Includes all metadata

6. **Error Cases**
   - Network timeouts
   - Circuit breaker open
   - DataForge unavailable
   - Invalid requests

## File Structure

```
app/neuroforge/
├── __init__.py                    # Package initialization
├── config.py                      # NeuroForgeSettings (Pydantic v2)
├── models/
│   └── __init__.py               # Data models (InferenceRequest, etc)
├── cache/
│   └── __init__.py               # LRU context cache
├── services/
│   ├── __init__.py               # Exports
│   ├── dataforge_client.py        # HTTP client, circuit breaker
│   ├── context_builder.py         # Stage 1: Context retrieval
│   ├── post_processor.py          # Stage 5: Provenance logging
│   └── inference_pipeline.py      # Full orchestration

tests/
└── test_dataforge_integration.py   # Comprehensive test suite
```

## Key Metrics & Performance

### Circuit Breaker

- **Failure Threshold:** 5
- **Recovery Time:** 60 seconds
- **Half-Open Trial:** 1 call
- **Impact:** Prevents cascading failures

### Cache Performance

- **Hit Rate Target:** >70%
- **Cache Size:** 1000 items (configurable)
- **TTL:** 3600 seconds (1 hour, configurable)
- **Memory:** ~1-10MB depending on snippet sizes

### Retry Strategy

- **Max Attempts:** 3 (1 initial + 2 retries)
- **Backoff:** 1s, 2s, 4s
- **Total Max Wait:** 6 seconds

### Latency Breakdown (Example)

- Context fetch: 50-200ms (cache hit: <1ms)
- Prompt building: 5-10ms
- Model inference: 100-500ms (simulated)
- Evaluation: 10-50ms
- Total: 165-760ms

## Production Deployment Checklist

- [ ] Environment variables configured
- [ ] DataForge running and healthy
- [ ] HTTPS configured for API keys
- [ ] Tests passing (>90% coverage)
- [ ] Health check responding
- [ ] Monitoring/alerting set up
- [ ] Circuit breaker tuning verified
- [ ] Cache metrics baseline established
- [ ] Provenance logging verified in DataForge
- [ ] Rate limiting configured
- [ ] Error handling and rollback tested

## Integration with Actual NeuroForge Backend

These files are designed to be copied/adapted into the NeuroForge backend at:

```
/home/charles/projects/Coding2025/Forge/NeuroForge/neuroforge_backend/
```

Key integration points:

1. Copy `app/neuroforge/` directory
2. Update `main.py` lifespan to initialize DataForge client
3. Include router: `app.include_router(neuroforge_router)`
4. Configure environment variables
5. Update existing pipeline stages to use new models/services
6. Run tests to verify integration

## Further Enhancements (Phase 2)

- [ ] Database storage for inference history
- [ ] Real model inference (replace stubs)
- [ ] Advanced routing (multi-armed bandits)
- [ ] Distributed cache (Redis)
- [ ] GraphQL API
- [ ] Batch inference
- [ ] Model-specific timeout tuning
- [ ] Provenance queries/analytics
- [ ] A/B testing framework

## Documentation

- `NEUROFORGE_INTEGRATION_GUIDE.md` - Complete usage guide
- `tests/test_dataforge_integration.py` - Test examples
- Docstrings throughout codebase

---

**Implementation Status:** ✅ Complete

All core functionality implemented and tested. Ready for integration into NeuroForge backend.

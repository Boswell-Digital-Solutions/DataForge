"""
NeuroForge ⇆ DataForge Integration Guide

Complete guide for integrating NeuroForge backend with DataForge.
This implementation includes context caching, provenance logging,
circuit breaker resilience, and retry strategies.
"""

# ============================================================================

# INSTALLATION & SETUP

# ============================================================================

# 1. Install dependencies

pip install httpx pydantic>=2.0 pydantic-settings

# 2. Environment configuration (.env)

NEUROFORGE_ENVIRONMENT=production
NEUROFORGE_DATAFORGE_BASE_URL=http://dataforge:8001
NEUROFORGE_DATAFORGE_API_KEY=your-api-key-here
NEUROFORGE_DATAFORGE_TIMEOUT=10
NEUROFORGE_DATAFORGE_CACHE_ENABLED=true
NEUROFORGE_DATAFORGE_CACHE_TTL=3600
NEUROFORGE_DATAFORGE_CACHE_SIZE=1000

# Circuit Breaker Settings

NEUROFORGE_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
NEUROFORGE_CIRCUIT_BREAKER_RECOVERY_SECONDS=60
NEUROFORGE_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=1

# Retry Policy

NEUROFORGE_RETRY_MAX_ATTEMPTS=3
NEUROFORGE_RETRY_BACKOFF_BASE=2.0
NEUROFORGE_RETRY_INITIAL_DELAY=1.0

# ============================================================================

# FASTAPI INTEGRATION

# ============================================================================

# In your main.py FastAPI app:

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.neuroforge.services import (
initialize_dataforge_client,
shutdown_dataforge_client,
)
from app.neuroforge.cache import init_context_cache
from app.neuroforge.config import init_settings
from app.neuroforge.api import router as neuroforge_router

@asynccontextmanager
async def lifespan(app: FastAPI):
"""FastAPI lifespan context manager.""" # Startup
init_settings("production")
init_context_cache(max_size=1000)
await initialize_dataforge_client()

    yield

    # Shutdown
    await shutdown_dataforge_client()

app = FastAPI(lifespan=lifespan)
app.include_router(neuroforge_router)

# ============================================================================

# BASIC USAGE

# ============================================================================

# 1. Simple Inference Request

from app.neuroforge.models import InferenceRequest
from app.neuroforge.services import run_inference

request = InferenceRequest(
request_id="req-12345",
domain="literary",
task_type="analysis",
user_query="Analyze the themes in the Odyssey",
max_tokens=2048,
metadata={
"project_id": "proj-1",
"user_id": "user-123",
}
)

result = await run_inference(request)

print(f"Result: {result.output}")
print(f"Latency: {result.latency_ms}ms")
print(f"Context ID: {result.context_pack_id}")

# 2. Direct Context Fetching

from app.neuroforge.services import build_context_for_request

context = await build_context_for_request(request)
print(f"Context blocks: {len(context.text_blocks)}")
print(f"From source: {context.source}")

# 3. Custom Provenance Logging

from app.neuroforge.services import (
post_process_and_log_provenance,
get_dataforge_client,
)

dataforge_client = get_dataforge_client()
result = await post_process_and_log_provenance(
result,
context_pack_id="pack-123",
dataforge_client=dataforge_client,
)

# ============================================================================

# CACHING STRATEGY

# ============================================================================

"""
LRU Context Cache:

- Automatic expiration based on TTL
- Cache key: "ctx:{domain}:{task_type}:{query_hash}"
- Default size: 1000 items
- Default TTL: 3600 seconds

Benefits:

- Reduces DataForge load for repeated queries
- Improves latency (cache hits are instant)
- Graceful degradation if DataForge is slow

Configuration:

- NEUROFORGE_DATAFORGE_CACHE_ENABLED=true/false
- NEUROFORGE_DATAFORGE_CACHE_TTL=seconds
- NEUROFORGE_DATAFORGE_CACHE_SIZE=max_items
  """

from app.neuroforge.cache import get_context_cache

cache = get_context_cache()

# Check metrics

metrics = await cache.get_metrics()
print(f"Cache hit rate: {metrics['hit_rate_percent']}%")
print(f"Size: {metrics['current_size']}/{metrics['max_size']}")

# Manual cache operations

await cache.put(key, context)
cached = await cache.get(key)
await cache.delete(key)
await cache.clear()

# ============================================================================

# CIRCUIT BREAKER RESILIENCE

# ============================================================================

"""
Circuit Breaker Pattern:

- Prevents cascading failures when DataForge is unavailable
- States: CLOSED (normal) → OPEN (failing fast) → HALF_OPEN (recovery) → CLOSED

Settings:

- Failure threshold: 5 consecutive failures
- Recovery time: 60 seconds
- Half-open trial: 1 call to test recovery

Behavior:

- CLOSED: All calls proceed normally
- OPEN: After 5+ failures, calls fail immediately without HTTP attempt
- HALF_OPEN: After recovery window, next call is trial
  - If success → back to CLOSED
  - If failure → back to OPEN

Error Handling:

- Only retries transient errors (5xx, timeouts, network)
- 4xx errors fail immediately (not retried)
- Provenance logging never triggers circuit breaker (non-fatal)
  """

from app.neuroforge.services import get_dataforge_client

client = get_dataforge_client()

# Check circuit state

state = client.circuit_breaker.state # "closed", "open", or "half_open"
metrics = client.circuit_breaker.metrics

print(f"Circuit state: {state}")
print(f"Failures: {metrics.failure_count}")
print(f"Success: {metrics.success_count}")

# ============================================================================

# RETRY STRATEGY

# ============================================================================

"""
Exponential Backoff Retries:

- Transient errors only: 5xx, timeouts, network errors
- NOT retried: 4xx errors (client errors, auth)
- Backoff: delay = initial_delay \* (base \*\* attempt)

Default:

- Max attempts: 3 (2 retries)
- Initial delay: 1 second
- Backoff base: 2.0
- Sequence: 1s, 2s, 4s

Examples:

- Timeout on attempt 1 → wait 1s → retry
- 502 Bad Gateway on attempt 2 → wait 2s → retry
- 400 Bad Request → FAIL immediately (not retried)
- 503 Service Unavailable → retried with backoff
  """

# ============================================================================

# PROVENANCE LOGGING

# ============================================================================

"""
Fire-and-Forget Logging:

- Provenance failures NEVER break the inference pipeline
- Errors are logged but not raised to caller
- Timeout for provenance calls: 5 seconds

Payload includes:

- context_pack_id: Reference to DataForge context used
- request_id: Unique identifier for tracing
- answer: Final output text
- model_name: Which model was used
- latency_ms: Total inference time
- extra: Extended metadata
  - tokens_in/out
  - router decision
  - evaluation scores
  - domain/task info
    """

from app.neuroforge.services import DataForgeProvenancePayload

payload = DataForgeProvenancePayload(
context_pack_id="pack-123",
request_id="req-456",
answer="The answer to your question is...",
model_name="gpt-4-mini",
latency_ms=250,
extra={
"tokens_in": 512,
"tokens_out": 128,
"router_decision": {
"ensemble": ["gpt-4", "claude"],
"winner": "gpt-4-mini",
},
"evaluation_scores": [
{"metric": "quality", "score": 0.92}
],
}
)

# Logged automatically by post_processor

# But can also be called directly:

await client.log_provenance(payload)

# ============================================================================

# TESTING

# ============================================================================

# Run tests

pytest tests/test_dataforge_integration.py -v

# Test scenarios covered:

# 1. Happy path: context fetch and caching

# 2. Cache TTL expiration

# 3. LRU eviction at max size

# 4. Circuit breaker opening after threshold

# 5. Circuit breaker HALF_OPEN recovery

# 6. Provenance logging (non-fatal errors)

# 7. Retry logic with exponential backoff

# 8. Full pipeline integration

# ============================================================================

# MONITORING & DEBUGGING

# ============================================================================

# Health check endpoint

GET /api/v1/inference/health

# Response: {"status": "healthy", "dataforge_circuit_state": "closed"}

# Cache metrics endpoint

GET /api/v1/inference/cache/metrics

# Response: {

# "hits": 1024,

# "misses": 256,

# "hit_rate_percent": 80.0,

# "evictions": 5,

# "current_size": 1000,

# "max_size": 1000

# }

# Clear cache endpoint

POST /api/v1/inference/cache/clear

# Response: {"status": "cleared"}

# Logging

import logging
logging.basicConfig(level=logging.DEBUG)

# Shows circuit breaker state changes, cache operations, retries, etc.

# ============================================================================

# INTEGRATION CHECKLIST

# ============================================================================

# Before deploying to production:

# ✅ Environment variables configured (.env)

# ✅ DataForge running and accessible

# ✅ Tests passing (pytest tests/test_dataforge_integration.py)

# ✅ Health check returning "healthy"

# ✅ Circuit breaker configured appropriately

# ✅ Cache metrics looking good (>70% hit rate ideal)

# ✅ Provenance logging verified in DataForge

# ✅ Retry behavior tested with simulated failures

# ✅ Monitoring/alerting set up for circuit breaker state

# ============================================================================

# TROUBLESHOOTING

# ============================================================================

# Problem: "Circuit breaker is OPEN"

# Solution: Wait recovery_seconds (60s default) or restart, check DataForge health

# Problem: "Failed to fetch context from DataForge"

# Solution:

# 1. Check NEUROFORGE_DATAFORGE_BASE_URL is correct

# 2. Check NEUROFORGE_DATAFORGE_API_KEY is valid

# 3. Check DataForge is running and healthy

# 4. Check network connectivity

# 5. Look at retry logs for details

# Problem: Cache hit rate too low

# Solution:

# 1. Increase NEUROFORGE_DATAFORGE_CACHE_SIZE

# 2. Increase NEUROFORGE_DATAFORGE_CACHE_TTL

# 3. Verify cache keys are stable (query normalization helps)

# Problem: Slow inference

# Solution:

# 1. Check if DataForge is responding slowly

# 2. Look at latency_ms in results

# 3. Check circuit breaker state

# 4. Check retry logs

# ============================================================================

# DATAFORGE ENDPOINTS (ASSUMED)

# ============================================================================

# POST /api/v1/context/fetch

# Request body:

# {

# "project_id": "string",

# "query": "string",

# "domain": "string",

# "max_tokens": 2048,

# "filters": { "author_id": "...", ... }

# }

# Response body:

# {

# "id": "context-pack-id",

# "snippets": [

# {"text": "...", "source_id": "...", "metadata": {...}}

# ],

# "metadata": {"project_id": "...", "retrieval_version": "v1"}

# }

# POST /api/v1/provenance/write

# Request body:

# {

# "context_pack_id": "string",

# "request_id": "string",

# "answer": "string",

# "model_name": "string",

# "latency_ms": int,

# "extra": { "tokens_in": ..., "tokens_out": ..., ... }

# }

# Response: 204 No Content or 200 OK

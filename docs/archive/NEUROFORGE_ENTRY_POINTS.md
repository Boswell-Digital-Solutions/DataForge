# NeuroForge Integration - Starting Points & Entry Points

## 🎯 Where to Start

### For Quick Overview (5 minutes)

→ Read: `NEUROFORGE_QUICK_REFERENCE.md`

### For Complete Understanding (30 minutes)

→ Read: `NEUROFORGE_INTEGRATION_GUIDE.md`

### For Architecture Deep Dive (1 hour)

→ Read: `NEUROFORGE_INTEGRATION_COMPLETE.md`

### For File Inventory

→ Read: `NEUROFORGE_FILES_MANIFEST.md`

## 📁 Key Files by Use Case

### I want to run inference

```python
from app.neuroforge.services import run_inference
from app.neuroforge.models import InferenceRequest

request = InferenceRequest(
    request_id="req-123",
    domain="literary",
    task_type="analysis",
    user_query="Analyze themes"
)

result = await run_inference(request)
print(result.output)
```

**File:** `app/neuroforge/services/inference_pipeline.py`

### I want to fetch context only

```python
from app.neuroforge.services import build_context_for_request
from app.neuroforge.models import InferenceRequest

request = InferenceRequest(...)
context = await build_context_for_request(request)
print(f"Snippets: {len(context.text_blocks)}")
```

**File:** `app/neuroforge/services/context_builder.py`

### I want to check cache metrics

```python
from app.neuroforge.cache import get_context_cache

cache = get_context_cache()
metrics = await cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate_percent']}%")
```

**File:** `app/neuroforge/cache/__init__.py`

### I want to check circuit breaker state

```python
from app.neuroforge.services import get_dataforge_client

client = get_dataforge_client()
state = client.circuit_breaker.state
print(f"Circuit: {state.value}")  # "closed", "open", "half_open"
```

**File:** `app/neuroforge/services/dataforge_client.py`

### I want to configure settings

```python
from app.neuroforge.config import init_settings

settings = init_settings("production")  # Validates all required settings
# or
settings = init_settings("development")  # Relaxed validation
```

**File:** `app/neuroforge/config.py`

### I want to setup FastAPI

```python
from contextlib import asynccontextmanager
from app.neuroforge.services import initialize_dataforge_client, shutdown_dataforge_client
from app.neuroforge.config import init_settings
from app.neuroforge.cache import init_context_cache
from app.neuroforge.api import router as neuroforge_router

@asynccontextmanager
async def lifespan(app):
    # Startup
    init_settings("production")
    init_context_cache(max_size=1000)
    await initialize_dataforge_client()
    yield
    # Shutdown
    await shutdown_dataforge_client()

app = FastAPI(lifespan=lifespan)
app.include_router(neuroforge_router)
```

**File:** `app/neuroforge/api/__init__.py`

### I want to run tests

```bash
pytest tests/test_dataforge_integration.py -v
pytest tests/test_dataforge_integration.py::TestCircuitBreaker -v
pytest tests/test_dataforge_integration.py -k "cache" -v
```

**File:** `tests/test_dataforge_integration.py`

## 🔗 Module Entry Points

### Configuration

```python
from app.neuroforge.config import (
    NeuroForgeSettings,      # Settings class
    get_settings,            # Get singleton instance
    init_settings,           # Initialize with validation
)
```

### Models

```python
from app.neuroforge.models import (
    InferenceRequest,        # Pipeline request
    InferenceResult,         # Pipeline result
    BuiltContext,            # Internal context
    ModelDecision,           # Router output
    EvaluationScore,         # Evaluator output
)
```

### Services

```python
from app.neuroforge.services import (
    # DataForge Client
    DataForgeClient,
    get_dataforge_client,
    initialize_dataforge_client,
    shutdown_dataforge_client,

    # Context Builder
    build_context_for_request,
    prefetch_context,
    clear_context_cache,

    # Post Processor
    post_process_and_log_provenance,
    format_output,
    build_provenance_summary,

    # Pipeline
    run_inference,
    get_inference_status,
)
```

### Cache

```python
from app.neuroforge.cache import (
    LRUContextCache,    # Cache class
    get_context_cache,  # Get singleton
    init_context_cache, # Initialize
)
```

### API

```python
from app.neuroforge.api import router  # FastAPI router
```

## 🚀 Common Workflows

### Workflow 1: Simple Inference

```python
# 1. Create request
request = InferenceRequest(
    request_id="r1",
    domain="literary",
    task_type="analysis",
    user_query="Analyze themes"
)

# 2. Run inference
result = await run_inference(request)

# 3. Access result
print(f"Output: {result.output}")
print(f"Model: {result.model_id}")
print(f"Latency: {result.latency_ms}ms")
```

### Workflow 2: Batch Inference with Prefetch

```python
# 1. Create requests
requests = [
    InferenceRequest(...),
    InferenceRequest(...),
    InferenceRequest(...),
]

# 2. Prefetch contexts
from app.neuroforge.services import prefetch_context
contexts = await prefetch_context(requests)

# 3. Run inferences
results = []
for request in requests:
    result = await run_inference(request)
    results.append(result)
```

### Workflow 3: Cache Monitoring

```python
# Get cache
cache = get_context_cache()

# Get metrics
metrics = await cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate_percent']}%")
print(f"Size: {metrics['current_size']}/{metrics['max_size']}")

# Clear if needed
await cache.clear()
```

### Workflow 4: Circuit Breaker Monitoring

```python
# Get client
client = get_dataforge_client()

# Check state
state = client.circuit_breaker.state
metrics = client.circuit_breaker.metrics

print(f"State: {state.value}")
print(f"Failures: {metrics.failure_count}")
print(f"Successes: {metrics.success_count}")

# If open, wait for recovery
if state == CircuitBreakerState.OPEN:
    print(f"Circuit will recover at {metrics.opened_at + timedelta(seconds=60)}")
```

### Workflow 5: Health Check

```python
# HTTP endpoint
GET /api/v1/inference/health

# Returns
{
    "status": "healthy",
    "dataforge_circuit_state": "closed"
}

# Or programmatically
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get("http://localhost:8000/api/v1/inference/health")
    print(resp.json())
```

## 📊 API Endpoints Reference

| Method | Path                              | Purpose            |
| ------ | --------------------------------- | ------------------ |
| POST   | `/api/v1/inference/`              | Submit inference   |
| GET    | `/api/v1/inference/history`       | Get history (stub) |
| GET    | `/api/v1/inference/cache/metrics` | Cache metrics      |
| POST   | `/api/v1/inference/cache/clear`   | Clear cache        |
| GET    | `/api/v1/inference/health`        | Health check       |

## 🧪 Test Scenarios

### Run All Tests

```bash
pytest tests/test_dataforge_integration.py -v
```

### Run Specific Test Class

```bash
# Circuit Breaker tests
pytest tests/test_dataforge_integration.py::TestCircuitBreaker -v

# Cache tests
pytest tests/test_dataforge_integration.py::TestCacheMetrics -v

# Context Builder tests
pytest tests/test_dataforge_integration.py::TestContextBuilder -v
```

### Run Specific Test

```bash
pytest tests/test_dataforge_integration.py::TestDataForgeClient::test_fetch_context_success -v
```

### Run with Coverage

```bash
pytest tests/test_dataforge_integration.py \
    --cov=app.neuroforge \
    --cov-report=html \
    --cov-report=term
```

## ⚙️ Configuration Reference

### Environment Variables

```bash
# DataForge Connection
NEUROFORGE_DATAFORGE_BASE_URL=http://dataforge:8001
NEUROFORGE_DATAFORGE_API_KEY=your-api-key
NEUROFORGE_DATAFORGE_TIMEOUT=10

# Caching
NEUROFORGE_DATAFORGE_CACHE_ENABLED=true
NEUROFORGE_DATAFORGE_CACHE_TTL=3600
NEUROFORGE_DATAFORGE_CACHE_SIZE=1000

# Circuit Breaker
NEUROFORGE_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
NEUROFORGE_CIRCUIT_BREAKER_RECOVERY_SECONDS=60
NEUROFORGE_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=1

# Retry Policy
NEUROFORGE_RETRY_MAX_ATTEMPTS=3
NEUROFORGE_RETRY_BACKOFF_BASE=2.0
NEUROFORGE_RETRY_INITIAL_DELAY=1.0

# General
NEUROFORGE_ENVIRONMENT=production
NEUROFORGE_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from app.neuroforge.config import NeuroForgeSettings

settings = NeuroForgeSettings(
    dataforge_base_url="http://dataforge:8001",
    dataforge_api_key="key",
    dataforge_cache_ttl=3600,
    circuit_breaker_failure_threshold=5,
    environment="production"
)
```

## 🐛 Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now see all circuit breaker transitions, cache operations, retries, etc.
```

### Check Circuit Breaker State

```python
client = get_dataforge_client()
print(f"State: {client.circuit_breaker.state}")
print(f"Failures: {client.circuit_breaker.metrics.failure_count}")
```

### Check Cache Performance

```python
cache = get_context_cache()
metrics = await cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate_percent']}%")
```

### Monitor Latency

```python
result = await run_inference(request)
print(f"Total latency: {result.latency_ms}ms")
print(f"Context pack: {result.context_pack_id}")
```

## 📚 Documentation Map

```
NEUROFORGE_QUICK_REFERENCE.md
├─ Quick start (5 min read)
├─ Common commands
└─ Troubleshooting

NEUROFORGE_INTEGRATION_GUIDE.md
├─ Installation & setup
├─ Basic usage (detailed)
├─ Advanced features
├─ Testing
├─ Monitoring
└─ Troubleshooting

NEUROFORGE_INTEGRATION_COMPLETE.md
├─ Architecture overview
├─ Design patterns
├─ Implementation details
├─ Performance metrics
└─ Future enhancements

NEUROFORGE_IMPLEMENTATION_INDEX.md
├─ High-level overview
├─ Component summary
├─ Integration checklist
└─ Support resources

NEUROFORGE_FILES_MANIFEST.md
├─ Complete file listing
├─ Code statistics
├─ Feature matrix
└─ Production readiness

tests/test_dataforge_integration.py
├─ 30+ test examples
├─ Test patterns
└─ Usage examples
```

## ✅ Deployment Checklist

- [ ] Read `NEUROFORGE_INTEGRATION_GUIDE.md`
- [ ] Copy `app/neuroforge/` directory
- [ ] Configure `.env` variables
- [ ] Update FastAPI app (lifespan + router)
- [ ] Run `pytest tests/test_dataforge_integration.py`
- [ ] Verify `GET /api/v1/inference/health` returns healthy
- [ ] Test inference: `POST /api/v1/inference/`
- [ ] Check cache metrics: `GET /api/v1/inference/cache/metrics`
- [ ] Monitor circuit breaker state
- [ ] Set up logging/monitoring
- [ ] Deploy to production

## 🎓 Learning Path

1. **5 min** - Read: `NEUROFORGE_QUICK_REFERENCE.md`
2. **15 min** - Read: Usage section of `NEUROFORGE_INTEGRATION_GUIDE.md`
3. **20 min** - Run tests: `pytest tests/test_dataforge_integration.py -v`
4. **30 min** - Read: `NEUROFORGE_INTEGRATION_COMPLETE.md`
5. **1 hour** - Read: Full `NEUROFORGE_INTEGRATION_GUIDE.md`
6. **1 hour** - Integration: Copy files, configure, test
7. **Ongoing** - Monitor, optimize, enhance

## 📞 Getting Help

| Issue             | Solution                                    |
| ----------------- | ------------------------------------------- |
| How do I...?      | Check `NEUROFORGE_QUICK_REFERENCE.md`       |
| Why is it...?     | Check `NEUROFORGE_INTEGRATION_COMPLETE.md`  |
| How do I test...? | See `tests/test_dataforge_integration.py`   |
| What's broken?    | Enable DEBUG logging, check circuit state   |
| How do I monitor? | Use `/api/v1/inference/` endpoints          |
| Need more info?   | Read full `NEUROFORGE_INTEGRATION_GUIDE.md` |

---

**Ready to integrate!** Start with `NEUROFORGE_QUICK_REFERENCE.md` for immediate use.

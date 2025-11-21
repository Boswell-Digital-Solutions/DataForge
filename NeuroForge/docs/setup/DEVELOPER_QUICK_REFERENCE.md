# NeuroForge - Quick Reference Guide for Developers

**TL;DR**: NeuroForge is production-ready but needs 3 critical fixes in 1 week before SaaS launch.

---

## Critical Issues You Must Know

### 1. Champion Model Selector Is NOT Thread-Safe ⚠️

**Location**: `neuroforge_backend/models/champion_model.py`

**Problem**:

```python
class ChampionModelSelector:
    async def update_champion_scores(self, domain, scores):
        self.rolling_trackers[domain].add_score(scores)  # ← RACE CONDITION
```

**Fix Required**:

```python
class ChampionModelSelector:
    def __init__(self):
        self._lock = asyncio.Lock()  # ← ADD THIS

    async def update_champion_scores(self, domain, scores):
        async with self._lock:  # ← ADD THIS
            self.rolling_trackers[domain].add_score(scores)
```

**Why it matters**: With 100 concurrent inferences, champion state can become corrupted, causing incorrect routing.

---

### 2. Frontend Has No Authentication ⚠️

**Location**: `neuroforge_frontend/src/lib/api/` + `neuroforge_backend/routers/inference.py`

**Problem**: Anyone can access any inference. No multi-tenant support. Blocks SaaS deployment.

**Fix Required**: Implement JWT bearer token authentication:

**Frontend** (`neuroforge_frontend/src/lib/api/client.ts`):

```typescript
import { browser } from "$app/environment";

// Add authorization header to all requests
export async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`/api/v1${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      if (browser) window.location.href = "/login";
    }
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }
  return response.json();
}
```

**Backend** (`neuroforge_backend/routers/inference.py`):

```python
from fastapi.security import HTTPBearer, HTTPAuthCredential

security = HTTPBearer()

@router.post("/inference")
async def submit_inference(
    request: InferenceRequest,
    credentials: HTTPAuthCredential = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    # Extract and validate JWT
    token = credentials.credentials
    user_id = verify_jwt_token(token)

    # Scope inference to user
    inference = InferenceLog(
        user_id=user_id,
        domain=request.domain,
        task_type=request.task_type,
        ...
    )
    await persistence.save_inference(session, inference)
```

---

### 3. DataForge is a Single Point of Failure ⚠️

**Location**: `neuroforge_backend/services/context_builder_fixed.py`

**Problem**: If DataForge is down, all new inferences get empty context (degraded quality).

**3-Tier Fallback Strategy** (Phase 2):

**Tier 1**: DataForge API (primary)

```python
try:
    return await dataforge_client.fetch_context(pack_id)
except DataForgeUnavailable:
    logger.warning(f"DataForge unavailable, trying cache")
```

**Tier 2**: Local SQLite cache (24-hour retention)

```python
cached = await db.query(ContextCache).filter_by(pack_id=pack_id).first()
if cached and cache_still_fresh(cached):
    return cached.data
```

**Tier 3**: Domain-specific fallback context

```python
fallback = DOMAIN_FALLBACKS[domain]  # Pre-defined generic contexts
return generate_context_from_template(fallback, task_type)
```

**Health check endpoint**:

```python
@router.get("/health/dataforge")
async def dataforge_status():
    try:
        response = await httpx.get(
            f"{config.dataforge.base_url}/health",
            timeout=5
        )
        healthy = response.status_code == 200
    except:
        healthy = False
    return {"service": "dataforge", "healthy": healthy}
```

**See**: `ACTION_ITEMS_AND_REMEDIATION_PLAN.md` for complete code examples.

---

## Architecture Patterns You Should Use

### The 5-Stage Pipeline (Copy This Pattern)

```python
from dataclasses import dataclass

@dataclass
class StageOutput:
    """Define output from each stage"""
    pass

class StageService:
    """Each service is a singleton"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def process(self, input_data):
        """Process and return typed output"""
        return StageOutput(...)

# Usage: Import singleton, never instantiate
from services.context_builder_fixed import context_builder  # ✅ Correct
await context_builder.build_context(...)

from services.context_builder_fixed import ContextBuilder
cb = ContextBuilder()  # ❌ Wrong - wastes resources
```

### Error Handling Pattern

```python
from fastapi import HTTPException

# Use explicit status codes
if not resource:
    raise HTTPException(status_code=404, detail="Not found")

if not authorized:
    raise HTTPException(status_code=403, detail="Not authorized")

if invalid_input:
    raise HTTPException(status_code=422, detail="Invalid input")
```

### Async/Await Pattern

```python
import asyncio

# ✅ Correct: Parallel execution
tasks = [
    model_router._call_ollama(prompt),
    model_router._call_anthropic(prompt),
    model_router._call_openai(prompt)
]
results = await asyncio.gather(*tasks, return_exceptions=True)

# ❌ Wrong: Sequential execution
result1 = await model_router._call_ollama(prompt)
result2 = await model_router._call_anthropic(prompt)
result3 = await model_router._call_openai(prompt)
```

### Database Access Pattern

```python
from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/inference")
async def submit_inference(
    request: InferenceRequest,
    session: AsyncSession = Depends(get_session)
):
    # Use session from dependency
    async with session.begin():
        await persistence.save_inference(session, data)
        # Auto-commits on exit
```

---

## Common Tasks

### Adding a New Inference Domain

1. **Add to enum** (`neuroforge_backend/main.py`):

```python
class Domain(str, Enum):
    LITERARY = "literary"
    MARKET = "market"
    GENERAL = "general"
    LEGAL = "legal"  # ← NEW
```

2. **Create domain adapter** (`neuroforge_backend/adapters/legal_adapter.py`):

```python
class LegalAdapter(DomainAdapter):
    def preprocess_context(self, context):
        # Add legal-specific preprocessing
        pass

    def postprocess_output(self, output):
        # Add legal-specific formatting
        pass

    def get_evaluation_rubric(self):
        return {
            "relevance": 0.3,
            "legal_accuracy": 0.5,
            "compliance": 0.2
        }
```

3. **Register adapter** (in `prompt_engine.py`):

```python
from adapters.legal_adapter import LegalAdapter

class DomainAdapterFactory:
    ADAPTERS = {
        "literary": LiteraryAdapter(),
        "market": MarketAdapter(),
        "general": GeneralAdapter(),
        "legal": LegalAdapter(),  # ← ADD THIS
    }
```

4. **Test it**:

```python
@pytest.mark.asyncio
async def test_legal_domain_inference():
    request = InferenceRequest(
        domain="legal",
        task_type="analysis",
        context_pack_id="legal-case-123",
        user_query="Is this contract enforceable?"
    )
    response = await submit_inference(request)
    assert response.model_id
    assert response.evaluation_score > 0
```

### Modifying Rate Limits

**Current**: 10 req/min (very aggressive)  
**Recommended**: 100 req/min (reasonable for production)

```python
# In main.py
if os.getenv("SKIP_RATE_LIMIT", "false").lower() != "true":
    limiter = Limiter(key_func=get_remote_address)
    logger.debug("Rate limiter enabled (production mode)")
else:
    limiter = NoOpLimiter()  # For tests

# In routers
@router.post("/inference")
@limiter.limit("100/minute")  # ← CHANGE THIS
async def submit_inference(request: InferenceRequest):
    ...
```

### Adding a New Model Provider

1. **Create client** (`neuroforge_backend/services/providers/groq_client.py`):

```python
class GroqClient:
    def __init__(self):
        self.api_key = config.groq_api_key
        self.client = AsyncGroqClient(api_key=self.api_key)

    async def call(self, prompt: PromptData) -> str:
        response = await self.client.chat.completions.create(
            model="mixtral-8x7b",
            messages=[{"role": "user", "content": prompt.user}],
            max_tokens=prompt.max_tokens
        )
        return response.choices[0].message.content
```

2. **Register in router** (`neuroforge_backend/services/model_router.py`):

```python
class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"  # ← ADD THIS

# In route_to_model():
if provider == ModelProvider.GROQ:
    return await groq_client.call(prompt)
```

3. **Test it**:

```python
@pytest.mark.asyncio
async def test_groq_provider():
    router = model_router
    result = await router.route_to_model(
        prompt=PromptData(...),
        provider="groq"
    )
    assert result.output
    assert result.tokens_used > 0
```

---

## Debugging Guide

### Issue: "Circuit breaker open for DataForge"

**Meaning**: DataForge has failed 5 times in a row. Check status:

```bash
# Check DataForge health
curl http://localhost:8001/health

# View NeuroForge circuit breaker status
curl http://localhost:8000/metrics | grep circuit_breaker_state

# Manually reset circuit (admin only)
curl -X POST http://localhost:8000/admin/circuit-breaker/reset \
  -H "X-API-Key: your-admin-key"
```

### Issue: "Champion model keeps changing"

**Meaning**: Rolling performance average is noisy. Increase window size:

```python
# In champion_model.py
class RollingPerformanceTracker:
    def __init__(self, window_size=50):  # ← INCREASE THIS
        # Larger window = more stable
```

### Issue: "Inference hangs (times out)"

**Check**:

1. LLM evaluator timeout (should be 30s)
2. DataForge context fetch timeout (should be 30s)
3. Model provider timeout (should be 60s total)
4. Database connection pool exhausted

```bash
# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis (if using)
redis-cli info stats
```

### Issue: "Rate limit errors"

**Current**: 10 req/min per IP  
**Solution**: Either increase limit or check if legitimate traffic:

```bash
# See rate limit headers
curl -i http://localhost:8000/api/v1/inference \
  -H "X-API-Key: test" | grep X-RateLimit
```

---

## Performance Tuning Checklist

- [ ] Profile latency per stage: `pytest tests/test_performance.py -v`
- [ ] Check cache hit rates: `curl http://localhost:8000/metrics | grep cache`
- [ ] Monitor database pool: `select count(*) from pg_stat_activity`
- [ ] Check champion model stability: `curl http://localhost:8000/admin/champion/status`
- [ ] Verify rate limits aren't blocking: `curl -v http://localhost:8000/health`

**Latency Targets**:

- Context Builder: <30ms (with cache hit)
- Prompt Engine: <10ms
- Model Router: <50ms (with fallback)
- Evaluator: <20ms
- Post-Processor: <5ms
- **Total**: <100ms average

---

## Testing Checklist Before Deployment

- [ ] Unit tests pass: `pytest tests/test_unit/ -v`
- [ ] Integration tests pass: `pytest tests/test_integration/ -v`
- [ ] Security tests pass: `pytest tests/test_security/ -v`
- [ ] Load test passes: `k6 run tests/load/k6_load_test.js --vus 100`
- [ ] All Phase 1 fixes have test cases
- [ ] Champion thread safety tested under concurrency
- [ ] Frontend JWT auth tested (401/403 responses)
- [ ] DataForge fallback tested (simulate outage)

---

## Deployment Command Reference

```bash
# Development
make dev
# → Runs on http://localhost:8000 with auto-reload

# Tests
make test
# → Runs pytest tests/ -v

# Production
make run
# → Runs with uvicorn, 4 workers

# Docker
make docker-build
make docker-run
# → Builds and runs Docker image

# Check Health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
```

---

## Important Files to Know

| File                                | Purpose                          | When to Edit                  |
| ----------------------------------- | -------------------------------- | ----------------------------- |
| `main.py`                           | FastAPI app, endpoints, lifespan | Add routes, middleware        |
| `config.py`                         | Environment config (Pydantic v2) | Change defaults, add settings |
| `auth.py`                           | API key validation               | Modify auth logic             |
| `services/context_builder_fixed.py` | DataForge integration            | Add caching, retry logic      |
| `services/model_router.py`          | Model selection, fallback        | Add routing strategies        |
| `services/evaluator.py`             | Scoring pipeline                 | Add evaluation dimensions     |
| `models/champion_model.py`          | Champion/challenger tracking     | Adjust promotion thresholds   |
| `database/models.py`                | SQLAlchemy ORM                   | Add persistence tables        |
| `routers/inference.py`              | Inference API endpoints          | Add request/response models   |
| `tests/test_critical_fixes.py`      | Critical path tests              | Add security/resilience tests |

---

## Key Performance Insights

**Cache is critical**:

- Context cache: 25-35% hit rate (saves 20-30ms per request)
- If cache missing: +20-30ms for DataForge fetch

**Model routing complexity**:

- Ollama (local): <20ms
- Anthropic: 50-100ms
- OpenAI: 100-150ms
- Fallback overhead: +10-20ms per attempt

**Database is fine**:

- Connection pool: 20 + 10 overflow (sufficient for 100 concurrent)
- Index on (domain, task_type, created_at) helps queries

---

## Contact & Escalation

**For questions about**:

- Architecture: See `ARCHITECTURE.md`
- Critical fixes: See `ACTION_ITEMS_AND_REMEDIATION_PLAN.md`
- Performance: See `VISUAL_SUMMARY.md`
- Full audit: See `TECHNICAL_DUE_DILIGENCE_REVIEW.md`

**Before deploying to production**: Run through `DEPLOYMENT_CHECKLIST` in `ACTION_ITEMS_AND_REMEDIATION_PLAN.md`

---

**Last Updated**: November 20, 2025  
**Version**: 1.0 (Post-Review)

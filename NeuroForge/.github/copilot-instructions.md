# NeuroForge - AI Agent Instructions

**Dual-stack project**: Backend (Python/FastAPI) + Frontend (SvelteKit/TypeScript)

## Project Overview

**NeuroForge** is a production-grade cognitive inference engine orchestrating multi-provider LLM routing through a **5-stage pipeline**. Serves AuthorForge, DataForge, TradeForge, VibeForge.

**Status**: Phase 4 Complete (Nov 19, 2025) — 95ms avg latency, ensemble voting, distributed caching, real LLM evaluation.

---

## Backend Architecture (Python/FastAPI)

### The 5-Stage Pipeline

```
Request → ①ContextBuilder → ②PromptEngine → ③ModelRouter → ④Evaluator → ⑤PostProcessor → Response
```

Each stage is a **module-level singleton service** in `services/`, outputs a typed `@dataclass` for the next stage.

### ⚠️ Critical Issues

1. **File Corruption**: `services/context_builder.py` is corrupted — **ALWAYS USE** `services/context_builder_fixed.py`
   - Already fixed in: `prompt_engine.py`, `post_processor.py`, `routers/inference.py`, `main.py`

2. **Service Import Pattern** (CRITICAL):
   ```python
   # ✅ CORRECT: Import singleton instance
   from services.context_builder_fixed import context_builder
   await context_builder.build_context()
   
   # ❌ WRONG: Never import the class
   from services.context_builder_fixed import ContextBuilder
   cb = ContextBuilder()  # Creates new instance, wastes connections
   ```

3. **Configuration**: Pydantic v2 with env prefix loading in `config.py`
   ```python
   from config import config
   print(config.dataforge.base_url)  # http://localhost:8001
   print(config.debug)  # True/False
   ```

### Core Services

| Service | Output | Key Features |
|---------|--------|--------------|
| context_builder_fixed | ContextWindow | Fetches/caches context from DataForge |
| prompt_engine | PromptData | Domain-specific prompt templates |
| model_router | ModelResult | Ensemble voting, fallback chains |
| evaluator | EvaluationResult | LLM-based scoring (coherence, relevance, factuality) |
| post_processor | NormalizedOutput | Format normalization, persistence |

### Phase 4 Optimization Layers

- **Ensemble Manager**: 4 voting strategies (unanimous, majority, weighted, confidence)
- **Intelligent Router**: Fallback chains with adaptive routing
- **Prompt Cache**: Exact hash + semantic similarity (25-35% hit rate)
- **Output Cache**: Semantic search caching (15-20% hit rate)
- **Redis Cache**: Distributed caching for multi-instance deployments (70% improvement)
- **Token Optimizer**: Smart context truncation (15-20% reduction)

### Development Workflows

```bash
make setup          # Initial setup
make dev            # Run with auto-reload (port 8000)
make test           # pytest tests/
make lint           # black, mypy
make build-rust     # Compile Rust modules
```

**Test Pattern** (in `conftest.py`):
```python
os.environ["SKIP_RATE_LIMIT"] = "true"  # Disable rate limiter in tests
# Fixtures: mock_config, event_loop
```

### Integration Points

- **DataForge API**: Circuit breaker (5 failures → 60s recovery) + 3 retries
- **Ollama Server**: Local LLMs on `localhost:11434` (models: neural-illm, neural-market, neural-general)
- **Anthropic/OpenAI**: Remote APIs with async httpx clients
- **SQLAlchemy DB**: All records via `repositories/` pattern (async-first)
- **Redis**: Optional distributed cache with graceful fallback
- **Prometheus**: `/metrics` endpoint with per-stage latency histograms

### Common Patterns

**Domain Adapters** (3 types in `adapters/`):
- Each has `preprocess_context()`, `postprocess_output()`, domain-specific evaluation rubrics
- Register new adapters in prompt_engine and evaluator

**Repository Pattern** (all async):
```python
from database import get_session
async def endpoint(session: AsyncSession = Depends(get_session)):
    persistence = PersistenceService(session)
    await persistence.inferences.create(inference)
    await persistence.metrics.record_model_metric(...)
```

**Resilience** (via tenacity + circuitbreaker):
- Retry: 3 attempts, exponential backoff
- Circuit Breaker: 5 failure threshold, 60s recovery
- Fallback: Mock scores if evaluator unavailable

### When Adding Features

| Feature | Location | Pattern |
|---------|----------|---------|
| New pipeline stage | `services/new_stage.py` | Service class + singleton + `@dataclass` output |
| New domain | `adapters/new_domain.py` | Inherit `DomainAdapter` |
| New routing strategy | `services/model_router.py` | Add to `RoutingStrategy` enum |
| New API endpoint | `routers/` + `main.py` | Pydantic model + route handler + `include_router()` |
| New external API | `config.py` + `services/` | Config class + async client singleton |
| New evaluation metric | `adapters/` + `services/llm_evaluator.py` | Domain evaluator method + LLM integration |

---

## Frontend Architecture (SvelteKit/TypeScript)

### Three-Layer Structure

1. **Routes** (`src/routes/`): SvelteKit pages with `+page.svelte` files
2. **Business Logic** (`src/lib/`): API client, stores, types
3. **Design System** (`src/app.css`, Tailwind v4): Forge tokens (forge-ash, forge-ember, forge-brass)

### Key Patterns

**API Integration**:
```typescript
import { neuroforgeApi } from '$lib/api/neuroforge';
const response = await neuroforgeApi.submitInference(request);
if (response.success) { /* use response.data */ }
```

**State Management** (Svelte stores):
```typescript
import { appState, setLoading } from '$lib/stores';
let stats = $appState;  // Auto-subscribe with $ prefix
await setLoading(true);
```

**Types** (centralized in `src/lib/types/index.ts`):
- Enums: `Domain` (literary/market/general), `TaskType`, `ModelProvider`
- Requests: `InferenceRequest`, `EvaluationRequest`
- Responses: `InferenceResult`, `DashboardStats`

### Development

```bash
npm run dev              # Dev server (localhost:5173)
npm run build            # Production build
npm run check            # TypeScript + svelte-check (strict)
npm run check:watch      # Watch mode
```

**Design Colors**: Always use Forge tokens (`bg-forge-ash-100`, `text-forge-ink-900`, etc.)

**Environment** (`.env.local`):
```env
VITE_BACKEND_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

---

## Cross-Stack Considerations

### Request Flow

```
Frontend (SvelteKit) 
  → API Call (Axios, VITE_BACKEND_URL)
  → Backend (FastAPI, routers/inference.py)
  → 5-stage pipeline (services/)
  → Response (InferenceResponse with correlation ID)
  → Frontend update (store update, notification)
```

### Shared Concepts

- **Correlation IDs**: Auto-generated UUIDs for end-to-end tracing (`X-Request-ID` header)
- **Domains**: literary, market, general (used in both frontend + backend)
- **Rate Limiting**: 10 req/min on backend `/inference` endpoint
- **Error Handling**: Frontend checks `response.success` before using `response.data`

---

## Deployment & Monitoring

**Production Checklist**:
- ✅ Context builder imports use `context_builder_fixed` (not corrupted version)
- ✅ Strict mode enabled (`config.strict_mode=True`)
- ✅ Rate limiter active (10 req/min)
- ✅ External API credentials in env vars
- ✅ Redis enabled for multi-instance deployments
- ✅ Prometheus metrics exported (`/metrics` endpoint)

**Prometheus Key Metrics**:
- `inference_pipeline_latency_ms`: End-to-end latency histogram
- `stage_latency_ms`: Per-stage latency (identify bottlenecks)
- `circuit_breaker_state`: 0=closed, 1=open, 2=half_open
- `model_evaluation_score`: Champion model score

**Performance Tuning**:
- Champion model update interval: `config.champion_model_update_interval` (default: 3600s)
- Context token budget: `config.max_context_tokens` (default: 8000)
- Routing strategy: `SPEED_OPTIMIZED` for latency, `COST_OPTIMIZED` for batch, `QUALITY_OPTIMIZED` for accuracy

---

## Quick Reference

| Issue | Solution |
|-------|----------|
| ImportError on context_builder | Use `context_builder_fixed` instead |
| Async/await errors | All services use `async def` and `await`; no blocking calls |
| Config not loading | Check env vars match prefix (e.g., `DATAFORGE_BASE_URL`) |
| High inference latency | Check `stage_latency_ms` Prometheus metric to find bottleneck |
| Circuit breaker stuck open | Wait 60s for recovery timeout; check target service health |
| Database session locked | Always use `Depends(get_session)` dependency per request |
| Frontend API call fails | Verify `VITE_BACKEND_URL` in `.env.local` matches backend port |
| Rate limit exceeded | 10 req/min limit on `/inference`; disable with `SKIP_RATE_LIMIT=true` in tests |

---

## File Organization Principles

- **Separation**: Pipeline stages (services/), domain logic (adapters/), routers, data (repositories/), models, utilities
- **Config**: All settings in `config.py`; never hardcode URLs/keys
- **Async-First**: All services use `async def` for future scalability
- **Module Singletons**: Import service instances, not classes
- **Dataclass Outputs**: Each stage → typed `@dataclass` for next stage
- **Type Safety**: Pydantic v2 (backend), TypeScript (frontend) — strict mode enabled

---

## References

- Backend: `ARCHITECTURE.md`, `README.md` (backend docs folder)
- Frontend: `README.md`, `STARTUP.md` (frontend folder)
- Monitoring: `monitoring/prometheus.yml`, `monitoring/grafana_dashboard.json`
- Rust: `rust/README.md` (token counting, text normalization)
- Tests: `tests/conftest.py` (pytest patterns)


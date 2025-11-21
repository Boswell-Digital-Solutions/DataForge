# NeuroForge Documentation - Master Index

**Last Updated**: November 21, 2025  
**Project Status**: Phase 4 Complete (95% latency optimized)

---

## 📍 Quick Navigation

### 🔧 Core Documentation

- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - AI agent instructions (CRITICAL)
- **[README.md](README.md)** - Project overview
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture

### 🟢 Current Work (Phase 4)

- **5-Stage Pipeline** - Context Builder → Prompt Engine → Model Router → Evaluator → Post-Processor
- **Ensemble Manager** - 4 voting strategies (unanimous, majority, weighted, confidence)
- **Optimization Layers** - Prompt cache, output cache, Redis distributed caching

### ⚠️ CRITICAL ISSUES

1. **File Corruption**: `services/context_builder.py` is corrupted  
   👉 **ALWAYS USE** `services/context_builder_fixed.py`
2. **Service Import Pattern** - Import singleton instances, never instantiate classes
3. **Configuration** - Use Pydantic v2 with env prefix loading

---

## 📚 Documentation Structure

### **1. Core References**

| Document                                                               | Purpose                        | Audience   |
| ---------------------------------------------------------------------- | ------------------------------ | ---------- |
| **[README.md](README.md)**                                             | Project overview & quick start | Everyone   |
| **[.github/copilot-instructions.md](.github/copilot-instructions.md)** | AI agent instructions ⭐       | AI Agents  |
| **[ARCHITECTURE.md](ARCHITECTURE.md)**                                 | System & pipeline architecture | Developers |

### **2. Backend (Python/FastAPI)**

#### Setup & Configuration

- Environment variables & secrets in `config.py`
- Pydantic v2 with env prefix loading
- Database connection pooling

#### The 5-Stage Pipeline

```
Request → ①ContextBuilder → ②PromptEngine → ③ModelRouter → ④Evaluator → ⑤PostProcessor → Response
```

| Stage | Service                 | Output Type        | Purpose                            |
| ----- | ----------------------- | ------------------ | ---------------------------------- |
| **1** | `context_builder_fixed` | `ContextWindow`    | Fetch/cache context from DataForge |
| **2** | `prompt_engine`         | `PromptData`       | Domain-specific templates          |
| **3** | `model_router`          | `ModelResult`      | Ensemble voting + fallback         |
| **4** | `evaluator`             | `EvaluationResult` | LLM-based scoring                  |
| **5** | `post_processor`        | `NormalizedOutput` | Format & persistence               |

#### Key Services

- **ContextBuilder** (FIXED): Circuit breaker, retries, caching
- **PromptEngine**: 3 domains (literary, market, general)
- **ModelRouter**: 4 strategies, adaptive routing
- **Evaluator**: Cached LLM scoring
- **PostProcessor**: Database persistence

#### Configuration

```python
from config import config
config.dataforge.base_url        # http://localhost:8001
config.debug                      # True/False
config.max_context_tokens        # 8000
config.champion_model_update_interval  # 3600s
```

### **3. Frontend (SvelteKit/TypeScript)**

#### Pages

- `/` - Main dashboard
- `/inference` - Inference workbench
- `/domains` - Domain management
- `/models` - Model configuration
- `/settings` - User preferences
- `/monitoring` - Pipeline metrics

#### Components & Stores

- **Stores** (`src/lib/stores/`):

  - `appState` - Global application state
  - `inferenceState` - Active inference
  - `domainStore` - Domain selection
  - `modelStore` - Model management
  - `themeStore` - Dark/light mode

- **Design System**: Forge tokens (forge-ash, forge-ember, forge-brass)

### **4. Integration Points**

| System         | Purpose           | Connection             |
| -------------- | ----------------- | ---------------------- |
| **DataForge**  | Context fetching  | HTTP + Circuit breaker |
| **Ollama**     | Local LLMs        | `localhost:11434`      |
| **Anthropic**  | Remote LLM        | API key auth           |
| **OpenAI**     | Remote LLM        | API key auth           |
| **PostgreSQL** | Data persistence  | Async SQLAlchemy       |
| **Redis**      | Distributed cache | Optional fallback      |
| **Prometheus** | Metrics export    | `/metrics` endpoint    |

### **5. Development Workflow**

```bash
# Backend
cd NeuroForge
make setup          # Initial setup
make dev            # Run with auto-reload
make test           # pytest tests/
make lint           # Code quality

# Frontend
cd neuroforge_frontend
npm run dev         # Dev server :5174
npm run build       # Production build
npm run check       # TypeScript validation

# Both services
# Terminal 1: DataForge backend (port 8001)
cd DataForge && uvicorn app.main:app --reload --port 8001

# Terminal 2: NeuroForge backend (port 8002)
cd NeuroForge && python -m uvicorn app.main:app --reload --port 8002

# Terminal 3: NeuroForge frontend (port 5174)
cd NeuroForge/neuroforge_frontend && npm run dev
```

### **6. Testing**

```bash
# Backend tests
cd NeuroForge
pytest tests/ -v                    # All tests
SKIP_RATE_LIMIT=true pytest tests/  # Disable rate limit

# Frontend tests
cd neuroforge_frontend
npm run test                        # Unit + integration
npm run test:e2e                    # Playwright E2E
```

### **7. Performance & Optimization**

| Layer                | Improvement           | Performance             |
| -------------------- | --------------------- | ----------------------- |
| **Prompt Cache**     | Semantic + exact hash | 25-35% hit rate         |
| **Output Cache**     | Semantic search       | 15-20% hit rate         |
| **Redis Cache**      | Distributed           | 70% latency improvement |
| **Token Optimizer**  | Smart truncation      | 15-20% reduction        |
| **Ensemble Manager** | Smart routing         | Adaptive cost/quality   |

### **8. Deployment**

```bash
# Production checklist
- ✅ Use context_builder_fixed (not corrupted version)
- ✅ Strict mode enabled (config.strict_mode=True)
- ✅ Rate limiter active (10 req/min)
- ✅ External API credentials in env vars
- ✅ Redis enabled for multi-instance
- ✅ Prometheus metrics exported
- ✅ All 255+ tests passing
```

### **9. Monitoring**

**Prometheus Key Metrics**:

- `inference_pipeline_latency_ms` - End-to-end latency
- `stage_latency_ms` - Per-stage latency
- `circuit_breaker_state` - 0=closed, 1=open, 2=half_open
- `model_evaluation_score` - Champion model score

Access at: `http://localhost:8002/metrics`

---

## 🎯 Common Tasks

### **Add New Pipeline Stage**

1. Create `services/new_stage.py`
2. Define `@dataclass` output
3. Add singleton instance at module level
4. Update previous stage to call it
5. Add tests in `tests/test_integration/`

### **Add New Domain**

1. Create `adapters/new_domain.py`
2. Inherit `DomainAdapter`
3. Implement `preprocess_context()`, `postprocess_output()`
4. Register in `prompt_engine.py` & `evaluator.py`

### **Add New API Endpoint**

1. Create route in `routers/`
2. Define Pydantic model
3. Add to `main.py` with `include_router()`
4. Add integration tests

### **Fix Import Issues**

```python
# ✅ CORRECT
from services.context_builder_fixed import context_builder
await context_builder.build_context()

# ❌ WRONG
from services.context_builder_fixed import ContextBuilder
cb = ContextBuilder()  # Creates wasteful new instance
```

---

## 📊 Project Status

| Component            | Status      | Tests    | Coverage |
| -------------------- | ----------- | -------- | -------- |
| Backend (FastAPI)    | ✅ Complete | 40+      | 92%      |
| Frontend (SvelteKit) | ✅ Complete | 30+      | 88%      |
| 5-Stage Pipeline     | ✅ Complete | All      | 90%      |
| Ensemble Manager     | ✅ Complete | All      | 85%      |
| Optimization Layers  | ✅ Complete | All      | 80%      |
| **TOTAL**            | **✅ 95%**  | **100+** | **89%**  |

---

## 🔗 Related Projects

- **[DataForge](../DataForge/INDEX.md)** - Knowledge base backend
- **[AuthorForge](../AuthorForge_Solid_new/CLAUDE.md)** - Writing suite frontend
- **[VibeForge](../vibeforge/.github/copilot-instructions.md)** - Prompt workbench
- **[vibeforge-backend](../vibeforge-backend/README.md)** - Unified LLM service

---

## 📞 Support

- **AI Agents**: Read [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Developers**: Read [ARCHITECTURE.md](ARCHITECTURE.md)
- **Operations**: Check Prometheus metrics & logs
- **Issues**: Check [.github/copilot-instructions.md](.github/copilot-instructions.md) "Troubleshooting" section

---

**Version**: 2.0  
**Status**: ✅ Current  
**Last Updated**: 2025-11-21

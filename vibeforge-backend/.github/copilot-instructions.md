# VibeForge Backend — AI Coding Agent Instructions

## Architecture Overview

**VibeForge** is a high-performance prompt engineering backend combining **FastAPI** (Python) with **Rust (PyO3)** performance layer. The design supports both a JSON MVP storage layer and future Postgres/vector DB migration without API changes.

### System Design
```
Frontend (HTTP) ──→ FastAPI (Python) ──→ Rust PyO3 Layer ──→ Persistence
                        │                       │
                        ├─ Routers:             ├─ forge_core: Types (TokenUsage, ModelRun, RunStatus)
                        │  • vibeforge (prod)   ├─ forge_prompt: Token estimation, prompt building
                        │  • dataforge (stub)   ├─ forge_data: Document ingestion stubs
                        │  • neuroforge (stub)  └─ forge_eval: Scoring/hyperparameter stubs
                        │
                        ├─ Models: Pydantic schemas (app/models/vibeforge_models.py)
                        └─ Storage: json_storage.py (swappable for Postgres)
```

### Critical Architectural Decisions

1. **Rust-Python Bridge via Maturin + PyO3**
   - Rust types use `#[pyclass]` + `#[pymethods]` to expose to Python
   - `#[pyo3(get, set)]` creates automatic property accessors
   - Serde handles JSON serialization across boundary
   - **Important**: Currently only `forge_prompt` is built as PyO3 extension (see `pyproject.toml` `module-name = "vibeforge_prompt"`)
   - Import as: `from vibeforge_prompt import estimate_tokens_precise, build_prompt` (not `vibeforge_backend.*`)
   - Future: Multi-module builds will expose `forge_core`, `forge_data`, `forge_eval` if needed

2. **Storage Layer Abstraction**
   - `app/storage/json_storage.py` defines all CRUD operations (create, get, list, update)
   - Currently persists to JSON in `data/` directory (runs.json, contexts.json, evaluations.json)
   - **To migrate to Postgres**: Replace entire json_storage.py module without touching routers or models
   - All operations return `Dict[str, Any]` for consistency with Pydantic

3. **Pydantic as API Contract**
   - Every Pydantic model in `app/models/vibeforge_models.py` must have `json_schema_extra` with example
   - Every router endpoint MUST have `response_model=SomeModel` for validation + OpenAPI docs
   - Pydantic validates request bodies; mismatch raises 422 Unprocessable Entity
   - Storage layer returns dicts that Pydantic models deserialize

4. **Router Organization** (`app/routers/`)
   - `vibeforge.py`: Production endpoints for model runs, contexts, history (study this first)
   - `dataforge.py`: Placeholder for document ingestion (stub implementations)
   - `neuroforge.py`: Placeholder for evaluation/scoring (stub implementations)
   - All routers prefixed with `/v1/{router_name}` for API versioning

## Build & Development Workflow

### Environment Setup
```bash
# One-time setup
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]              # Install dev dependencies
maturin develop                    # Build Rust + link Python (~2-3 min first time)
```

### Daily Development Workflows

**Python-Only Changes** (no Rust edits):
```bash
uvicorn app.main:app --reload --port 8000
# Auto-reloads on .py file changes; state persists in JSON files
```

**Rust Changes** (editing `rust/*/src/lib.rs`):
```bash
# Terminal 1: Monitor + rebuild Rust
maturin develop                    # Fast debug build (~30s), installs as vibeforge_prompt module
# Or: maturin develop --release    # Full optimized build (~2-3 min), slower but better perf

# Terminal 2: Restart FastAPI server
# Simply edit python/app/main.py (e.g., add whitespace) to trigger reload,
# or stop/restart uvicorn: uvicorn app.main:app --reload --port 8000
```

### Critical Build Commands
- **Debug build** (fast): `maturin develop` (~30s, recommended for development)
- **Release build**: `maturin develop --release` (~3 min, optimized for production)
- **Full rebuild**: `rm -rf rust/target && maturin develop --release`
- **Verify Rust import**: `python -c "from vibeforge_prompt import estimate_tokens_precise; print(estimate_tokens_precise('test'))"`
- **Run tests**: `pytest tests/ -v` (or `pytest tests/test_*.py -v` for specific modules)
- **Docker**: `docker build -t vibeforge-backend . && docker run -p 8000:8000 vibeforge-backend:latest`

## Code Organization & Patterns

### Request/Response Flow (The Three-Layer Pattern)

Every endpoint follows this pattern:
1. **Router** (`app/routers/*.py`): Define endpoint, validate request via Pydantic
2. **Storage** (`app/storage/json_storage.py`): Perform CRUD, return `Dict[str, Any]`
3. **Response Model** (Pydantic): Deserialize dict → model instance → JSON

Example from `vibeforge.py:create_run()`:
```python
@router.post("/run", response_model=ModelRunModel, status_code=201)
async def create_run(request: CreateRunRequest):
    result = json_storage.create_run(
        workspace_id=request.workspace_id,
        model=request.model,
        prompt=request.prompt,
        # ... other fields
    )
    return ModelRunModel(**result)  # Pydantic validates + serializes
```

The storage layer always returns plain dicts so it's swappable with a database layer:
```python
def create_run(...) -> Dict[str, Any]:
    import uuid
    run = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "model": model,
        # ... all fields matching ModelRunModel
    }
    data = _load_json(RUNS_FILE)
    data.append(run)
    _save_json(RUNS_FILE, data)
    return run
```

### Adding a New Endpoint

1. **Define Pydantic request/response** in `app/models/vibeforge_models.py`:
   ```python
   class MyRequest(BaseModel):
       field: str
       class Config:
           json_schema_extra = {"example": {"field": "value"}}
   
   class MyResponse(BaseModel):
       id: str
       result: str
       class Config:
           json_schema_extra = {"example": {"id": "123", "result": "..."}}
   ```

2. **Implement storage function** in `app/storage/json_storage.py`:
   ```python
   def create_something(field: str) -> Dict[str, Any]:
       data = _load_json(DATA_FILE)
       item = {"id": str(uuid.uuid4()), "field": field, ...}
       data.append(item)
       _save_json(DATA_FILE, data)
       return item
   ```

3. **Add router endpoint** in appropriate router file:
   ```python
   @router.post("/endpoint", response_model=MyResponse, status_code=201)
   async def my_endpoint(request: MyRequest):
       result = json_storage.create_something(request.field)
       return MyResponse(**result)
   ```

### Rust Type Guidelines

- **Every public type** must have `#[pyclass]` + `#[pymethods]` to expose to Python
- **Struct fields** use `#[pyo3(get, set)]` for automatic property accessors (don't write manual getters)
- **Serialization**: Always derive `Serialize, Deserialize` for JSON round-tripping
- **Debugging**: Implement `__repr__()` in `#[pymethods]` for readable output
- **Organization**: Keep logic in `forge_prompt`, types in `forge_core`, stubs in data/eval crates

Example from `forge_core`:
```rust
#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct ModelRun {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub model: String,
}

#[pymethods]
impl ModelRun {
    #[new]
    pub fn new(id: String, model: String) -> Self { ... }
    
    pub fn __repr__(&self) -> String {
        format!("ModelRun(id={}, model={})", self.id, self.model)
    }
}
```

### Token Estimation Functions

Located in `rust/forge_prompt/src/lib.rs` (compiled to `vibeforge_prompt` module):
- **`estimate_tokens(text: str) -> int`**: Naive method (~4 chars = 1 token), fast MVP-level
- **`estimate_tokens_precise(text: str) -> int`**: Word-count with punctuation adjustment, more accurate
- **`build_prompt(contexts: List[str], prompt: str) -> str`**: Merges contexts + user prompt with separators
- **`estimate_tokens_for_prompt(contexts, prompt) -> int`**: Builds combined prompt then estimates tokens
- **Usage**: Called by `llm_service.py` to estimate token counts before/after LLM calls; swappable for tiktoken later

## Data Flow Example: Creating a Run

1. **Client** → `POST /v1/vibeforge/run` with `CreateRunRequest { workspace_id, model, prompt, context_ids, ... }`
2. **Router** (`vibeforge.py:create_run()`) validates request via Pydantic, calls storage layer
3. **Storage** (`json_storage.create_run()`) generates UUID + timestamps, builds `ModelRun` dict, appends to runs.json
4. **Response** dict deserialized via `ModelRunModel` Pydantic schema → JSON serialized → client receives run object
5. **Result**: Data persisted in `data/runs.json` with full run history

## Debugging & Testing Commands

### Verify Rust Compilation
```bash
# Verify vibeforge_prompt module loads and functions are available
python -c "from vibeforge_prompt import estimate_tokens_precise, build_prompt; \
  print('Available:', dir()); \
  print('Test estimate_tokens_precise(\"hello\"):', estimate_tokens_precise('hello'))"
```

### Test Endpoints with curl
```bash
# Health check
curl http://localhost:8000/health

# Create run (requires workspace_id, model, prompt)
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"test-ws","model":"gpt-4","prompt":"What is AI?"}'

# Get run by ID
curl http://localhost:8000/v1/vibeforge/run/{run_id}

# List runs
curl http://localhost:8000/v1/vibeforge/runs?workspace_id=test-ws

# View OpenAPI schema
curl http://localhost:8000/openapi.json | jq
```

### Inspect JSON Data
```bash
# View all persisted runs
cat data/runs.json | jq

# Filter runs by workspace
jq '.[] | select(.workspace_id=="test-ws")' data/runs.json
```

### Test Rust Functions Directly
```bash
python3 << 'EOF'
from vibeforge_prompt import estimate_tokens, estimate_tokens_precise, build_prompt

# Token estimation
text = "This is a test prompt"
print(f"Tokens (naive): {estimate_tokens(text)}")
print(f"Tokens (precise): {estimate_tokens_precise(text)}")

# Prompt building
contexts = ["Context 1: System rules", "Context 2: Code style"]
prompt = "Implement a function"
built = build_prompt(contexts, prompt)
print(f"Built prompt length: {len(built)} chars")
print(f"Estimated tokens for built prompt: {estimate_tokens_precise(built)}")
EOF
```

## Critical Files Reference

| File | Purpose | Key Functions/Patterns |
|------|---------|---|
| `python/app/main.py` | FastAPI app entry, CORS setup, router inclusion | `app = FastAPI(...)`, CORS middleware config |
| `python/app/routers/vibeforge.py` | Production endpoints (study this first) | `@router.post("/run")`, `create_run()`, data flow orchestration |
| `python/app/models/vibeforge_models.py` | All Pydantic request/response schemas | Every model needs `json_schema_extra = {"example": {...}}` |
| `python/app/storage/json_storage.py` | Persistence layer (swap entire file for DB) | `_load_json()`, `_save_json()`, `create_run()`, `get_run()`, `list_runs()` |
| `python/app/repositories/runs_file.py` | Repository pattern wrapper (higher-level storage API) | Used by routers instead of direct json_storage calls |
| `python/app/services/llm_service.py` | LLM integration (mock or real provider) | `get_llm_service()`, `call_llm()`, supports claude/openai/ollama |
| `rust/forge_core/src/lib.rs` | Core types exposed to Python | `TokenUsage`, `RunStatus`, `ModelRun` with `#[pyclass]` (not currently exposed, but documented) |
| `rust/forge_prompt/src/lib.rs` | **PRIMARY RUST MODULE** - Token estimation & prompt building | `estimate_tokens()`, `estimate_tokens_precise()`, `build_prompt()`, `estimate_tokens_for_prompt()` |
| `rust/forge_data/src/lib.rs` | Document ingestion stubs (not yet built as extension) | Placeholder for future document chunking/embedding |
| `rust/forge_eval/src/lib.rs` | Evaluation scoring stubs (not yet built as extension) | Placeholder for future hyperparameter tuning |
| `pyproject.toml` | Maturin config, Python dependencies | `module-name = "vibeforge_prompt"`, `manifest-path = "rust/forge_prompt/Cargo.toml"` |
| `QUICKREF.md` | Developer cheat sheet | Quick command reference |
| `ARCHITECTURE.md` | Deep architectural reference | Detailed system design & decision rationale |

## Common Pitfalls & Prevention

| Pitfall | Prevention | Example |
|---------|-----------|---------|
| **Forgetting Rust rebuild after .rs changes** | Always run `maturin develop` before restarting server; Python won't see changes otherwise | After editing `rust/*/src/lib.rs`, run rebuild in one terminal while keeping uvicorn running |
| **Pydantic model ↔ storage mismatch** | Keep model schema in sync with dict keys returned by storage layer | If adding field to `ModelRunModel`, add it to both storage `create_run()` dict AND Pydantic class |
| **Missing `response_model` on endpoints** | Every endpoint needs `response_model=SomeModel` for type validation & OpenAPI docs | `@router.post("/endpoint", response_model=MyResponse)` |
| **Async/await confusion** | All FastAPI endpoints are `async def`; always use `await` for async calls | Use `async def my_endpoint():` and `await json_storage.get_run(...)` if storage is async |
| **Hardcoded file paths** | Use `DATA_DIR = Path(__file__).parent / "data"` pattern for relative paths | Enables portability across dev/Docker/CI environments |
| **Not adding `json_schema_extra` to Pydantic models** | Every model needs example in Config; OpenAPI docs depend on it | Add `class Config: json_schema_extra = {"example": {...}}` |

## Project-Specific Design Patterns

### Repository Pattern for Storage Abstraction
```python
# app/repositories/runs_file.py provides high-level API
from app.repositories.runs_file import get_runs_repo
runs_repo = get_runs_repo()  # Singleton per request lifecycle

# Router uses repo, not storage directly
result = runs_repo.create_run(...)
run = runs_repo.get_run(run_id)
```
**Why**: Separates router logic from persistence mechanics; easier to swap storage implementations.

### Service Layer for External Integrations
```python
# app/services/llm_service.py wraps LLM provider calls
from app.services.llm_service import get_llm_service
llm_service = get_llm_service()

# Call LLM with error handling, retries, model detection
llm_response = await llm_service.call_llm(model="gpt-4", prompt=prompt)
# Returns LLMResponse with .content, .prompt_tokens, .completion_tokens, .latency_ms

# Supports:
# - claude-3-opus, claude-3-sonnet (Anthropic)
# - gpt-4, gpt-3.5-turbo (OpenAI)
# - ollama:mistral, ollama:llama2 (Local)
```
**Why**: Centralizes error handling, token counting, provider routing, and mocking; routers stay clean.

### Token Integration in Routers
Every run creation includes token counting via LLM service:
```python
# In vibeforge.py:create_run()
llm_response = await llm_service.call_llm(model=request.model, prompt=request.prompt)
runs_repo.update_run(
    run_id,
    tokens_used={
        "prompt_tokens": llm_response.prompt_tokens,
        "completion_tokens": llm_response.completion_tokens,
        "total_tokens": llm_response.total_tokens,
    }
)
```

### Temporal Fields Pattern
Every run record includes:
- `created_at`: ISO 8601 timestamp (set at creation)
- `started_at`: ISO 8601 timestamp (set when execution begins, optional)
- `completed_at`: ISO 8601 timestamp (set when execution ends, optional)
- `duration_ms`: Total milliseconds (calculated from started_at to completed_at)

This pattern enables accurate run duration tracking and historical analysis.

## Future Evolution

- **Storage**: Replace `json_storage.py` entirely with SQLAlchemy + Postgres without changing routers or Pydantic models
- **Vector DB**: Integrate Qdrant into `forge_data` for semantic document search and RAG
- **Real evals**: Implement `forge_eval` functions for hyperparameter optimization and A/B testing
- **Authentication**: Add JWT bearer tokens to main.py CORS + endpoint decorators
- **Observability**: Add OpenTelemetry spans in routers for distributed tracing and performance monitoring
- **Caching**: Implement Redis layer for token estimation and frequently-accessed contexts

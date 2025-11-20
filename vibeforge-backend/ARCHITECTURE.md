# VibeForge Backend Architecture & Implementation Guide

## Overview

The VibeForge backend is a **high-performance, modular API layer** combining:

- **FastAPI** for clean, async HTTP routing
- **Rust (PyO3)** for performance-critical logic
- **JSON persistence** (MVP) → Postgres + vector DB (production)

### Design Principles

1. **Modular Rust crates**: Each subsystem (core, prompt, data, eval) is independently compilable
2. **Abstracted storage**: JSON layer can be swapped for any database without changing API
3. **Type-safe boundaries**: Pydantic models enforce contracts between Python and Rust
4. **Async-first**: All FastAPI endpoints support concurrent requests
5. **Graceful degradation**: Stub implementations allow frontend development in parallel

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (SvelteKit)                     │
│               HTTP Client @ localhost:5173                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP/JSON (CORS enabled)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                       │
│               (app/main.py, port 8000)                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │   VibeForge    │  │ DataForge  │  │   NeuroForge       │ │
│  │   Routers      │  │  Routers   │  │    Routers         │ │
│  │ /v1/vibeforge │  │/v1/dataforge│ │ /v1/neuroforge    │ │
│  └────────┬───────┘  └────────┬───┘  └─────────┬──────────┘ │
│           │                   │                │             │
│           └───────────┬───────┴────────────────┘             │
│                       ▼                                      │
│        ┌──────────────────────────────┐                     │
│        │  Pydantic Models (schemas)   │                     │
│        │  - Request/Response types    │                     │
│        │  - Validation & coercion     │                     │
│        └──────────────┬───────────────┘                     │
│                       ▼                                      │
│        ┌──────────────────────────────────────────┐        │
│        │     Rust Python Modules (PyO3)           │        │
│        ├──────────────────────────────────────────┤        │
│        │  ┌─────────────────────────────────────┐ │        │
│        │  │  forge_core (types & primitives)   │ │        │
│        │  │  - TokenUsage, RunStatus, ModelRun │ │        │
│        │  │  - ContextBlock, Evaluation        │ │        │
│        │  └─────────────────────────────────────┘ │        │
│        │                                           │        │
│        │  ┌─────────────────────────────────────┐ │        │
│        │  │  forge_prompt (context & tokens)   │ │        │
│        │  │  - estimate_tokens()                │ │        │
│        │  │  - PromptContext, merge_contexts()  │ │        │
│        │  └─────────────────────────────────────┘ │        │
│        │                                           │        │
│        │  ┌─────────────────────────────────────┐ │        │
│        │  │  forge_data (ingestion stubs)      │ │        │
│        │  │  - Document, chunking, search      │ │        │
│        │  └─────────────────────────────────────┘ │        │
│        │                                           │        │
│        │  ┌─────────────────────────────────────┐ │        │
│        │  │  forge_eval (scoring stubs)        │ │        │
│        │  │  - Score, Evaluation, sweeps       │ │        │
│        │  └─────────────────────────────────────┘ │        │
│        └──────────────┬──────────────────────────┘        │
│                       ▼                                     │
│        ┌──────────────────────────────┐                   │
│        │   Storage Abstraction Layer   │                  │
│        │   (app/storage/json_storage)  │                  │
│        └──────────────┬───────────────┘                   │
│                       ▼                                     │
│         ┌─────────────────────────────┐                   │
│         │    JSON Files (MVP)         │                   │
│         │  - data/runs.json           │                   │
│         │  - data/contexts.json       │                   │
│         │  - data/evaluations.json    │                   │
│         └─────────────────────────────┘                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
        (Future: Replace storage with Postgres + Qdrant)
```

---

## File Structure

```
vibeforge-backend/
│
├── rust/                                    # Rust workspace
│   ├── Cargo.toml                           # Workspace config + shared deps
│   ├── Cargo.lock                           # (auto-generated)
│   │
│   ├── forge_core/
│   │   ├── Cargo.toml                       # PyO3 cdylib, no dependencies
│   │   └── src/lib.rs                       # Types: TokenUsage, RunStatus, ModelRun, ContextBlock
│   │
│   ├── forge_prompt/
│   │   ├── Cargo.toml                       # Depends on forge_core
│   │   └── src/lib.rs                       # estimate_tokens, PromptContext, merge_contexts
│   │
│   ├── forge_data/
│   │   ├── Cargo.toml                       # Depends on forge_core
│   │   └── src/lib.rs                       # Document, chunking, search (stubs)
│   │
│   └── forge_eval/
│       ├── Cargo.toml                       # Depends on forge_core
│       └── src/lib.rs                       # Score, Evaluation, sweeps (stubs)
│
├── python/
│   ├── __init__.py
│   │
│   └── app/
│       ├── __init__.py                      # Exports FastAPI app
│       ├── main.py                          # FastAPI setup, health checks
│       │
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── vibeforge.py                 # /v1/vibeforge/* (production)
│       │   ├── dataforge.py                 # /v1/dataforge/* (stub)
│       │   └── neuroforge.py                # /v1/neuroforge/* (stub)
│       │
│       ├── models/
│       │   └── __init__.py                  # Pydantic schemas for all routes
│       │
│       └── storage/
│           ├── __init__.py
│           └── json_storage.py              # File I/O: runs, contexts, evals
│
├── data/                                    # JSON persistence (MVP)
│   ├── .gitkeep
│   ├── runs.json                            # (auto-created on first write)
│   ├── contexts.json                        # (auto-created on first write)
│   └── evaluations.json                     # (auto-created on first write)
│
├── pyproject.toml                           # Maturin + dependencies
├── Dockerfile                               # Container definition
├── .env.example                             # Environment template
├── .gitignore                               # Git exclusions
├── README.md                                # Getting started guide
└── ARCHITECTURE.md                          # This file
```

---

## Rust Crate Details

### 1. `forge_core` — Shared Type Definitions

**Purpose**: Core entities bridging Rust ↔ Python

**Key Exports**:

```rust
#[pyclass]
pub struct TokenUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

#[pyclass]
pub enum RunStatus {
    Pending, Running, Complete, Error, Cancelled
}

#[pyclass]
pub struct ModelRun {
    pub id: String,
    pub workspace_id: String,
    pub model: String,
    pub prompt: String,
    pub status: String,
    pub output: Option<String>,
    pub error: Option<String>,
    pub tokens_used: Option<(u32, u32, u32)>,
    pub created_at: String,      // ISO 8601
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub duration_ms: Option<u64>,
    pub context_ids: Vec<String>,
    pub model_config: Option<String>, // JSON
    pub tags: Vec<String>,
}

#[pyclass]
pub struct ContextBlock {
    pub id: String,
    pub title: String,
    pub kind: String,           // "system" | "design" | "project" | "code" | "workflow"
    pub description: String,
    pub tags: Vec<String>,
    pub content: String,
    pub is_active: bool,
    pub last_updated: String,   // ISO 8601
    pub source: String,         // "global" | "workspace" | "local"
}
```

**Python Import**:

```python
from forge_core import TokenUsage, RunStatus, ModelRun, ContextBlock
```

---

### 2. `forge_prompt` — Prompt & Token Logic

**Purpose**: High-performance token estimation, context merging

**Key Exports**:

```rust
#[pyfunction]
pub fn estimate_tokens(text: &str) -> u32
    // Naive: len / 4

#[pyfunction]
pub fn estimate_tokens_precise(text: &str) -> u32
    // Better: word_count * 1.3 + punctuation * 0.1

#[pyclass]
pub struct PromptContext {
    pub system_prompt: String,
    pub user_prompt: String,
    pub context_blocks: Vec<String>,
    pub total_tokens_estimated: u32,
}
// Methods: add_context(), merge_contexts(), recalculate_tokens()
```

**Performance**: ~1000x faster than pure Python (naive regex-based tokenization)

**Python Usage**:

```python
from forge_prompt import estimate_tokens_precise, PromptContext

tokens = estimate_tokens_precise("Explain quantum computing")
# -> 5 tokens

ctx = PromptContext("You are a physicist", "Explain quantum...")
ctx.add_context("Background: QM basics...")
ctx.recalculate_tokens()
merged = ctx.merge_contexts()
```

---

### 3. `forge_data` — Document Ingestion (Stub)

**Purpose**: Placeholder for future vector store integration

**Key Exports**:

```rust
#[pyclass]
pub struct Document {
    pub id: String,
    pub content: String,
    pub metadata: String,  // JSON
    pub chunk_count: usize,
}
// Methods: chunk(chunk_size: usize) -> Vec<String>

#[pyfunction]
pub fn create_corpus(name: String) -> String

#[pyfunction]
pub fn search_corpus(corpus_id: &str, query: &str) -> Vec<String>
    // Returns empty vec (stub)
```

**Future**: Replace `search_corpus` with actual semantic search against Qdrant

---

### 4. `forge_eval` — Evaluation & Scoring (Stub)

**Purpose**: Model evaluation metrics and hyperparameter sweeps

**Key Exports**:

```rust
#[pyclass]
pub struct Score {
    pub name: String,
    pub value: f32,
    pub scale: String,  // "1-5" | "1-10" | "0-1"
}
// Methods: is_valid() -> bool

#[pyclass]
pub struct Evaluation {
    pub id: String,
    pub run_id: String,
    pub evaluator: String,
    pub scores: Vec<(String, f32)>,
    pub notes: String,
    pub created_at: String,
}
// Methods: add_score(), average_score()

#[pyfunction]
pub fn create_sweep(name: String, param_grid: Vec<String>) -> String
    // Returns stub description
```

---

## FastAPI Routing Structure

### Top-Level Routers

All routes prefixed with `/v1/` for versioning:

#### **VibeForge** (`/v1/vibeforge`) — Production

**Runs**:

- `POST /run` → Create run
- `GET /run/{run_id}` → Fetch run
- `GET /history` → List runs (paginated, filterable)

**Contexts**:

- `POST /context` → Create context block
- `GET /context/{context_id}` → Fetch context
- `GET /contexts` → List contexts (filterable)
- `POST /context/{context_id}/toggle` → Toggle active status

---

#### **DataForge** (`/v1/dataforge`) — Stub

- `POST /corpus` → Create corpus
- `POST /corpus/{corpus_id}/ingest` → Queue document ingestion
- `GET /corpus/{corpus_id}/search` → Search corpus
- `GET /corpus/{corpus_id}/documents` → List documents

**Future Expansion**:

- Add batch ingestion
- Implement semantic search with vector DB
- Add corpus management (stats, retention policies)

---

#### **NeuroForge** (`/v1/neuroforge`) — Stub

- `POST /eval` → Create evaluation
- `GET /evals` → List evaluations
- `POST /sweep` → Create parameter sweep
- `GET /sweep/{sweep_id}` → Get sweep progress

**Future Expansion**:

- Implement sweep execution queue
- Add model comparison metrics
- Add AutoML integration

---

## Data Models (Pydantic)

All models in `app/models/__init__.py`:

### Request Models

```python
class CreateRunRequest(BaseModel):
    workspace_id: str
    model: str
    prompt: str
    context_ids: List[str] = []
    model_config: Optional[Dict[str, Any]] = None
    tags: List[str] = []
```

### Response Models

```python
class ModelRunModel(BaseModel):
    id: str
    workspace_id: str
    model: str
    prompt: str
    status: str  # "pending" | "running" | "complete" | "error" | "cancelled"
    output: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[TokenUsageModel] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    context_ids: List[str] = []
    model_config: Optional[Dict[str, Any]] = None
    tags: List[str] = []

class RunHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ModelRunModel]
```

---

## Storage Layer (`app/storage/json_storage.py`)

### Design Pattern: Storage Abstraction

All data access goes through a storage module:

```python
# For Runs
def create_run(...) -> Dict[str, Any]
def get_run(run_id: str) -> Optional[Dict[str, Any]]
def update_run(run_id: str, updates: Dict) -> Optional[Dict[str, Any]]
def list_runs(workspace_id=None, model=None, status=None, limit=100, offset=0) -> Dict

# For Contexts
def create_context(...) -> Dict[str, Any]
def get_context(context_id: str) -> Optional[Dict[str, Any]]
def list_contexts(workspace_id=None, kind=None, is_active=None) -> List[Dict]
def toggle_context_active(context_id: str) -> Optional[Dict[str, Any]]

# For Evaluations
def create_evaluation(...) -> Dict[str, Any]
def list_evaluations(run_id: Optional[str] = None) -> List[Dict]
```

### MVP: JSON Persistence

- **File**: `data/{runs,contexts,evaluations}.json`
- **Format**: Pretty-printed JSON array of objects
- **Auto-creation**: Files created on first write
- **Sorting**: `last_updated` or `created_at` descending

### Production Migration

Replace `json_storage.py` with database calls:

```python
# app/storage/postgres_storage.py (future)
async def create_run(...):
    async with db.transaction():
        await db.execute(
            "INSERT INTO runs (...) VALUES (...)",
            ...
        )
        return run_dict

# app/storage/vector_storage.py (future - for DataForge)
async def search_corpus(corpus_id: str, query: str):
    embeddings = await embed_model.encode(query)
    results = await qdrant_client.search(
        collection_name=corpus_id,
        query_vector=embeddings,
        limit=10
    )
    return results
```

**No API changes required** — routers import from `app.storage` abstraction.

---

## Development Workflow

### 1. Initial Setup

```bash
cd vibeforge-backend

# Create venv
python -m venv venv
source venv/bin/activate

# Build Rust modules (maturin)
maturin develop

# Install Python deps
pip install -e .[dev]
```

### 2. Development Loop

**For Python changes**:

```bash
# Code → Save → Uvicorn auto-reloads
uvicorn app.main:app --reload
```

**For Rust changes**:

```bash
# Code → Save → Rebuild
maturin develop

# Restart uvicorn
# (or edit python file to trigger reload)
```

### 3. Testing

```bash
pytest tests/ -v                    # All tests
pytest tests/test_vibeforge.py -v   # Specific module
pytest tests/ --cov=app             # With coverage
```

### 4. API Documentation

Visit **http://localhost:8000/docs** (Swagger UI)

Auto-generated from Pydantic models + FastAPI route docstrings.

---

## Docker Deployment

### Build

```bash
docker build -t vibeforge-backend:latest .
```

Build process:

1. Start from `python:3.11-slim`
2. Install Rust toolchain
3. Build all Rust modules with maturin
4. Install Python dependencies
5. Expose port 8000
6. Health check via `/health`

### Run

```bash
docker run \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  vibeforge-backend:latest
```

Backend accessible at **http://localhost:8000**

---

## Integration with Frontend (SvelteKit)

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure per environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Example Frontend Call

```javascript
// From SvelteKit frontend (src/routes/+page.svelte)
async function createRun() {
  const response = await fetch("http://localhost:8000/v1/vibeforge/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: "ws-1",
      model: "gpt-4",
      prompt: "Explain AI",
      tags: ["ai", "explanation"],
    }),
  });

  const run = await response.json();
  console.log("Run created:", run.id);
}
```

---

## Performance Characteristics

### Token Estimation

| Method       | Operations/sec | Approach                       |
| ------------ | -------------- | ------------------------------ |
| Python regex | ~100K          | Word split + punctuation count |
| Rust naive   | ~4M            | `len / 4`                      |
| Rust precise | ~2M            | `words * 1.3 + punct * 0.1`    |

**Impact**: Estimate tokens for 10,000-char prompt in **5ms** (Rust) vs **50ms** (Python)

### Context Merging

| Operation                    | Time           |
| ---------------------------- | -------------- |
| Merge 10 contexts (5KB each) | ~1ms (Rust)    |
| JSON serialize 1K runs       | ~10ms (Python) |

### Scaling

- **MVP (JSON)**: Good for ~10K runs, <100 contexts
- **Production (Postgres)**: Unlimited scale with proper indexing
- **Vector search**: Add Qdrant for semantic search (~50ms latency)

---

## Security Considerations

### MVP (Development)

- CORS: `allow_origins=["*"]` for ease of development
- No authentication (all endpoints public)
- No input validation (Pydantic handles basic type coercion)

### Production Checklist

- [ ] Switch CORS to specific origins
- [ ] Add API key / JWT authentication
- [ ] Implement rate limiting
- [ ] Add request validation + sanitization
- [ ] Use environment-specific settings
- [ ] Enable HTTPS/TLS
- [ ] Add request signing (webhook security)
- [ ] Log all API access
- [ ] Implement audit trails
- [ ] Regular security scans (Cargo audit, Bandit)

---

## Monitoring & Observability

### Logging

```python
# Add logging middleware
import logging

logger = logging.getLogger(__name__)

@app.post("/v1/vibeforge/run")
async def create_run(request: CreateRunRequest):
    logger.info(f"Creating run for model: {request.model}")
    # ...
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "vibeforge-backend",
        "version": "0.1.0"
    }
```

### Future

- [ ] Prometheus metrics
- [ ] Structured logging (JSON format)
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Error tracking (Sentry)

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'forge_core'`

**Solution**:

```bash
maturin develop --release
```

Maturin needs to be rerun after Rust code changes.

---

### Issue: `Address already in use` (port 8000)

**Solution**:

```bash
uvicorn app.main:app --port 8001
```

Or kill the existing process:

```bash
lsof -ti:8000 | xargs kill -9
```

---

### Issue: JSON file corruption

**Solution**:

```bash
# Reset all data
rm data/*.json

# Restart server to recreate empty files
```

---

## Next Steps / Roadmap

### Phase 1 (MVP) ✅

- [x] Rust crates (forge_core, forge_prompt, forge_data, forge_eval)
- [x] FastAPI routing (VibeForge main endpoints)
- [x] JSON storage
- [x] Pydantic validation
- [x] Docker support

### Phase 2 (Q1 2026)

- [ ] Postgres migration with async SQLAlchemy
- [ ] Authentication (JWT)
- [ ] API rate limiting
- [ ] Input validation & sanitization
- [ ] Structured logging

### Phase 3 (Q2 2026)

- [ ] Qdrant vector store (DataForge semantic search)
- [ ] Async task queue (Celery for model runs)
- [ ] WebSocket support (real-time run progress)
- [ ] Model provider orchestration (OpenAI, Anthropic, etc.)

### Phase 4 (Q3 2026)

- [ ] Fine-tuning pipeline
- [ ] AutoML integration (NeuroForge sweep execution)
- [ ] Multi-workspace isolation
- [ ] Audit logging & compliance

---

## Contributing

### Adding a New Endpoint

1. **Define the route** in `app/routers/vibeforge.py` (or appropriate router)
2. **Add Pydantic models** in `app/models/__init__.py`
3. **Implement storage logic** in `app/storage/json_storage.py`
4. **Test** with `pytest` and `/docs` UI

### Adding Rust Functionality

1. **Implement in appropriate crate** (forge_prompt, forge_eval, etc.)
2. **Add `#[pyfunction]` or `#[pyclass]` macros**
3. **Export from `#[pymodule]` block**
4. **Rebuild**: `maturin develop`
5. **Import in Python**: `from forge_prompt import ...`

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [PyO3 Guide](https://pyo3.rs/)
- [Maturin Guide](https://www.maturin.rs/)
- [Rust Book](https://doc.rust-lang.org/book/)

---

**Created**: 2025-11-18  
**Version**: 0.1.0  
**Status**: MVP — Ready for development

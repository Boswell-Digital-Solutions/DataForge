# Quick Reference Guide

## File Structure at a Glance

```
vibeforge-backend/
├── rust/
│   ├── Cargo.toml                  ← Workspace config
│   ├── forge_core/src/lib.rs       ← Types (Run, Context, Token)
│   ├── forge_prompt/src/lib.rs     ← Token estimation, context merge
│   ├── forge_data/src/lib.rs       ← Document ingestion stubs
│   └── forge_eval/src/lib.rs       ← Scoring & evaluation stubs
│
├── python/app/
│   ├── main.py                     ← FastAPI app entry point
│   ├── routers/
│   │   ├── vibeforge.py            ← /v1/vibeforge/* endpoints
│   │   ├── dataforge.py            ← /v1/dataforge/* endpoints
│   │   └── neuroforge.py           ← /v1/neuroforge/* endpoints
│   ├── models/__init__.py          ← Pydantic schemas
│   └── storage/json_storage.py     ← Data persistence (JSON)
│
├── data/                           ← JSON data files (auto-created)
├── pyproject.toml                  ← Python package & Maturin config
├── Dockerfile                      ← Container definition
├── README.md                       ← Getting started
├── ARCHITECTURE.md                 ← Deep dive architecture
└── QUICKREF.md                     ← This file
```

---

## Command Quick Reference

### Setup (One-Time)

```bash
# From vibeforge-backend directory
cd vibeforge-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Build Rust + install Python
maturin develop
pip install -e .[dev]
```

### Development (Daily)

```bash
# Start dev server (auto-reload on Python changes)
uvicorn app.main:app --reload --port 8000

# In a separate terminal: watch Rust files
# When you edit .rs files, run:
maturin develop

# Then restart uvicorn (or edit app.py to trigger reload)
```

### Testing

```bash
pytest tests/ -v                    # Run all tests
pytest tests/test_vibeforge.py -v   # Run one module
pytest tests/ --cov=app             # With coverage
pytest -k "test_create_run"         # Run matching tests
```

### Docker

```bash
docker build -t vibeforge-backend:latest .
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  vibeforge-backend:latest
```

### Debugging

```bash
# Check what imports are available
python -c "from forge_core import ModelRun; print(ModelRun)"

# View generated Pydantic schema
python -c "from app.models import ModelRunModel; print(ModelRunModel.model_json_schema())"

# Test API endpoint directly
curl http://localhost:8000/health

# Check port usage
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000

# Rebuild Rust from scratch
rm -rf rust/target
cargo clean
maturin develop --release
```

---

## API Endpoints Quick Reference

### VibeForge (Production) — `/v1/vibeforge`

```
POST /run                          → Create new run
GET /run/{run_id}                  → Fetch run
GET /history                       → List runs (paginated)

POST /context                      → Create context block
GET /context/{context_id}          → Fetch context
GET /contexts                      → List contexts
POST /context/{context_id}/toggle  → Toggle active
```

### DataForge (Stub) — `/v1/dataforge`

```
POST /corpus                       → Create corpus
POST /corpus/{corpus_id}/ingest    → Ingest document
GET /corpus/{corpus_id}/search     → Search (empty, stub)
GET /corpus/{corpus_id}/documents  → List documents
```

### NeuroForge (Stub) — `/v1/neuroforge`

```
POST /eval                         → Create evaluation
GET /evals                         → List evaluations
POST /sweep                        → Create sweep config
GET /sweep/{sweep_id}              → Get sweep status
```

---

## Example API Calls

### Create a Run

```bash
curl -X POST "http://localhost:8000/v1/vibeforge/run" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-1",
    "model": "gpt-4",
    "prompt": "Explain machine learning",
    "context_ids": ["ctx-1"],
    "tags": ["ml", "education"]
  }'
```

### Get Run History

```bash
curl "http://localhost:8000/v1/vibeforge/history?workspace_id=ws-1&limit=10&offset=0"
```

### Create Context

```bash
curl -X POST "http://localhost:8000/v1/vibeforge/context?workspace_id=ws-1&title=Code%20Style&kind=code&description=Python%20conventions&content=Use%20PEP%208...&source=workspace"
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Create run
response = requests.post(
    f"{BASE_URL}/v1/vibeforge/run",
    json={
        "workspace_id": "ws-1",
        "model": "gpt-4",
        "prompt": "Explain AI",
        "tags": ["ai"]
    }
)
run = response.json()
print(f"Created run: {run['id']}")

# Get history
response = requests.get(
    f"{BASE_URL}/v1/vibeforge/history",
    params={"workspace_id": "ws-1", "limit": 10}
)
history = response.json()
print(f"Total runs: {history['total']}")
```

---

## Rust → Python Bridge Cheat Sheet

### Exporting a Rust Function

```rust
// In rust/forge_prompt/src/lib.rs
#[pyfunction]
pub fn estimate_tokens(text: &str) -> u32 {
    (text.len() as f32 / 4.0).ceil() as u32
}

#[pymodule]
fn forge_prompt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(estimate_tokens, m)?)?;
    Ok(())
}
```

### Using in Python

```python
from forge_prompt import estimate_tokens

tokens = estimate_tokens("Hello world!")
print(tokens)  # → 3
```

### Exporting a Rust Class

```rust
// In Rust
#[pyclass]
pub struct PromptContext {
    #[pyo3(get, set)]
    pub system_prompt: String,
    #[pyo3(get, set)]
    pub total_tokens_estimated: u32,
}

#[pymethods]
impl PromptContext {
    #[new]
    pub fn new(system_prompt: String) -> Self {
        // ...
    }

    pub fn merge_contexts(&self) -> String {
        // ...
    }
}

#[pymodule]
fn forge_prompt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PromptContext>()?;
    Ok(())
}
```

### Using in Python

```python
from forge_prompt import PromptContext

ctx = PromptContext("You are helpful")
ctx.add_context("Some background")
merged = ctx.merge_contexts()
```

---

## Common Issues & Fixes

| Problem                           | Solution                                        |
| --------------------------------- | ----------------------------------------------- |
| `ModuleNotFoundError: forge_core` | Run `maturin develop`                           |
| `Address already in use :8000`    | `lsof -ti:8000 \| xargs kill -9`                |
| JSON files empty/corrupted        | `rm data/*.json` and restart                    |
| Maturin build fails               | `cargo clean && maturin develop --release`      |
| Python can't find Rust module     | Make sure venv is activated                     |
| API returns 404                   | Check route path, should be `/v1/vibeforge/...` |
| CORS errors in frontend           | Check `CORSMiddleware` config in `main.py`      |

---

## Storage Schema (JSON MVP)

### `data/runs.json`

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "workspace_id": "ws-1",
    "model": "gpt-4",
    "prompt": "Explain AI",
    "status": "pending",
    "output": null,
    "error": null,
    "tokens_used": null,
    "created_at": "2025-11-18T10:00:00Z",
    "started_at": null,
    "completed_at": null,
    "duration_ms": null,
    "context_ids": ["ctx-123"],
    "model_config": {},
    "tags": ["ai", "education"]
  }
]
```

### `data/contexts.json`

```json
[
  {
    "id": "ctx-123",
    "workspace_id": "ws-1",
    "title": "Code Review Guidelines",
    "kind": "code",
    "description": "Standard code review checklist",
    "content": "- Check naming conventions...",
    "tags": ["review", "code"],
    "is_active": true,
    "last_updated": "2025-11-18T10:00:00Z",
    "source": "workspace"
  }
]
```

### `data/evaluations.json`

```json
[
  {
    "id": "eval-123",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "evaluator": "human",
    "scores": { "accuracy": 4.5, "clarity": 4.8 },
    "notes": "Good explanation",
    "created_at": "2025-11-18T10:10:00Z"
  }
]
```

---

## Migration Path: JSON → Postgres

**Current**: JSON files  
**Future**: PostgreSQL + Qdrant

### Strategy

1. **No API changes**: All storage logic in `app/storage/json_storage.py`
2. **Create new layer**: `app/storage/postgres_storage.py`
3. **Switch via env var**: `STORAGE_BACKEND=postgres` (default: `json`)
4. **Minimal refactor**: Just swap which storage module is imported

```python
# In app/storage/__init__.py (future)
if os.getenv("STORAGE_BACKEND") == "postgres":
    from app.storage.postgres_storage import *
else:
    from app.storage.json_storage import *

# Routers don't need to change
from app.storage import create_run, list_runs, ...
```

---

## Performance Tips

| Operation         | Optimization                                            |
| ----------------- | ------------------------------------------------------- |
| Token estimation  | Use Rust `estimate_tokens_precise()` (~2M ops/sec)      |
| Context merging   | Batch multiple contexts in `PromptContext`              |
| Run history fetch | Add indexes on `workspace_id`, `created_at` in Postgres |
| Vector search     | Use Qdrant with embeddings cache                        |
| API response time | Use response caching (Redis layer)                      |

---

## Resources & Links

- **FastAPI**: https://fastapi.tiangolo.com/
- **PyO3**: https://pyo3.rs/
- **Maturin**: https://www.maturin.rs/
- **Pydantic**: https://docs.pydantic.dev/
- **Rust Book**: https://doc.rust-lang.org/book/
- **Cargo**: https://doc.rust-lang.org/cargo/

---

## Next Steps

1. **Activate venv**: `source venv/bin/activate`
2. **Start dev server**: `uvicorn app.main:app --reload`
3. **Open API docs**: http://localhost:8000/docs
4. **Try an endpoint**: POST /v1/vibeforge/run
5. **Read ARCHITECTURE.md** for deep dive

---

**Version**: 0.1.0  
**Last Updated**: 2025-11-18

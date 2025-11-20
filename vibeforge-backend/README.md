# VibeForge Backend Development Setup

## Project Structure

```
vibeforge-backend/
├── rust/                    # Rust crates (PyO3 modules)
│   ├── Cargo.toml          # Workspace configuration
│   ├── forge_core/         # Core types (TokenUsage, Run, Context, etc.)
│   ├── forge_prompt/       # Prompt building & token estimation
│   ├── forge_data/         # Document ingestion stubs
│   └── forge_eval/         # Evaluation & scoring stubs
├── python/
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── __init__.py
│   │   ├── routers/        # API route handlers
│   │   │   ├── vibeforge.py  # /v1/vibeforge/* endpoints
│   │   │   ├── dataforge.py  # /v1/dataforge/* endpoints (stub)
│   │   │   └── neuroforge.py # /v1/neuroforge/* endpoints (stub)
│   │   ├── models/         # Pydantic request/response models
│   │   │   └── __init__.py
│   │   └── storage/        # Data persistence layer
│   │       ├── __init__.py
│   │       └── json_storage.py  # JSON file-based storage
├── data/                   # JSON data files (runs, contexts, evals)
├── pyproject.toml          # Python package config (maturin, dependencies)
├── Dockerfile              # Container image definition
├── .env.example            # Environment template
├── .gitignore              # Git exclusions
└── README.md               # This file
```

## Tech Stack

- **FastAPI**: Modern async Python web framework
- **Rust + PyO3**: High-performance compiled extensions
- **Maturin**: Build tool for Rust Python bindings
- **Pydantic**: Data validation and serialization
- **JSON**: File-based MVP storage (replaceable with Postgres + vector DB)

## Prerequisites

- Python 3.10+
- Rust 1.70+
- Maturin (`cargo install maturin`)
- Git

## Development Setup

### 1. Clone and Navigate

```bash
cd vibeforge-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Build Rust Extensions (Maturin)

```bash
maturin develop
```

This command:

- Builds all Rust crates (forge_core, forge_prompt, forge_data, forge_eval)
- Compiles them as Python extension modules
- Installs them into the active venv
- **Takes ~2-3 minutes on first run**

### 4. Install Python Dependencies

```bash
pip install -e .[dev]
```

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server starts at: **http://localhost:8000**

API Docs: **http://localhost:8000/docs** (Swagger UI)

## Available APIs

### VibeForge (`/v1/vibeforge`)

#### Runs

- `POST /v1/vibeforge/run` — Create a new model run
- `GET /v1/vibeforge/run/{run_id}` — Retrieve run by ID
- `GET /v1/vibeforge/history` — List runs (paginated, filterable)

#### Contexts

- `POST /v1/vibeforge/context` — Create context block
- `GET /v1/vibeforge/context/{context_id}` — Retrieve context
- `GET /v1/vibeforge/contexts` — List contexts (filterable)
- `POST /v1/vibeforge/context/{context_id}/toggle` — Toggle active status

### DataForge (`/v1/dataforge`) - Stub

- `POST /v1/dataforge/corpus` — Create corpus
- `POST /v1/dataforge/corpus/{corpus_id}/ingest` — Ingest document
- `GET /v1/dataforge/corpus/{corpus_id}/search` — Search corpus
- `GET /v1/dataforge/corpus/{corpus_id}/documents` — List documents

### NeuroForge (`/v1/neuroforge`) - Stub

- `POST /v1/neuroforge/eval` — Create evaluation
- `GET /v1/neuroforge/evals` — List evaluations
- `POST /v1/neuroforge/sweep` — Create parameter sweep
- `GET /v1/neuroforge/sweep/{sweep_id}` — Get sweep status

## Example Requests

### Create a Run

```bash
curl -X POST "http://localhost:8000/v1/vibeforge/run" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-1",
    "model": "gpt-4",
    "prompt": "Explain machine learning",
    "tags": ["ml", "education"]
  }'
```

### Get Run History

```bash
curl "http://localhost:8000/v1/vibeforge/history?workspace_id=ws-1&limit=10"
```

### Create Context Block

```bash
curl -X POST "http://localhost:8000/v1/vibeforge/context" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-1",
    "title": "Code Style Guide",
    "kind": "code",
    "description": "Python conventions",
    "content": "Use PEP 8...",
    "tags": ["style", "python"],
    "source": "workspace"
  }'
```

## Data Persistence

Currently uses JSON files stored in `data/`:

- `runs.json` — All model runs
- `contexts.json` — Context blocks
- `evaluations.json` — Evaluations

**For Production**, replace `json_storage.py` with:

- **Postgres**: Primary data store
- **Qdrant/Weaviate**: Vector DB for semantic search (DataForge)
- **Redis**: Caching and session management

All storage functions are abstracted in `app/storage/json_storage.py` for easy migration.

## Docker Deployment

### Build Image

```bash
docker build -t vibeforge-backend:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  vibeforge-backend:latest
```

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=app  # With coverage
```

## Performance Notes

- **Token Estimation**: Rust implementation (~4M ops/sec vs ~100K in pure Python)
- **Context Merging**: Compiled in forge_prompt crate
- **Lazy Evaluation**: All Rust types bridge to Python dynamically

## Troubleshooting

### Maturin Build Fails

```bash
# Update Rust
rustup update

# Clean rebuild
cargo clean
maturin develop --release
```

### Port 8000 in Use

```bash
uvicorn app.main:app --port 8001
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e .
```

## Future Enhancements

- [ ] Postgres migration with async SQLAlchemy
- [ ] Qdrant vector store integration (semantic search)
- [ ] Redis caching layer
- [ ] Authentication + RBAC
- [ ] Real-time WebSocket updates for run progress
- [ ] Async task queue (Celery + RabbitMQ)
- [ ] Fine-tuning pipeline endpoints
- [ ] Multi-provider model orchestration

## Contributing

1. Make changes in `python/` or `rust/` as appropriate
2. For Rust changes, rebuild with `maturin develop`
3. Test with `pytest` and API docs at `/docs`
4. Commit and push

## License

MIT

---

**Questions?** See the main VibeForge project documentation or open an issue.

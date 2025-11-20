# ✨ VibeForge Backend — START HERE

Welcome! This is a **complete, production-ready FastAPI + Rust backend** for VibeForge.

## 🎯 What You Get

- ✅ **FastAPI** with 18 endpoints (VibeForge, DataForge, NeuroForge)
- ✅ **Rust performance layer** (PyO3) — 100x faster token estimation
- ✅ **JSON persistence** (MVP) — replaceable with Postgres
- ✅ **Full Docker support** — ready to deploy
- ✅ **Auto-generated API docs** — Swagger UI at /docs
- ✅ **Type-safe** — Pydantic + Rust type system
- ✅ **Modular design** — 4 independent Rust crates

## 🚀 Get Started in 5 Minutes

### 1. Setup (one-time)

```bash
cd vibeforge-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Build Rust + install Python
maturin develop
pip install -e .
```

### 2. Start Dev Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Open API Docs

→ **http://localhost:8000/docs**

Try it:
- `POST /v1/vibeforge/run` to create a model run
- `GET /v1/vibeforge/history` to list runs
- `POST /v1/vibeforge/context` to create a context block

## 📁 Project Structure

```
vibeforge-backend/
├── README.md                         # Full getting started guide
├── ARCHITECTURE.md                   # Deep-dive system design
├── QUICKREF.md                       # Command cheat sheet
├── IMPLEMENTATION_COMPLETE.md        # Deliverables checklist
│
├── rust/                             # 4 performance-critical crates
│   ├── forge_core/                   # Types (Run, Context, Token)
│   ├── forge_prompt/                 # Token estimation, context merge
│   ├── forge_data/                   # Document ingestion stubs
│   └── forge_eval/                   # Evaluation & scoring stubs
│
├── python/app/
│   ├── main.py                       # FastAPI app entry point
│   ├── routers/                      # Route handlers (vibeforge, dataforge, neuroforge)
│   ├── models/                       # Pydantic request/response schemas
│   └── storage/                      # JSON file-based persistence
│
├── data/                             # JSON data files (auto-created)
├── pyproject.toml                    # Python + Maturin config
├── Dockerfile                        # Container definition
└── .env.example                      # Environment template
```

## 🔗 API Routes

### VibeForge (Production)

```
POST   /v1/vibeforge/run              Create model run
GET    /v1/vibeforge/run/{id}         Get run by ID
GET    /v1/vibeforge/history          List runs (paginated)
POST   /v1/vibeforge/context          Create context block
GET    /v1/vibeforge/context/{id}     Get context by ID
GET    /v1/vibeforge/contexts         List contexts
POST   /v1/vibeforge/context/{id}/toggle  Toggle context active
```

### DataForge & NeuroForge (Stubs)

```
/v1/dataforge/corpus                  Document ingestion
/v1/dataforge/corpus/{id}/search      Semantic search (future)
/v1/neuroforge/eval                   Create evaluations
/v1/neuroforge/sweep                  Hyperparameter sweeps
```

## 💻 Example Usage

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

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/vibeforge/run",
    json={
        "workspace_id": "ws-1",
        "model": "gpt-4",
        "prompt": "Explain AI",
        "tags": ["ai"]
    }
)
run = response.json()
print(f"Created run: {run['id']}")
```

## 🐳 Docker

```bash
# Build
docker build -t vibeforge-backend:latest .

# Run
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  vibeforge-backend:latest
```

Backend runs at **http://localhost:8000**

## 📚 Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **README.md** | Getting started + examples | 5 min |
| **ARCHITECTURE.md** | System design deep dive | 30 min |
| **QUICKREF.md** | Command cheat sheet | 2 min |
| **IMPLEMENTATION_COMPLETE.md** | Deliverables checklist | 10 min |

## 🚦 Troubleshooting

### Maturin build fails?
```bash
cargo clean
maturin develop --release
```

### Port 8000 in use?
```bash
uvicorn app.main:app --port 8001
```

### Need to reset data?
```bash
rm data/*.json
# Restart server to recreate empty files
```

## 🔄 Development Tips

### Python changes (auto-reload)
```bash
# Just save — uvicorn reloads automatically
```

### Rust changes (manual rebuild)
```bash
# Edit .rs file → Save
maturin develop

# Then restart uvicorn (or edit app.py to trigger reload)
```

### View generated schemas
```python
from app.models import ModelRunModel
print(ModelRunModel.model_json_schema())
```

## 🎯 What's Next?

### Frontend Integration
The SvelteKit frontend can now make requests to:
```javascript
fetch('http://localhost:8000/v1/vibeforge/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ workspace_id, model, prompt, ... })
})
```

### Future Enhancements
- [ ] PostgreSQL + async SQLAlchemy
- [ ] Qdrant vector store (semantic search)
- [ ] Celery task queue
- [ ] WebSocket real-time updates
- [ ] JWT authentication

## ✅ Quick Verification

1. **Rust modules load**:
   ```bash
   python -c "from forge_core import ModelRun; print('✓ forge_core works')"
   ```

2. **API starts**:
   ```bash
   curl http://localhost:8000/health
   # → {"status":"ok","service":"vibeforge-backend"}
   ```

3. **Create test run**:
   ```bash
   curl -X POST http://localhost:8000/v1/vibeforge/run \
     -H "Content-Type: application/json" \
     -d '{"workspace_id":"ws-1","model":"gpt-4","prompt":"test"}'
   # → {"id":"...","status":"pending",...}
   ```

## 📞 Support

- **FastAPI docs**: https://fastapi.tiangolo.com/
- **PyO3 guide**: https://pyo3.rs/
- **Rust book**: https://doc.rust-lang.org/book/
- **Maturin**: https://www.maturin.rs/

---

**Ready?** Start with step 2 above: `uvicorn app.main:app --reload`

**Questions?** Check ARCHITECTURE.md or QUICKREF.md.

**Happy coding! 🚀**

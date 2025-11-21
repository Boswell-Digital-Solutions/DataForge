# ⚡ VibeForge API - Developer Quick Start

## 🚀 5-Minute Setup

```bash
# 1. Navigate to project
cd vibeforge-backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Build Rust + Install Python
maturin develop           # ~2-3 minutes
pip install -e .[dev]

# 4. Start development server
uvicorn app.main:app --reload --port 8000

# 5. Open browser
# Swagger UI:  http://localhost:8000/docs
# ReDoc:       http://localhost:8000/redoc
# API:         http://localhost:8000/openapi.json
```

## 📝 Environment Setup (Optional)

```bash
# Set LLM API keys for real providers
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Ollama (default already localhost:11434)
export OLLAMA_BASE_URL="http://localhost:11434"
```

**Without keys**: Providers return mock responses (still works for testing!)

---

## 🧪 Testing with cURL

### Create a Run

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "What is machine learning?",
    "active_contexts": []
  }'
```

### Get Run by ID

```bash
curl http://localhost:8000/v1/vibeforge/run/550e8400-e29b-41d4-a716-446655440000
```

### Get History

```bash
curl "http://localhost:8000/v1/vibeforge/history?limit=10&offset=0"

# With filters
curl "http://localhost:8000/v1/vibeforge/history?model=gpt-4&status=complete"
```

### Health Check

```bash
curl http://localhost:8000/v1/vibeforge/health
```

---

## 📂 Project Structure

```
python/app/
├── main.py                      # FastAPI app entry
├── models/
│   ├── __init__.py             # Re-exports
│   └── vibeforge_models.py ✨   # Your schemas
├── services/
│   ├── __init__.py
│   └── llm_service.py ✨        # LLM integration
├── repositories/
│   ├── __init__.py
│   └── runs_file.py ✨          # JSON storage
└── routers/
    └── vibeforge.py             # Endpoints

rust/
├── forge_core/src/lib.rs        # Core types
└── forge_prompt/src/lib.rs      # Token/prompt building
```

---

## 🔌 Three Main APIs

### 1. POST /v1/vibeforge/run (Create & Execute)

```python
# Request
{
  "model": "claude-3-opus-20240229",  # or gpt-4, ollama:mistral
  "prompt": "Your prompt here",
  "active_contexts": [                # Optional
    {
      "id": "ctx-001",
      "title": "Context title",
      "content": "Context content",
      "kind": "code",                 # system|design|project|code|workflow
      "priority": 1
    }
  ],
  "data_profile_id": null,            # Optional
  "eval_profile_id": null             # Optional
}

# Response (201)
{
  "id": "uuid",
  "model": "...",
  "prompt": "...",
  "status": "complete",
  "output": "LLM response text",
  "tokens_used": {
    "prompt_tokens": 50,
    "completion_tokens": 150,
    "total_tokens": 200
  },
  "created_at": "2025-11-18T10:00:00Z",
  "started_at": "2025-11-18T10:00:01Z",
  "completed_at": "2025-11-18T10:00:05Z",
  "duration_ms": 4000,
  "active_contexts": [...],
  "data_profile_id": null,
  "eval_profile_id": null
}
```

### 2. GET /v1/vibeforge/run/{run_id} (Retrieve One)

```bash
# Returns: ModelRunModel (same as POST response)
```

### 3. GET /v1/vibeforge/history (List All)

```bash
# Query params:
?limit=10&offset=0&model=gpt-4&status=complete

# Response (200)
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "items": [
    { /* ModelRunModel */ },
    { /* ModelRunModel */ }
  ]
}
```

---

## 🧩 Key Modules

### LLM Service

```python
from app.services.llm_service import get_llm_service

service = get_llm_service()

# Call any LLM
response = await service.call_llm(
  model="claude-3-opus-20240229",
  prompt="Hello AI"
)
print(response.content)           # "Hello! How can I help..."
print(response.prompt_tokens)     # 2
print(response.completion_tokens) # 150
print(response.total_tokens)      # 152

# Estimate tokens
tokens = service.estimate_tokens("claude", "Hello world")
print(tokens)  # ~3
```

### Runs Repository

```python
from app.repositories.runs_file import get_runs_repo

repo = get_runs_repo()

# Create
run = repo.create_run(
  model="gpt-4",
  prompt="Test",
  status="pending"
)

# Get
run = repo.get_run(run["id"])

# Update
repo.update_run(
  run["id"],
  status="complete",
  output="Response",
  tokens_used={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
)

# List
history = repo.list_runs(limit=10, offset=0, model="gpt-4", status="complete")
print(history["total"])      # Total matching runs
print(history["items"])      # List of runs
```

### Pydantic Models

```python
from app.models import (
  CreateRunRequest,
  ModelRunModel,
  TokenUsageModel,
  ContextBlockModel,
)

# These validate request/response data automatically
# Used by FastAPI for type checking and Swagger documentation
```

---

## 🐛 Debugging

### Check Data File

```bash
cat python/app/data/runs.json | jq
```

### View Logs

```bash
# The server prints logs to console
# Look for:
# - "Creating run..."
# - "Calling LLM..."
# - "Run completed"
# - Any ERROR messages
```

### Test Individual Components

```bash
# Test LLM service
python -c "
from app.services.llm_service import get_llm_service
service = get_llm_service()
print(service.providers.keys())
"

# Test repository
python -c "
from app.repositories.runs_file import get_runs_repo
repo = get_runs_repo()
print(f'Data file: {repo.runs_file}')
"

# Test models
python -c "
from app.models import CreateRunRequest
req = CreateRunRequest(model='gpt-4', prompt='test', active_contexts=[])
print(req.model_dump_json(indent=2))
"
```

### Rust Module Status

```bash
python -c "import forge_core; print(dir(forge_core))"
python -c "import forge_prompt; print(dir(forge_prompt))"
```

---

## 🔑 LLM Provider Routing

```
Model Identifier              →    Provider      →    Config
───────────────────────────────────────────────────────────────
"claude-3-opus-20240229"      →    Claude        →    Anthropic API
"gpt-4"                       →    GPT           →    OpenAI API
"ollama:mistral"              →    Ollama        →    Local HTTP
"ollama:neural-chat"          →    Ollama        →    Local HTTP
```

**Without API keys**: All providers return mock responses  
**With API keys**: Real responses from services

---

## 📊 Data Persistence

### Location

```
python/app/data/runs.json
```

### Format

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "model": "gpt-4",
    "prompt": "Your prompt",
    "status": "complete",
    "output": "LLM output",
    "error": null,
    "tokens_used": {
      "prompt_tokens": 50,
      "completion_tokens": 150,
      "total_tokens": 200
    },
    "created_at": "2025-11-18T10:00:00Z",
    "started_at": "2025-11-18T10:00:01Z",
    "completed_at": "2025-11-18T10:00:05Z",
    "duration_ms": 4000,
    "active_contexts": [],
    "data_profile_id": null,
    "eval_profile_id": null
  }
]
```

### Backup

```bash
cp python/app/data/runs.json python/app/data/runs.json.backup
```

### Clear Data

```bash
rm python/app/data/runs.json
# Will recreate empty on next run
```

---

## 🚨 Common Issues

### Issue: "Module not found: forge_core"

**Solution**: Run `maturin develop` to compile Rust modules

### Issue: "Connection refused" to LLM

**Solution**: Check if service is running (Ollama, or API keys set)

### Issue: Empty output from LLM

**Solution**: Check if API key is set, or using mock provider

### Issue: Port 8000 already in use

**Solution**: Kill process or use different port

```bash
# Kill
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --reload --port 8001
```

### Issue: JSON decode error

**Solution**: Check `python/app/data/runs.json` is valid JSON

```bash
python -m json.tool python/app/data/runs.json
```

---

## 📚 Documentation

- **Full Implementation**: `IMPLEMENTATION_API_COMPLETE.md`
- **API Summary**: `API_IMPLEMENTATION_SUMMARY.md`
- **Verification**: `VERIFICATION_CHECKLIST.md`
- **Architecture**: `ARCHITECTURE.md`
- **Quick Reference**: `QUICKREF.md`
- **Copilot Guide**: `.github/copilot-instructions.md`

---

## 🎓 Learning Path

1. ✅ Read this file (you are here)
2. ⬜ Start server and test via Swagger UI
3. ⬜ Review `python/app/models/vibeforge_models.py` (schemas)
4. ⬜ Review `python/app/services/llm_service.py` (providers)
5. ⬜ Review `python/app/repositories/runs_file.py` (storage)
6. ⬜ Review `python/app/routers/vibeforge.py` (endpoints)
7. ⬜ Read `IMPLEMENTATION_API_COMPLETE.md` (deep dive)
8. ⬜ Run `test_implementation.py` (verification)
9. ⬜ Create unit tests in `tests/` directory
10. ⬜ Plan database migration to Postgres

---

## 🎯 Next Tasks

- [ ] Set LLM API keys in environment
- [ ] Test all three providers
- [ ] Create comprehensive test suite
- [ ] Add authentication (JWT)
- [ ] Implement context management
- [ ] Add rate limiting
- [ ] Setup monitoring
- [ ] Plan Postgres migration
- [ ] Setup CI/CD pipeline
- [ ] Deploy to production

---

**Ready to use!** 🚀  
Questions? See documentation files listed above.

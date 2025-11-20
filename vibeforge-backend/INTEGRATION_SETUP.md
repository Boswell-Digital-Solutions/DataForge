# VibeForge Frontend-Backend Integration Setup

Complete step-by-step guide for integrating SvelteKit frontend with FastAPI + Rust backend.

## Quick Start (5 minutes)

### Backend Setup

```bash
cd vibeforge-backend

# 1. Create environment file
cat > .env << 'EOF'
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=true
ANTHROPIC_API_KEY=sk-ant-xxx  # Get from https://console.anthropic.com
OPENAI_API_KEY=sk-xxx          # Optional: Get from https://platform.openai.com
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
LOG_LEVEL=INFO
EOF

# 2. Build Rust extensions and install dependencies
maturin develop
pip install -e .[dev]

# 3. Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd vibeforge

# 1. Create environment file
cat > .env.local << 'EOF'
PUBLIC_API_BASE_URL=http://localhost:8000
PUBLIC_API_VERSION=v1
EOF

# 2. Install dependencies
pnpm install

# 3. Copy API client files (see Files section below)

# 4. Start dev server
pnpm dev
```

Visit: http://localhost:5173

---

## Environment Variables

### Backend (.env in vibeforge-backend/)

| Variable            | Purpose                  | Example                     | Required          |
| ------------------- | ------------------------ | --------------------------- | ----------------- |
| `API_PORT`          | FastAPI server port      | `8000`                      | ✓                 |
| `API_HOST`          | Bind address             | `0.0.0.0`                   | ✓                 |
| `DEBUG`             | Enable debug mode        | `true`                      | ✓                 |
| `ANTHROPIC_API_KEY` | Claude API key           | `sk-ant-...`                | For Claude models |
| `OPENAI_API_KEY`    | OpenAI API key           | `sk-...`                    | For GPT models    |
| `CORS_ORIGINS`      | Allowed frontend origins | `["http://localhost:5173"]` | ✓                 |
| `LOG_LEVEL`         | Logging verbosity        | `INFO`, `DEBUG`             | ✓                 |

**Get API Keys:**

- **Anthropic**: https://console.anthropic.com/account/keys
- **OpenAI**: https://platform.openai.com/account/api-keys

### Frontend (.env.local in vibeforge/)

| Variable              | Purpose     | Example                 | Required |
| --------------------- | ----------- | ----------------------- | -------- |
| `PUBLIC_API_BASE_URL` | Backend URL | `http://localhost:8000` | ✓        |
| `PUBLIC_API_VERSION`  | API version | `v1`                    | ✓        |

**Note**: Only `PUBLIC_*` variables are accessible in browser. Backend secrets stay on server.

---

## Files to Add to Frontend

### 1. Type Definitions

**Path**: `src/lib/api/types.ts`

Copy content from `FRONTEND_API_TYPES.ts` in this repo.

### 2. API Client

**Path**: `src/lib/api/client.ts`

Copy content from `FRONTEND_API_CLIENT.ts` in this repo.

### 3. Optional: Environment Variables

**Path**: `.env.local`

```env
PUBLIC_API_BASE_URL=http://localhost:8000
PUBLIC_API_VERSION=v1
```

### 4. Example Usage in Component

**Path**: `src/routes/workbench/+page.svelte`

See INTEGRATION_GUIDE.md for full examples.

---

## Verification Checklist

### Backend Health

```bash
# Should return 200 OK
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"vibeforge"}
```

### CORS Configuration

```bash
# Verify CORS headers are set
curl -X OPTIONS http://localhost:8000/v1/vibeforge/run \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -v | grep -i "access-control"

# Should include:
# Access-Control-Allow-Origin: http://localhost:5173
# Access-Control-Allow-Methods: POST, GET, etc.
```

### API Key Configuration

```bash
# Test Claude endpoint (requires ANTHROPIC_API_KEY)
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "Say hello",
    "active_contexts": []
  }'
```

### Rust Module

```bash
# Verify Rust extension is loaded
python -c "from vibeforge_prompt import estimate_tokens_precise; \
  print('Tokens:', estimate_tokens_precise('hello'))"
```

### Frontend API Connection

1. Open http://localhost:5173 in browser
2. Open DevTools (F12)
3. Go to Console tab
4. Paste:
   ```javascript
   fetch("http://localhost:8000/health")
     .then((r) => r.json())
     .then(console.log)
     .catch(console.error);
   ```
5. Should print: `{status: "ok", service: "vibeforge"}`

---

## Common Issues & Solutions

### CORS Error: "Access to XMLHttpRequest blocked by CORS policy"

**Cause**: Frontend origin not in backend `CORS_ORIGINS`

**Fix**:

```bash
# 1. Edit .env in backend
CORS_ORIGINS=["http://localhost:5173"]

# 2. Restart backend (Ctrl+C, then run again)
uvicorn app.main:app --reload --port 8000
```

### 404 Not Found on /v1/vibeforge/run

**Cause**: Backend not running or wrong port

**Fix**:

```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Verify frontend .env.local
cat .env.local | grep PUBLIC_API_BASE_URL

# 3. Restart frontend to pick up new env vars
```

### "API key not configured"

**Cause**: Missing `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

**Fix**:

```bash
# 1. Get key from https://console.anthropic.com/account/keys
# 2. Add to .env in backend
ANTHROPIC_API_KEY=sk-ant-xxx

# 3. Restart backend
```

### "Rust module not found"

**Cause**: `vibeforge_prompt` extension not built

**Fix**:

```bash
cd vibeforge-backend

# Clean rebuild
rm -rf rust/target
maturin develop

# Verify
python -c "from vibeforge_prompt import estimate_tokens_precise; print('OK')"
```

### TypeScript errors about types

**Cause**: Type files not in right location

**Fix**:

```bash
# Verify path exists
ls -la vibeforge/src/lib/api/types.ts
ls -la vibeforge/src/lib/api/client.ts

# Should see both files
```

---

## Development Workflow

### Terminal 1: Backend

```bash
cd vibeforge-backend
uvicorn app.main:app --reload --port 8000
```

**Auto-reloads on**:

- Python file changes
- `.env` changes (restart manually)

**Rust changes** require:

```bash
maturin develop
# Then restart uvicorn
```

### Terminal 2: Frontend

```bash
cd vibeforge
pnpm dev
```

**Auto-reloads on**:

- Svelte file changes
- TypeScript changes
- `.env.local` changes (may need browser refresh)

### Terminal 3: Optional - Log Monitor

```bash
cd vibeforge-backend
tail -f data/runs.json | jq
```

---

## Testing the Full Integration

### Test 1: Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"vibeforge"}
```

### Test 2: Create Run via API

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "What is 2+2?",
    "active_contexts": []
  }'
```

**Expected response**: Full run object with `status: "complete"`

### Test 3: Get Run Details

```bash
# Replace RUN_ID with the ID from Test 2
curl http://localhost:8000/v1/vibeforge/run/{RUN_ID}
```

### Test 4: Fetch History

```bash
curl http://localhost:8000/v1/vibeforge/history?limit=5
```

### Test 5: Frontend Component Test

In frontend browser console:

```javascript
// Test API client import
import { postRun } from "$lib/api/client";

// Create a test run
const run = await postRun({
  model: "claude-3-opus-20240229",
  prompt: "Hello!",
  active_contexts: [],
});

console.log(run);
```

---

## Performance Tuning

### Optimize Rust Build

**For development** (faster):

```bash
maturin develop
# ~30 seconds, unoptimized
```

**For production** (slower but better):

```bash
maturin develop --release
# ~2-3 minutes, optimized
```

### Token Estimation Performance

Rust module is fast:

```bash
python3 << 'EOF'
from vibeforge_prompt import estimate_tokens_precise
import time

text = "The quick brown fox jumps over the lazy dog. " * 1000

start = time.time()
for _ in range(1000):
    estimate_tokens_precise(text)
elapsed = time.time() - start

print(f"1000 calls in {elapsed:.2f}s = {1000/elapsed:.0f} calls/sec")
EOF
```

Expected: >10,000 calls/sec (very fast)

---

## Deployment Checklist

- [ ] Backend `.env` has real API keys (not sample keys)
- [ ] Frontend `.env.local` uses production API URL
- [ ] Backend CORS includes all frontend domains
- [ ] Rust extensions built in release mode
- [ ] All dependencies installed (`maturin develop` + `pip install -e .[dev]`)
- [ ] Database migration plan (JSON → Postgres)
- [ ] Logging configured for production (not DEBUG)
- [ ] Error handling in frontend for all edge cases
- [ ] Rate limiting configured (if needed)
- [ ] Backup strategy for `data/` directory

---

## Next Steps

1. **Implement Context Management**: Add CRUD endpoints for context blocks
2. **Add Streaming**: Use WebSockets for real-time LLM output
3. **Evaluation System**: Implement scoring endpoints for run evaluation
4. **Vector Search**: Integrate Qdrant for semantic search
5. **Authentication**: Add JWT tokens for user isolation
6. **Production Deployment**: Docker/Kubernetes setup

See ARCHITECTURE.md for design decisions and roadmap.

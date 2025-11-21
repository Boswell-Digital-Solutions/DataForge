# VibeForge Frontend-Backend Integration - Quick Start Checklist

**Goal**: Get VibeForge frontend (SvelteKit) and backend (FastAPI + Rust) working together in 15 minutes.

## Pre-requisites ✓

- [ ] Backend repository cloned: `vibeforge-backend/`
- [ ] Frontend repository cloned: `vibeforge/`
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] API key (Anthropic or OpenAI)

---

## Backend Setup (5 minutes)

### 1. Navigate to backend

```bash
cd vibeforge-backend
```

### 2. Create environment file

```bash
cat > .env << 'EOF'
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=true
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO
EOF
```

**Get API key**: https://console.anthropic.com/account/keys

### 3. Build Rust & install dependencies

```bash
maturin develop
pip install -e .[dev]
```

Expected output: `✓ Rust compiled successfully`

### 4. Start backend server

```bash
uvicorn app.main:app --reload --port 8000
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 5. Verify backend is running

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"vibeforge"}
```

✓ **Backend Ready!** Leave this terminal running.

---

## Frontend Setup (5 minutes)

### 1. In a new terminal, navigate to frontend

```bash
cd vibeforge
```

### 2. Create environment file

```bash
cat > .env.local << 'EOF'
PUBLIC_API_BASE_URL=http://localhost:8000
PUBLIC_API_VERSION=v1
EOF
```

### 3. Add API client files

Copy these files from backend repo to frontend:

- Copy `FRONTEND_API_TYPES.ts` → `src/lib/api/types.ts`
- Copy `FRONTEND_API_CLIENT.ts` → `src/lib/api/client.ts`

```bash
# If files are in backend root:
mkdir -p src/lib/api
cp ../vibeforge-backend/FRONTEND_API_TYPES.ts src/lib/api/types.ts
cp ../vibeforge-backend/FRONTEND_API_CLIENT.ts src/lib/api/client.ts
```

### 4. Install dependencies

```bash
pnpm install
```

### 5. Start frontend server

```bash
pnpm dev
```

Expected output:

```
VITE v4.x.x ready in XXX ms
➜  Local:   http://localhost:5173/
```

✓ **Frontend Ready!** Leave this terminal running.

---

## Integration Testing (3 minutes)

### 1. Open browser

Navigate to: **http://localhost:5173**

You should see the VibeForge workbench.

### 2. Test CORS connection

Open browser DevTools (F12) → Console tab:

```javascript
fetch("http://localhost:8000/health")
  .then((r) => r.json())
  .then(console.log)
  .catch(console.error);
```

Should print: `{status: 'ok', service: 'vibeforge'}`

If it fails:

- [ ] Backend running? `curl http://localhost:8000/health`
- [ ] Check `.env` in backend has `CORS_ORIGINS=["http://localhost:5173"]`
- [ ] Restart backend

### 3. Test run creation

In browser Console:

```javascript
import { postRun } from "$lib/api/client";

postRun({
  model: "claude-3-opus-20240229",
  prompt: "What is 2+2?",
  active_contexts: [],
})
  .then((r) => {
    console.log("Status:", r.status);
    console.log("Output:", r.output);
    console.log("Tokens:", r.tokens_used?.total_tokens);
  })
  .catch((e) => console.error(e));
```

Should print run output in console.

✓ **Integration Working!**

---

## Command Reference

### Backend (Terminal 1)

```bash
cd vibeforge-backend

# Build Rust
maturin develop

# Start server
uvicorn app.main:app --reload --port 8000

# View logs
tail -f data/runs.json | jq

# Kill server
# Ctrl+C
```

### Frontend (Terminal 2)

```bash
cd vibeforge

# Start dev server
pnpm dev

# Stop server
# Ctrl+C

# Rebuild after dependency changes
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Testing (Terminal 3)

```bash
# Test backend
curl http://localhost:8000/health

# Test API
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-opus-20240229","prompt":"Hi","active_contexts":[]}'

# Run integration tests
bash integration_test.sh
```

---

## Troubleshooting

### ❌ "CORS error" in browser

**Fix**:

1. Check backend `.env` has: `CORS_ORIGINS=["http://localhost:5173"]`
2. Restart backend: Stop (Ctrl+C) and run again
3. Clear browser cache: Ctrl+Shift+Delete

### ❌ "Cannot POST /v1/vibeforge/run" (404)

**Fix**:

1. Verify backend running: `curl http://localhost:8000/health`
2. Check frontend `.env.local`: `PUBLIC_API_BASE_URL=http://localhost:8000`
3. Restart frontend

### ❌ "Anthropic API key not configured"

**Fix**:

1. Get key: https://console.anthropic.com/account/keys
2. Add to backend `.env`: `ANTHROPIC_API_KEY=sk-ant-xxx`
3. Restart backend

### ❌ "vibeforge_prompt not found"

**Fix**:

```bash
cd vibeforge-backend
rm -rf rust/target
maturin develop
```

### ❌ "Port 8000 already in use"

**Fix**:

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --port 8001
```

---

## Next Steps

1. **Explore the UI**

   - Go to http://localhost:5173/workbench
   - Create a run with a prompt
   - Check http://localhost:5173/history

2. **Read Full Docs**

   - Integration Guide: `INTEGRATION_GUIDE.md`
   - API Reference: `API_REFERENCE.md`
   - Architecture: `ARCHITECTURE.md`

3. **Advanced Features**
   - Add context blocks to runs
   - Implement filtering in history
   - Add WebSocket support for streaming
   - Deploy to production

---

## File Structure

```
vibeforge-backend/
├── .env                           ← Configuration
├── python/app/
│   ├── main.py                    ← FastAPI app
│   ├── models/vibeforge_models.py ← Pydantic schemas
│   └── routers/vibeforge.py       ← API endpoints
├── rust/forge_prompt/src/lib.rs   ← Token estimation
└── data/runs.json                 ← Persisted runs

vibeforge/
├── .env.local                     ← Frontend config
├── src/lib/api/
│   ├── types.ts                   ← Type definitions
│   └── client.ts                  ← API client
├── src/routes/
│   ├── workbench/+page.svelte     ← Main UI
│   ├── history/+page.svelte       ← History panel
│   └── run/[id]/+page.svelte      ← Details view
└── pnpm-lock.yaml
```

---

## Verification Checklist

After setup, verify:

- [ ] Backend health: `curl http://localhost:8000/health` → 200 OK
- [ ] Frontend loads: Visit http://localhost:5173 → No errors
- [ ] CORS works: Browser console → No CORS errors
- [ ] API call works: Create a run from frontend → Gets output
- [ ] History works: Visit /history → See past runs
- [ ] Token counting: Check `tokens_used` in run response

---

## Support

If you encounter issues:

1. Check logs:

   - **Backend**: Terminal 1 output
   - **Frontend**: Browser Console (F12)

2. Review documentation:

   - Docs: `INTEGRATION_GUIDE.md`
   - API: `API_REFERENCE.md`
   - Troubleshooting: `INTEGRATION_SETUP.md`

3. Run tests:
   ```bash
   bash integration_test.sh
   ```

---

## Quick Reference

| Command                                     | Purpose           |
| ------------------------------------------- | ----------------- |
| `curl http://localhost:8000/health`         | Check backend     |
| `uvicorn app.main:app --reload --port 8000` | Start backend     |
| `pnpm dev`                                  | Start frontend    |
| `maturin develop`                           | Build Rust module |
| `bash integration_test.sh`                  | Run all tests     |

---

**You're all set! 🚀 Open http://localhost:5173 and start using VibeForge.**

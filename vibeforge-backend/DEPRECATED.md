# ⚠️ DEPRECATED: vibeforge-backend

**This backend is deprecated and should no longer be used.**

---

## Migration Status: COMPLETE ✅

All functionality from `vibeforge-backend` has been successfully migrated to the proper Forge architecture:

### What Was Migrated

1. **LLM Execution Logic** → **NeuroForge**

   - Location: `/NeuroForge/neuroforge_backend/workbench/`
   - Endpoints:
     - `POST /api/v1/workbench/execute` - Execute prompts on multiple models
     - `GET /api/v1/workbench/models` - List available models
   - Features: Context building, prompt templating, multi-model execution, token tracking

2. **Storage & Analytics** → **DataForge**

   - Location: `/DataForge/app/api/runs_router.py` + `/DataForge/app/services/runs_service.py`
   - Endpoints:
     - `POST /api/v1/runs` - Log execution runs
     - `GET /api/v1/runs` - List runs with filters
     - `GET /api/v1/runs/{id}` - Get run details
     - `DELETE /api/v1/runs/{id}` - Delete run
     - `GET /api/v1/runs/analytics/usage` - Usage metrics
   - Features: Run history, cost tracking, per-model analytics, workspace metrics

3. **Frontend Integration** → **VibeForge**
   - Location: `/vibeforge/src/lib/stores/`
   - Integration: Direct API calls to NeuroForge and DataForge
   - No backend routes in VibeForge (pure frontend)

---

## Why Was This Deprecated?

### Architecture Violation

The `vibeforge-backend` violated the Forge ecosystem's core architectural principle:

**VibeForge should be frontend-only.**

The Forge architecture follows a clean 3-pillar design:

```
┌─────────────────┐
│ VibeForge       │  Frontend only (SvelteKit)
│ UI Layer        │  User interactions, visual design
└────────┬────────┘
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ NeuroForge      │    │ DataForge       │
│ LLM Execution   │───▶│ Storage         │
│ Multi-model     │    │ Analytics       │
└─────────────────┘    └─────────────────┘
```

Creating a separate `vibeforge-backend` duplicated functionality that already existed (or should exist) in NeuroForge and DataForge, leading to:

- Code duplication
- Architectural confusion
- Maintenance burden
- Deployment complexity

---

## Migration Details

### Before (vibeforge-backend)

```
vibeforge-backend/
├── python/app/routers/vibeforge.py  # LLM execution
├── python/app/storage/              # Run storage
└── rust/                            # Performance-critical code
```

### After (Proper Architecture)

**NeuroForge** (LLM Execution):

```python
# /NeuroForge/neuroforge_backend/workbench/router.py
@router.post("/api/v1/workbench/execute")
async def execute_prompt(request: ExecutePromptRequest):
    # Context building → Prompt engineering → Model routing
    # Supports Claude, GPT, Ollama
    pass
```

**DataForge** (Storage & Analytics):

```python
# /DataForge/app/api/runs_router.py
@router.post("/api/v1/runs")
async def log_run(request: RunCreate):
    # Store run with costs, tokens, timing
    # Calculate per-model analytics
    pass
```

**VibeForge** (Frontend):

```typescript
// /vibeforge/src/lib/stores/runStore.ts
async function executeRun(request: ExecutePromptRequest) {
  // Call NeuroForge for execution
  const result = await neuroforgeClient.executePrompt(request);

  // Log to DataForge for history
  await dataforgeClient.logRun(result);
}
```

---

## What to Use Instead

### For LLM Execution

**Use NeuroForge:**

- URL: `http://localhost:8002/api/v1/workbench/execute`
- Features: Multi-model execution, context building, prompt templates
- Models: Claude 3.5 Sonnet, GPT-4o, Ollama local models

### For Run Storage & Analytics

**Use DataForge:**

- URL: `http://localhost:8001/api/v1/runs`
- Features: Run history, cost tracking, usage metrics, workspace analytics
- Database: PostgreSQL with TimescaleDB support for time-series

### For UI

**Use VibeForge:**

- URL: `http://localhost:5173`
- Features: 3-column workbench, preset management, context blocks, multi-model comparison
- Tech: SvelteKit 2 + Svelte 5 + Tailwind CSS v4

---

## Migration Documentation

Full migration details documented in:

- `/Forge/BACKEND_MIGRATION_PLAN.md` - Original migration strategy
- `/Forge/SESSION_SUMMARY_2025_01_22.md` - Implementation session log
- `/vibeforge/REFACTORING_COMPLETE.md` - Frontend changes
- `/DataForge/RUNS_ENDPOINT_COMPLETE.md` - DataForge implementation
- `/NeuroForge/neuroforge_backend/workbench/` - NeuroForge workbench module

---

## Timeline

- **Created**: Early 2025 (exact date unknown)
- **Identified as violation**: January 22, 2025
- **Migration started**: January 22, 2025
- **Migration completed**: November 21, 2025
- **Status**: **DEPRECATED - DO NOT USE**

---

## Cleanup Recommendations

This repository should be:

1. ✅ Marked as deprecated (this file)
2. ⏳ Archived on GitHub (if applicable)
3. ⏳ Removed from documentation references
4. ⏳ Excluded from deployment pipelines

**Do not delete** - keep for historical reference and to prevent accidental recreation.

---

## Questions?

If you need functionality that was in `vibeforge-backend`:

- Check NeuroForge for LLM execution
- Check DataForge for storage/analytics
- Check VibeForge stores for frontend integration

For architecture questions, see:

- `/Forge/README.md` - Forge ecosystem overview
- `/Forge/COMPREHENSIVE_SYSTEM_REVIEW.md` - System architecture

---

**Last Updated**: November 21, 2025  
**Deprecated By**: GitHub Copilot (Claude Sonnet 4.5)  
**Reason**: Architecture violation - functionality moved to proper backends

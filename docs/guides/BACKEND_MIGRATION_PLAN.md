# Backend Migration Plan - vibeforge-backend → NeuroForge + DataForge

**Date:** November 22, 2025  
**Status:** 🚧 Phase 1.2 Complete (LLM Provider Integration)  
**Goal:** Migrate all vibeforge-backend functionality to proper backend services

**Latest:** See [LLM_PROVIDER_INTEGRATION_COMPLETE.md](LLM_PROVIDER_INTEGRATION_COMPLETE.md) for Phase 1.2 details

---

## 🎯 Migration Overview

The `vibeforge-backend` repository contains mixed concerns that violate the Forge architecture. This plan details how to migrate its functionality to the correct backends.

### Current State (Wrong)

```
VibeForge Frontend → vibeforge-backend → [mixed LLM + data + stubs]
```

### Target State (Correct)

```
VibeForge Frontend → NeuroForge (LLM execution, versioning, deployments)
                  → DataForge (context, analytics, storage)
```

---

## 📦 What vibeforge-backend Contains

### 1. LLM Execution Service

**Location:** `python/app/services/llm_service.py`

**Features:**

- Unified LLM interface (Claude, GPT, Ollama)
- Token estimation
- Prompt building
- Error handling
- Provider fallback

**Migration Target:** ⚡ **NeuroForge**

---

### 2. Run Management

**Location:** `python/app/routers/vibeforge.py`

**Endpoints:**

- `POST /v1/vibeforge/run` - Execute LLM run
- `GET /v1/vibeforge/run/{id}` - Get run details
- `GET /v1/vibeforge/history` - List runs

**Migration:**

- Execution logic → **NeuroForge** `/api/v1/workbench/execute`
- Run storage/retrieval → **DataForge** `/api/v1/runs/*`

---

### 3. Storage Layer

**Location:** `python/app/repositories/runs_file.py`, `python/app/storage/json_storage.py`

**Features:**

- Run persistence (JSON files)
- Context storage
- Evaluation storage

**Migration Target:** 📊 **DataForge**

---

### 4. Stub Endpoints

**Location:** `python/app/routers/dataforge.py`, `python/app/routers/neuroforge.py`

**Status:** Placeholders - should be removed after migration

---

## 🔀 Migration Strategy

### Phase 1: NeuroForge Setup (Week 1)

#### 1.1 Create Workbench Module in NeuroForge

```
NeuroForge/
├── app/
│   ├── workbench/              # NEW
│   │   ├── __init__.py
│   │   ├── routes.py           # Workbench-specific routes
│   │   ├── services.py         # LLM execution service
│   │   ├── models.py           # Request/response schemas
│   │   └── providers.py        # LLM provider implementations
```

#### 1.2 Migrate LLM Service

**Source:** `vibeforge-backend/python/app/services/llm_service.py` (485 lines)

**Target:** `NeuroForge/app/workbench/services.py`

**Key Components to Migrate:**

- `UnifiedLLMService` class
- `LLMResponse` dataclass
- Claude provider implementation
- OpenAI provider implementation
- Ollama provider implementation
- Token estimation logic
- Provider status checking

**New NeuroForge Endpoints:**

```python
POST   /api/v1/workbench/execute
POST   /api/v1/workbench/prompts
GET    /api/v1/workbench/prompts/{id}
GET    /api/v1/workbench/prompts/{id}/versions
POST   /api/v1/workbench/tests/generate
POST   /api/v1/workbench/compare
GET    /api/v1/workbench/models
```

**Implementation Steps:**

1. Copy `llm_service.py` to NeuroForge
2. Refactor to NeuroForge conventions
3. Add prompt versioning logic
4. Add test generation endpoints
5. Add model comparison endpoints
6. Update environment variable names
7. Add authentication/authorization
8. Write integration tests

---

### Phase 2: DataForge Setup (Week 1-2)

#### 2.1 Create Runs Module in DataForge

```
DataForge/
├── app/
│   ├── runs/                   # NEW
│   │   ├── __init__.py
│   │   ├── routes.py           # Run logging/retrieval
│   │   ├── models.py           # Run schemas
│   │   └── repository.py       # Database access
```

#### 2.2 Migrate Run Storage

**Source:** `vibeforge-backend/python/app/repositories/runs_file.py`

**Target:** `DataForge/app/runs/repository.py`

**Migration Tasks:**

- Replace JSON file storage with PostgreSQL
- Add TimescaleDB for time-series analytics
- Implement run history queries
- Add aggregation/analytics queries

**New DataForge Endpoints:**

```python
POST   /api/v1/runs              # Log run result
GET    /api/v1/runs              # List runs (with filters)
GET    /api/v1/runs/{id}         # Get run details
GET    /api/v1/analytics/usage   # Usage metrics
GET    /api/v1/analytics/costs   # Cost tracking
POST   /api/v1/workspaces        # Workspace management
```

**Implementation Steps:**

1. Create database schema for runs
2. Migrate run models to DataForge
3. Implement CRUD operations
4. Add analytics queries
5. Add workspace management
6. Write database migrations
7. Write integration tests

---

### Phase 3: Frontend Integration (Week 2)

#### 3.1 Update VibeForge API Clients

**Update neuroforgeClient.ts:**

```typescript
// Remove mock data, implement real HTTP calls
export async function executePrompt(request: ExecutePromptRequest) {
  const response = await fetch(`${NEUROFORGE_API_BASE}/workbench/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify(request),
  });
  return handleResponse(response);
}
```

**Update dataforgeClient.ts:**

```typescript
// Implement run logging
export async function logRun(run: PromptRun) {
  const response = await fetch(`${DATAFORGE_API_BASE}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify(run),
  });
  return handleResponse(response);
}
```

#### 3.2 Update Stores

**Already completed:**

- ✅ `presets.ts` - Prepared for NeuroForge integration
- ✅ `contextStore.ts` - Has `loadContexts()` for DataForge
- ✅ `runStore.ts` - Has `executeRun()` for NeuroForge + DataForge

**Next Steps:**

- Implement actual API calls when backends are ready
- Add error handling UI
- Add loading states
- Add retry logic

---

### Phase 4: Testing & Validation (Week 2-3)

#### 4.1 Integration Testing

- Test VibeForge → NeuroForge execution flow
- Test VibeForge → DataForge logging flow
- Test end-to-end prompt execution
- Test error handling and fallbacks

#### 4.2 Performance Testing

- Load test NeuroForge endpoints
- Load test DataForge endpoints
- Optimize database queries
- Add caching where appropriate

#### 4.3 Security Audit

- Verify API authentication
- Check authorization rules
- Validate input sanitization
- Test rate limiting

---

### Phase 5: Archive vibeforge-backend (Week 3)

#### 5.1 Verification Checklist

- [ ] All LLM execution logic migrated to NeuroForge
- [ ] All storage logic migrated to DataForge
- [ ] All VibeForge API calls point to NeuroForge/DataForge
- [ ] All tests passing
- [ ] Documentation updated
- [ ] No production traffic to vibeforge-backend

#### 5.2 Archive Steps

1. Add `DEPRECATED.md` to vibeforge-backend repo
2. Update README with migration notice
3. Archive GitHub repository
4. Update documentation references
5. Remove from deployment pipelines

---

## 📋 Detailed Task Breakdown

### NeuroForge Tasks (12 tasks)

#### High Priority

- [x] **NF-1:** Create `/app/workbench/` module structure ✅ (Already existed)
- [x] **NF-2:** Migrate `UnifiedLLMService` from vibeforge-backend ✅ (Enhanced existing service)
- [x] **NF-3:** Implement `POST /api/v1/workbench/execute` ✅ (Already implemented)
- [x] **NF-4:** Implement `GET /api/v1/workbench/models` ✅ (Enhanced with Ollama models)
- [ ] **NF-5:** Add prompt versioning storage (PostgreSQL)
- [ ] **NF-6:** Implement `POST /api/v1/workbench/prompts`

#### Medium Priority

- [ ] **NF-7:** Implement `POST /api/v1/workbench/compare` (model comparison)
- [ ] **NF-8:** Implement `POST /api/v1/workbench/tests/generate`
- [ ] **NF-9:** Add streaming support for LLM responses
- [ ] **NF-10:** Add provider fallback logic

#### Low Priority

- [ ] **NF-11:** Add deployment endpoints (API/MCP generation)
- [ ] **NF-12:** Add cost estimation per provider

---

### DataForge Tasks (10 tasks)

#### High Priority

- [ ] **DF-1:** Create `/app/runs/` module structure
- [ ] **DF-2:** Create database schema for runs (TimescaleDB)
- [ ] **DF-3:** Implement `POST /api/v1/runs` (log run)
- [ ] **DF-4:** Implement `GET /api/v1/runs` (list with filters)
- [ ] **DF-5:** Implement `GET /api/v1/runs/{id}` (get details)

#### Medium Priority

- [ ] **DF-6:** Implement `GET /api/v1/analytics/usage`
- [ ] **DF-7:** Implement `GET /api/v1/analytics/costs`
- [ ] **DF-8:** Add workspace management endpoints
- [ ] **DF-9:** Add context storage endpoints (already exists?)

#### Low Priority

- [ ] **DF-10:** Add data export endpoints for analytics

---

### VibeForge Tasks (6 tasks)

#### High Priority

- [ ] **VF-1:** Update `neuroforgeClient.ts` with real API calls
- [ ] **VF-2:** Update `dataforgeClient.ts` with real API calls
- [ ] **VF-3:** Update stores to remove mock data
- [ ] **VF-4:** Add error handling UI components

#### Medium Priority

- [ ] **VF-5:** Add loading states to all async operations
- [ ] **VF-6:** Add retry logic for failed API calls

---

## 🔧 Technical Details

### Environment Variables

**NeuroForge:**

```bash
# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/neuroforge

# Authentication
JWT_SECRET=...
API_KEY_SALT=...
```

**DataForge:**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dataforge
TIMESCALE_ENABLED=true

# Vector Store
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Authentication
JWT_SECRET=...
API_KEY_SALT=...
```

**VibeForge:**

```bash
# Frontend only needs public API endpoints
VITE_NEUROFORGE_API_BASE=http://localhost:8002/api/v1
VITE_DATAFORGE_API_BASE=http://localhost:8001/api/v1
VITE_VIBEFORGE_API_KEY=vf-dev-key
```

---

### Database Schema (DataForge)

**runs table:**

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR(255) NOT NULL,
    prompt_snapshot TEXT NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    output TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_runs_workspace ON runs(workspace_id);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);
CREATE INDEX idx_runs_model ON runs(model_id);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('runs', 'created_at');
```

---

### API Authentication Flow

```
VibeForge (Browser)
    |
    | [Bearer token in header]
    v
NeuroForge/DataForge
    |
    | [Validate JWT/API key]
    v
Protected Resource
```

**Authentication Implementation:**

1. VibeForge sends API key with each request
2. NeuroForge/DataForge validate key against database
3. Check workspace permissions
4. Return 401 if invalid, proceed if valid

---

## 📊 Success Metrics

### Performance Targets

- LLM execution latency: < 5s (P95)
- Run logging latency: < 200ms (P95)
- History retrieval: < 500ms (P95)
- API availability: > 99.9%

### Migration Completion Criteria

- ✅ All vibeforge-backend endpoints deprecated
- ✅ VibeForge using only NeuroForge/DataForge APIs
- ✅ 100% test coverage on critical paths
- ✅ Documentation complete
- ✅ Zero production errors for 1 week

---

## 🚨 Risks & Mitigation

### Risk 1: Breaking Changes

**Mitigation:**

- Deploy both backends simultaneously
- Feature flag new endpoints
- Gradual rollout with monitoring

### Risk 2: Data Loss During Migration

**Mitigation:**

- Keep vibeforge-backend running during migration
- Sync data to new databases
- Verify data integrity before cutover

### Risk 3: Performance Degradation

**Mitigation:**

- Load test before production
- Monitor latency metrics
- Have rollback plan ready

---

## 📅 Timeline

| Week     | Focus                | Deliverables                                       |
| -------- | -------------------- | -------------------------------------------------- |
| Week 1   | NeuroForge Setup     | LLM service migrated, execute endpoint working     |
| Week 2   | DataForge Setup      | Run storage working, analytics queries implemented |
| Week 2-3 | Frontend Integration | All API clients updated, stores connected          |
| Week 3   | Testing              | All tests passing, performance validated           |
| Week 3-4 | Archive              | vibeforge-backend archived, docs updated           |

---

## 🤝 Next Actions

### Immediate (This Week)

1. Review this plan with team
2. Set up NeuroForge `/app/workbench/` module
3. Start migrating `UnifiedLLMService`

### Short Term (Next Week)

1. Implement NeuroForge execute endpoint
2. Set up DataForge runs schema
3. Begin frontend integration

### Long Term (Next Month)

1. Complete all migrations
2. Archive vibeforge-backend
3. Update all documentation

---

**Migration Lead:** GitHub Copilot  
**Plan Date:** November 21, 2025  
**Status:** Ready for Review 📋

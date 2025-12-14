# VibeForge_BDS: Complete Implementation Plan

**Version:** 2.0  
**Status:** Phase 0 - Ready to Begin  
**Timeline:** 42 hours development (Phases 0-5)  
**Organization:** Boswell Digital Solutions LLC  
**Updated:** December 8, 2025

---

## Executive Summary

**VibeForge_BDS** is the internal development orchestration system for the Forge ecosystem. It provides a Tauri desktop interface to access and coordinate **all 120 ForgeAgents skills**, with special focus on the **75 BDS-only skills** for ecosystem-wide development, planning, and governance.

**What It Does:**
- Plan complex multi-repo features using AI (S1-S9, R1-R7)
- Execute code changes automatically (I1-I7, L1-L7)
- Evaluate quality and compliance (P1-P7, O1-O9)
- Coordinate across entire Forge ecosystem (S1-S9)
- Enforce SAS rules automatically (L2, P1-P7)

**Architecture:**
```
VibeForge_BDS (Tauri Desktop, SvelteKit)
    ↓
ForgeAgents Backend (REST API, 120 skills)
    ├→ MAPO (Multi-step orchestration)
    ├→ NeuroForge (Model routing, championing)
    ├→ DataForge (Data persistence, SAS documents)
    └→ Rake (Ingestion pipelines)
```

---

## 1. Product Architecture

### 1.1 Desktop-First Design

**Framework:**
- Tauri 2.x (Rust backend, native OS integration)
- SvelteKit 5 (Frontend, file-based routing)
- TypeScript 5.9 (Full type safety)
- Tailwind CSS v4 (Styling)

**Key Principle:**
Thin client → All AI logic in ForgeAgents backend. VibeForge_BDS is orchestration UI only.

### 1.2 Core Panels

```
┌─────────────────────────────────────────────────────┐
│           VibeForge_BDS Main Window                 │
├─────────────┬──────────────────────┬────────────────┤
│   Skills    │    Planning/Execution │     Output &  │
│  Library    │       Workspace       │   Streaming   │
│             │                      │   Results     │
│  • Public   │  Plan: [text area]   │               │
│    (45)     │  [RUN PLAN]          │  [Streaming   │
│             │                      │   output]     │
│  • BDS      │  Execution: [...]    │               │
│    (75)     │  [EXECUTE]           │   [Results]   │
│             │                      │               │
│  [Search]   │  MAPO Pipeline:      │   [SAS Check] │
│             │  [visual diagram]    │               │
│             │                      │               │
│  History    │  Multi-model routing │   Metrics:    │
│  [Sessions] │  [Toggle Claude/GPT] │   • Cost      │
│  [Pins]     │                      │   • Tokens    │
│             │  [Multi-repo toggle] │   • Time      │
└─────────────┴──────────────────────┴────────────────┘
```

### 1.3 Key Features by Agent Category

| Category | Skills | Feature | Example |
|----------|--------|---------|---------|
| **Planning (R1-R7, S1-S9)** | 14 | Roadmap, strategy, cross-product planning | Plan new AuthorForge feature across 3 repos |
| **Execution (I1-I7, L1-L7)** | 14 | Code generation, implementation, optimization | Auto-implement pull request with tests |
| **Evaluation (O1-O9, P1-P7)** | 16 | Quality metrics, safety, compliance | Auto-evaluate code quality + SAS alignment |
| **Orchestration (L1-L7, M1-M7)** | 14 | MAPO pipelines, model routing, video | Route task to best model, execute workflow |
| **Knowledge (N1-N7, H1-H7)** | 14 | RAG, fine-tuning, data pipelines | Plan DataForge ingestion + chunking |
| **Learning (G1-G7)** | 7 | Teaching, concepts, research | Train team on new Forge capability |
| **Ecosystem (S1-S9)** | 9 | Cross-product sync, standards | Coordinate feature across 5 products |

---

## 2. 120-Skill Access Model

### 2.1 Skill Distribution

```
ForgeAgents Backend
│
├─ 45 PUBLIC SKILLS (Sections A-K, Q)
│  ├─ Learning (A1-A7, G1-G7) → 14 skills
│  ├─ Architecture (B1-B8) → 8 skills
│  ├─ Code (C1-C6, I1-I7) → 13 skills
│  ├─ Writing (C1-C6, Q1-Q7) → 13 skills
│  └─ UX (B6-B7, J1-J7) → 8 skills
│  └─ RAG (H5-H7, N1-N3) → 6 skills
│
└─ 75 BDS-ONLY SKILLS (Sections L-S, P, R, O)
   ├─ Planning (R1-R7, S1-S9) → 14 skills
   ├─ Execution (I1-I7, L1-L7, M1-M7) → 20 skills
   ├─ Evaluation (O1-O9, P1-P7) → 16 skills
   ├─ Orchestration (L1-L7, N1-N7, O1-O9) → 23 skills
   └─ Ecosystem (S1-S9) → 9 skills
```

### 2.2 VibeForge_BDS Only Sees BDS Skills

```
Frontend Permission Check:

User opens VibeForge_BDS
  ↓
Load JWT token (BDS user credentials)
  ↓
GET /api/v1/bds/skills
  → Returns 120 skills with BDS_ONLY marked
  → All 45 public skills + 75 internal
  ↓
UI displays ALL 120 in skill library
  ↓
Skills are filtered/organized by category
```

---

## 3. Core Workflows

### 3.1 Planning Workflow (R1-R7, S1-S9)

**Use Case:** "Add cross-product feature to Forge ecosystem"

```
1. User Input
   "Add real-time collaboration to AuthorForge, 
    integrate with VibeForge, update DataForge 
    for shared workspaces"
   ↓

2. Route to Planning Skills
   • S1 (Forge Interop Planner): Design interaction points
   • S4 (Ecosystem Memory Strategy): Shared data model
   • R2 (Capability Roadmap): Timeline and phases
   • R3 (Risk Forecast): Risk assessment
   ↓

3. Parallel Execution
   • Run all 4 skills in parallel
   • Aggregate results
   • Generate unified plan
   ↓

4. Output
   • Per-repo task breakdown
   • Cross-product dependencies
   • Risk mitigation strategies
   • Timeline estimate
   • SAS compliance notes
```

### 3.2 Execution Workflow (I1-I7, L1-L7)

**Use Case:** "Implement vector similarity search in DataForge"

```
1. User provides task from plan
   "Add POST /similarity endpoint with tests"
   ↓

2. Route to Execution Skills
   • I1 (Clean Code Rewriter): Code structure
   • I3 (Performance Analysis): Optimization hints
   • I5 (CI/CD Advisor): Testing strategy
   • L1 (MAPO Designer): Safety/policy checks
   ↓

3. Parallel Code Generation
   • Generate implementation
   • Generate unit tests (100% coverage required)
   • Generate integration tests
   • Run linting/formatting
   ↓

4. Validation
   • L2 (Policy Validator): SAS compliance check
   • Run all tests
   • Generate PR description
   ↓

5. Output
   • PR ready for review
   • All tests passing
   • SAS compliance verified
   • Cost estimate included
```

### 3.3 Evaluation Workflow (O1-O9, P1-P7)

**Use Case:** "Evaluate model performance on task"

```
1. Load models
   • Claude 3.5 Sonnet
   • GPT-4 Turbo
   • Local Llama
   ↓

2. Route to Evaluation Skills
   • O3 (Scoring Metric Designer): Define quality metrics
   • O8 (Compute Optimizer): Efficiency metrics
   • P5 (Predictable Behavior): Consistency check
   ↓

3. Run evaluations
   • All models on same test set
   • Parallel execution
   • Collect metrics
   ↓

4. Analysis
   • O1 (Champion Criteria): Select best model
   • O7 (Model Comparison): Explain differences
   ↓

5. Output
   • Champion model recommended
   • Performance comparison
   • Cost-benefit analysis
   • Confidence scores
```

### 3.4 Orchestration Workflow (L1-L7)

**Use Case:** "Execute complex multi-step task with fallbacks"

```
1. User describes task
   "Process batch of documents with safety checks"
   ↓

2. Design MAPO pipeline
   • L1 (MAPO Designer): Multi-step workflow
   • L2 (Policy Validator): Safety checks
   • L3 (Local vs Cloud): Model selection
   • L4 (Champion Routing): Champion selection
   ↓

3. Execute pipeline
   • Step 1: Local validation
   • Step 2: Cloud processing (if needed)
   • Step 3: Safety check
   • Step 4: Result merge
   ↓

4. Handle failures
   • L5 (Conflict Resolver): Merge disagreements
   • Retry with fallback model
   • Log for analysis
   ↓

5. Output
   • Result + confidence
   • Execution trace
   • Cost breakdown
   • Performance metrics
```

---

## 4. Implementation Phases

### Phase 0: Backend Client Layer (4 hours) — **THIS IS TODAY**

**Deliverables:**
- ForgeAgents API client (auth, token management)
- Skill discovery endpoints
- Streaming response handling
- Error handling + retry logic

**Files to Create:**
```
src/lib/api/
├── forgeAgentsClient.ts      ← Core API client
├── skillRegistry.ts          ← Skill discovery
├── types.ts                  ← API types
└── auth.ts                   ← Token management
```

**Success Criteria:**
- ✅ Can call ForgeAgents `/api/v1/bds/skills`
- ✅ Can invoke a simple skill (A1 or B1)
- ✅ Can stream responses
- ✅ Tokens refresh automatically

---

### Phase 1: Core UI & Skill Library (8 hours)

**Deliverables:**
- Skill library panel (search, filter, categories)
- Skill detail view
- Quick test UI
- Favorites/pins

**Files to Create:**
```
src/routes/
├── +page.svelte              ← Main workbench
├── library/
│   ├── +page.svelte          ← Skill library
│   ├── SkillCard.svelte       ← Skill display
│   └── SkillDetail.svelte     ← Skill details
└── quick-test/
    └── +page.svelte          ← Test runner
```

**Success Criteria:**
- ✅ Display all 120 skills organized by section
- ✅ Search and filter skills
- ✅ Can invoke any skill from UI
- ✅ Results display with streaming

---

### Phase 2: Planning Panel (12 hours)

**Deliverables:**
- Planning input form
- Multi-skill orchestration
- Plan visualization
- SAS compliance display

**Files to Create:**
```
src/routes/
└── planning/
    ├── +page.svelte          ← Planning panel
    ├── PlanningForm.svelte    ← Input form
    ├── PlanDisplay.svelte     ← Results display
    ├── SASChecker.svelte      ← Compliance
    └── RiskAssessment.svelte  ← Risk display
```

**Success Criteria:**
- ✅ User inputs feature description
- ✅ System calls 4-6 planning skills
- ✅ Aggregates results into unified plan
- ✅ Displays SAS compliance status
- ✅ Estimates effort and risk

---

### Phase 3: Execution Panel (10 hours)

**Deliverables:**
- Code generation UI
- Test runner integration
- PR creation
- Multi-model comparison

**Files to Create:**
```
src/routes/
└── execution/
    ├── +page.svelte          ← Execution panel
    ├── CodeGenerator.svelte   ← Generation UI
    ├── TestRunner.svelte      ← Test execution
    ├── MultiModel.svelte      ← Model comparison
    └── PRBuilder.svelte       ← PR generation
```

**Success Criteria:**
- ✅ Takes task from plan
- ✅ Generates code with I1-I7 skills
- ✅ Runs tests (100% pass required)
- ✅ Validates SAS compliance
- ✅ Creates PR with description

---

### Phase 4: Evaluation & Coordination (8 hours)

**Deliverables:**
- Model evaluation UI
- Cross-product coordination
- Multi-agent workflow visualization

**Files to Create:**
```
src/routes/
├── evaluation/
│   └── +page.svelte          ← Evaluation panel
└── coordination/
    └── +page.svelte          ← Coordination panel
```

**Success Criteria:**
- ✅ Evaluate models on test set
- ✅ Display comparison metrics
- ✅ Plan cross-product features
- ✅ Visualize dependencies

---

### Phase 5: Polish & Production (4 hours)

**Deliverables:**
- Performance optimization
- Error handling
- Documentation
- Desktop packaging

**Success Criteria:**
- ✅ App runs smoothly
- ✅ No console errors
- ✅ Tauri builds successfully
- ✅ Ready for internal use

---

## 5. Technology Stack

**Frontend:**
- SvelteKit 5
- TypeScript 5.9
- Tailwind CSS v4
- Svelte runes (`$state`, `$derived`)

**Desktop:**
- Tauri 2.x
- Rust backend

**Backend Integration:**
- ForgeAgents (REST API)
- MAPO (orchestration)
- NeuroForge (model routing)
- DataForge (data persistence)

**Development:**
- Vite 7.x
- Vitest
- pnpm

---

## 6. API Contracts

### 6.1 Authentication

```typescript
// Login
POST /api/v1/auth/login
{
  "email": "charles@bds.com",
  "password": "***"
}

Response:
{
  "access_token": "jwt_token_here",
  "refresh_token": "refresh_token_here",
  "expires_at": "2025-12-09T12:00:00Z"
}

// Token refresh
POST /api/v1/auth/refresh
{
  "refresh_token": "refresh_token_here"
}
```

### 6.2 Skill Discovery

```typescript
// List all BDS skills
GET /api/v1/bds/skills
  Authorization: Bearer {access_token}

Response:
[
  {
    "id": "R1",
    "name": "Product Strategy Mapper",
    "section": "R",
    "description": "...",
    "inputs": { "vision": "string", "timeframe": "string" },
    "access": "BDS_ONLY",
    "category": "strategy"
  },
  ...
]

// Search skills
GET /api/v1/bds/skills/search?query=planning
  Authorization: Bearer {access_token}
```

### 6.3 Skill Invocation

```typescript
// Invoke skill
POST /api/v1/bds/skills/{skillId}/invoke
{
  "inputs": {
    "vision": "Real-time collaboration across Forge",
    "timeframe": "Q1 2026"
  },
  "options": {
    "model": "claude-3.5-sonnet",
    "temperature": 0.7
  }
}

Response (non-streaming):
{
  "sessionId": "sess_123456",
  "status": "success",
  "output": "...",
  "metadata": {
    "tokens_used": 2345,
    "cost": 0.0082,
    "latency_ms": 3450
  }
}

// Streaming
POST /api/v1/bds/skills/{skillId}/invoke?stream=true
  → Server-Sent Events stream
```

---

## 7. Data Models

### 7.1 Skill Definition

```typescript
interface Skill {
  id: string;           // A1, R2, S7, etc.
  name: string;
  section: string;      // A, R, S, etc.
  version: number;
  description: string;
  inputs: Record<string, InputType>;
  outputs: OutputType;
  access: "PUBLIC" | "BDS_ONLY";
  category: SkillCategory;
  tags: string[];
  estimatedCost: { min: number, max: number };
  modelCompatibility: string[];
  examples?: string[];
}

type SkillCategory = 
  | "learning"
  | "architecture"
  | "code"
  | "planning"
  | "execution"
  | "evaluation"
  | "orchestration"
  | "ecosystem";
```

### 7.2 Execution Session

```typescript
interface ExecutionSession {
  sessionId: string;
  skillId: string;
  status: "pending" | "running" | "completed" | "failed";
  inputs: Record<string, any>;
  output?: string;
  error?: string;
  metadata: {
    startedAt: Date;
    completedAt?: Date;
    tokensUsed: number;
    cost: number;
    model: string;
  };
}

interface ExecutionPlan {
  planId: string;
  description: string;
  steps: ExecutionSession[];
  dependencies: Map<string, string[]>;
  estimatedCost: number;
  estimatedTime: number;
  sasCompliance: {
    status: "pass" | "warn" | "fail";
    violations: string[];
  };
}
```

---

## 8. Security & Access Control

### 8.1 Authentication

- JWT tokens with 1-hour expiry
- Refresh tokens with 30-day expiry
- Stored in Tauri secure storage
- Automatic token refresh before expiry

### 8.2 Authorization

- BDS users only (email domain check)
- Skill access control (PUBLIC vs BDS_ONLY)
- Audit logging of all API calls
- Rate limiting (1000 req/min per user)

### 8.3 Data Protection

- HTTPS only
- API keys never logged
- SAS compliance automatic
- Execution logs stored in DataForge

---

## 9. Development Workflow

### 9.1 Quick Start

```bash
# Clone and setup
git clone https://github.com/bds/vibeforge_bds
cd vibeforge_bds
pnpm install

# Environment
cp .env.example .env
# Edit .env with:
VITE_FORGE_AGENTS_URL=http://localhost:8100
VITE_BDS_API_KEY=your-internal-key

# Dev server
pnpm dev

# Tauri dev
npm run tauri dev

# Build desktop app
npm run tauri build
```

### 9.2 Git Workflow

```bash
# Feature branch
git checkout -b phase-0-backend-client

# After each task
git add -A
git commit -m "feat: Add ForgeAgents client"
git tag phase-0-task-1-complete

# When phase complete
git tag phase-0-complete
git push origin phase-0-complete
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```bash
pnpm test
```

**Coverage:**
- API client (auth, tokens, errors)
- Skill registry
- Data transformations
- Type safety

### 10.2 Integration Tests

- ForgeAgents API connectivity
- Skill invocation
- Streaming responses
- Error handling

### 10.3 E2E Tests

- Login workflow
- Skill discovery
- Planning workflow
- Execution workflow

---

## 11. Success Metrics by Phase

### Phase 0 (Today)
- ✅ ForgeAgents API client works
- ✅ Can list 120 skills
- ✅ Can invoke a skill successfully
- ✅ Can stream responses

### Phase 1
- ✅ Display all 120 skills in library
- ✅ Search/filter works
- ✅ Can test any skill from UI

### Phase 2
- ✅ User inputs feature description
- ✅ System generates multi-skill plan
- ✅ Shows SAS compliance status

### Phase 3
- ✅ Generate code from task
- ✅ Run tests (100% pass)
- ✅ Create PR automatically

### Phase 4
- ✅ Evaluate models
- ✅ Plan cross-product features
- ✅ Show dependencies

### Phase 5
- ✅ App ready for production use
- ✅ No errors
- ✅ Desktop app builds
- ✅ Team can use for development

---

## 12. Timeline & Effort

| Phase | Tasks | Hours | Status |
|-------|-------|-------|--------|
| **0** | Backend client | 4h | 🔴 Starting |
| **1** | UI & library | 8h | ⏳ Next |
| **2** | Planning | 12h | ⏳ Next |
| **3** | Execution | 10h | ⏳ Later |
| **4** | Evaluation | 8h | ⏳ Later |
| **5** | Polish | 4h | ⏳ Later |
| **TOTAL** | | **46h** | |

**Charles's Focus:** Phase 0 today (4h), then Phase 1-5 across next 4 weeks

---

## 13. Deliverables Checklist

### Phase 0 (Today - 4h)
- [ ] Create `src/lib/api/forgeAgentsClient.ts`
- [ ] Create `src/lib/api/skillRegistry.ts`
- [ ] Create `src/lib/api/auth.ts`
- [ ] Create `src/lib/api/types.ts`
- [ ] Test skill discovery
- [ ] Git tag: `phase-0-complete`

### Phase 1 (Next week - 8h)
- [ ] Skill library UI
- [ ] Search/filter
- [ ] Quick test runner
- [ ] Skill details view

### Phase 2+ (Following weeks)
- [ ] Planning panel
- [ ] Execution panel
- [ ] Evaluation UI
- [ ] Coordination dashboard

---

## 14. Key Principles

1. **Thin Client:** All logic in ForgeAgents, UI just orchestrates
2. **Skill-First:** Every feature is a skill invocation
3. **Multi-Model:** Route through NeuroForge for optimal model selection
4. **SAS-First:** Automatic compliance checking on everything
5. **Async Everywhere:** Non-blocking operations, streaming results
6. **Type Safety:** 100% TypeScript, no `any` types

---

## 15. Resources

- **ForgeAgents 120-Skill API Registry:** `ForgeAgents_120_Skill_API_Registry.md`
- **Public VibeForge Guide:** `VibeForge_Public_Edition_Guide.md`
- **Development Setup:** `DEVELOPMENT.md`

---

**Start Date:** December 8, 2025  
**Phase 0 Target:** Today end-of-day  
**Full Completion:** January 26, 2026

**Ready to build.** ⚒️

# 📚 Forge Ecosystem Documentation Map

**Last Updated**: November 21, 2025  
**Status**: ✅ Fully Organized & Consolidated

---

## 🎯 START HERE

### Quick Links by Role

| Role                   | Start Here                                                           | Time   | Purpose           |
| ---------------------- | -------------------------------------------------------------------- | ------ | ----------------- |
| 👨‍💻 **Developer**       | [README.md](./README.md)                                             | 2 min  | Overview & setup  |
| 🤖 **AI Agent**        | [.github/copilot-instructions.md](./.github/copilot-instructions.md) | 5 min  | Core guidance     |
| 🚀 **DevOps/Operator** | [README.md](./README.md) → Deployment sections                       | 10 min | Deployment guides |
| 📊 **Project Manager** | [INDEX.md](./INDEX.md)                                               | 5 min  | Status & progress |
| 🧪 **QA/Tester**       | [docs/guides/](./docs/guides/)                                       | 15 min | Test procedures   |

---

## 📂 Documentation Structure

### Root Level (Active, Current)

```
Forge/
├── README.md                      ← START HERE (overview + quick setup)
├── INDEX.md                       ← Ecosystem master index
├── 00_GET_STARTED_HERE.md        ← Quick start for new users
├── DOCUMENTATION_GUIDE.txt        ← Visual reference guide
├── MASTER_INDEX_DOCUMENTATION.md  ← Detailed file catalog
│
├── DataForge/INDEX.md             ← Service: Knowledge base backend
├── NeuroForge/INDEX.md            ← Service: LLM orchestration
├── AuthorForge_Solid_new/INDEX.md ← Service: Writing suite
├── vibeforge/INDEX.md             ← Service: Prompt workbench
├── vibeforge-backend/INDEX.md     ← Service: Unified LLM service
│
├── .github/
│   └── copilot-instructions.md    ← AI agent guidance
│
└── docs/                          ← All archived & reference docs
    ├── archive/                   ← Historical documentation
    │   ├── phase-1/              ← DataForge phase completions
    │   ├── phase-2/              ← NeuroForge phase completions
    │   ├── phase-3/              ← AuthorForge/VibeForge completions
    │   └── phase-4/              ← Phase 4 planning & progress
    │
    ├── guides/                    ← How-to guides & references
    │   ├── *GUIDE*.md
    │   └── *RESEARCH*.md
    │
    └── references/                ← Handoffs, status updates
        ├── SESSION_*.md
        ├── HANDOFF_*.md
        └── WEEK_*.md
```

---

## 🚀 Getting Started (3 Steps)

### Step 1: Understand the Ecosystem (5 minutes)

Read **[README.md](./README.md)** for:

- The 7 services overview
- Local development setup (6 terminals)
- Tech stack & architecture
- Key takeaways

### Step 2: Explore Service Documentation (10-15 minutes)

Choose your service and read its `INDEX.md`:

- **[DataForge/INDEX.md](./DataForge/INDEX.md)** - Knowledge base backend
- **[NeuroForge/INDEX.md](./NeuroForge/INDEX.md)** - LLM orchestration
- **[AuthorForge_Solid_new/INDEX.md](./AuthorForge_Solid_new/INDEX.md)** - Writing suite
- **[vibeforge/INDEX.md](./vibeforge/INDEX.md)** - Prompt workbench
- **[vibeforge-backend/INDEX.md](./vibeforge-backend/INDEX.md)** - Unified LLM

### Step 3: Get Detailed Guidance (As Needed)

- **Setting up locally**: Check service `README.md` → Setup section
- **Running tests**: Check service `README.md` → Testing section
- **Deploying**: Check [docs/guides/](./docs/guides/) for deployment procedures
- **Understanding architecture**: Check service `.github/copilot-instructions.md`
- **Historical context**: Check [docs/archive/](./docs/archive/) for phase-specific info

---

## 📚 Core Services

### The 7 Services

| Service                 | Type                 | Port | Status            | Doc                                          |
| ----------------------- | -------------------- | ---- | ----------------- | -------------------------------------------- |
| **DataForge**           | Backend API          | 8001 | ✅ Phase 4 (95%)  | [INDEX.md](./DataForge/INDEX.md)             |
| **NeuroForge**          | LLM Orchestration    | 8002 | ✅ Phase 4 (95%)  | [INDEX.md](./NeuroForge/INDEX.md)            |
| **AuthorForge_Solid**   | Frontend (SolidJS)   | 3000 | ✅ Phase 3+ (95%) | [INDEX.md](./AuthorForge_Solid_new/INDEX.md) |
| **VibeForge**           | Frontend (SvelteKit) | 5173 | ✅ Phase 3+ (95%) | [INDEX.md](./vibeforge/INDEX.md)             |
| **vibeforge-backend**   | Unified LLM          | 8003 | ✅ Phase 2 (95%)  | [INDEX.md](./vibeforge-backend/INDEX.md)     |
| **NeuroForge Frontend** | Frontend (SvelteKit) | 5174 | 🚧 In Dev         | —                                            |
| **AuthorForge**         | Backend (Python)     | 8000 | ✅ Phase 1 (95%)  | —                                            |

---

## 📖 What's Organized Where?

### Active Documentation (Root Level)

**Use these to get started:**

- `README.md` - Project overview & quick start
- `INDEX.md` - Master ecosystem guide
- `00_GET_STARTED_HERE.md` - Quick orientation
- `.github/copilot-instructions.md` - AI agent guidance

### Service Guides (In Each Service Folder)

**Use these for service-specific work:**

- `DataForge/INDEX.md` - Knowledge base guidance
- `NeuroForge/INDEX.md` - LLM orchestration guidance
- `AuthorForge_Solid_new/INDEX.md` - Writing suite guidance
- `vibeforge/INDEX.md` - Prompt workbench guidance
- `vibeforge-backend/INDEX.md` - Unified LLM guidance

### How-To Guides (docs/guides/)

**Use these for specific tasks:**

- `*GUIDE*.md` - Connector guides, integration guides
- `*RESEARCH*.md` - Research & architecture notes
- `OUTPUTCOLUMN_INTEGRATION.md` - Feature integration guide

### Historical Documentation (docs/archive/)

**Reference only (no longer active):**

- `phase-1/` - DataForge completions & quick refs
- `phase-2/` - NeuroForge completions & quick refs
- `phase-3/` - AuthorForge/VibeForge completions & verification
- `phase-4/` - Phase 4 planning, checklist, delivery reports

### Session References (docs/references/)

**Use for context or historical info:**

- `HANDOFF_*.md` - End-of-session handoffs
- `SESSION_*.md` - Session status updates
- `WEEK_*.md` - Weekly integration plans
- `CONSOLIDATION_*.md` - Consolidation reports

---

## ✅ Current Project Status

### Completion Metrics

- **Overall**: 95% complete (7 services, Phase 4)
- **Tests**: 255+ total (86% coverage)
- **Documentation**: 100+ files organized
- **Entry Points**: 7 clear paths per role

### By Service

- ✅ **DataForge** - Phase 4 Complete (95% - External Search)
- ✅ **NeuroForge** - Phase 4 Complete (95% - LLM Orchestration)
- ✅ **AuthorForge_Solid** - Phase 3+ Complete (95% - 7 Pages)
- ✅ **VibeForge** - Phase 3+ Complete (95% - 9 Pages)
- ✅ **vibeforge-backend** - Phase 2 Complete (95% - Unified LLM)
- 🚧 **NeuroForge Frontend** - In Development (SvelteKit)
- ✅ **AuthorForge** - Phase 1 Complete (95% - Python Backend)

---

## 🔗 Quick Links

**I want to...**

| Goal                        | Link                                                                 | Time   |
| --------------------------- | -------------------------------------------------------------------- | ------ |
| Understand the architecture | [INDEX.md](./INDEX.md)                                               | 5 min  |
| Set up locally              | [README.md](./README.md) → Setup                                     | 10 min |
| Run the system              | [00_GET_STARTED_HERE.md](./00_GET_STARTED_HERE.md)                   | 5 min  |
| Read service docs           | Choose service [INDEX.md](#core-services)                            | 15 min |
| Check deployment            | [docs/guides/](./docs/guides/)                                       | 10 min |
| Review project status       | [INDEX.md](./INDEX.md) → Status                                      | 3 min  |
| Find AI guidance            | [.github/copilot-instructions.md](./.github/copilot-instructions.md) | 5 min  |
| Look up historical info     | [docs/archive/](./docs/archive/)                                     | varies |

---

## 🎯 Key Takeaways

1. **Start with README.md** - Get overview in 2 minutes
2. **Then read INDEX.md** - Understand full architecture in 5 minutes
3. **Choose your service** - Read service-specific INDEX.md (10-15 min)
4. **Reference guides** - Use docs/guides/ for specific tasks
5. **Historical context** - Check docs/archive/ if you need phase history
6. **AI agents** - Always check .github/copilot-instructions.md in relevant service

---

## 📞 Documentation Structure Summary

```
Need quick info?          → README.md (2 min)
Need architecture view?   → INDEX.md (5 min)
Need service details?     → Service/INDEX.md (15 min)
Need specific task help?  → docs/guides/ (varies)
Need historical context?  → docs/archive/ (varies)
Need AI guidance?         → .github/copilot-instructions.md (5 min)
```

---

**Last Updated**: November 21, 2025  
**All documentation consolidated, organized, and ready for use** ✅

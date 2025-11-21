# 📚 NeuroForge Documentation Map

**Last Updated**: November 21, 2025  
**Status**: ✅ All documentation organized & accessible

---

## 🎯 START HERE

### Quick Navigation by Role

| Role                        | Document                                                                           | Time   |
| --------------------------- | ---------------------------------------------------------------------------------- | ------ |
| **New Developer**           | [README.md](../../README.md)                                                       | 5 min  |
| **AI Agent Guidance**       | [.github/copilot-instructions.md](../../.github/copilot-instructions.md)           | 10 min |
| **Quick Start**             | [docs/setup/DEVELOPER_QUICK_REFERENCE.md](docs/setup/DEVELOPER_QUICK_REFERENCE.md) | 10 min |
| **Understand the Pipeline** | [INDEX.md](INDEX.md)                                                               | 10 min |
| **Backend Setup**           | [docs/setup/BACKEND_SETUP_COMPLETE.md](docs/setup/BACKEND_SETUP_COMPLETE.md)       | 15 min |

---

## 📂 Documentation Structure

### Root Level (Active Documents)

**Core Guides:**

- `INDEX.md` - Master index & 5-stage pipeline overview
- `README.md` - Project overview (in parent /Forge directory)

### docs/setup/ (Setup & Development)

**Getting started & references:**

- `DEVELOPER_QUICK_REFERENCE.md` - Commands & patterns
- `BACKEND_SETUP_COMPLETE.md` - Backend installation
- `REVIEW_INDEX.md` - Code review procedures

### docs/guides/ (Integration & Features)

**Feature implementation & integration:**

- `PHASE_3_DASHBOARD_IMPLEMENTATION.md` - Dashboard features
- `VISUAL_SUMMARY.md` - Architecture visual overview

### docs/archive/ (Historical Documentation)

**Phase completions & technical reviews:**

- `PHASE_*.md` - Phase documentation (1-4)
- `*_COMPLETE.md` - Completion reports
- `*_REVIEW.md` - Technical/due diligence reviews
- `*FIXES*.md` - Bug fixes & patches
- `*ACTION*.md` - Action items & remediation

---

## 🎯 The 5-Stage Pipeline

1. **ContextBuilder** - Fetches context from DataForge
2. **PromptEngine** - Applies domain-specific templates
3. **ModelRouter** - Ensemble voting & fallback chains
4. **Evaluator** - LLM-based scoring
5. **PostProcessor** - Format normalization & persistence

**⚠️ Critical**: Always use `context_builder_fixed.py` (original is corrupted)

---

## 🎯 Common Tasks

### I want to...

| Goal                            | Location                                                                                           |
| ------------------------------- | -------------------------------------------------------------------------------------------------- |
| Understand the 5-stage pipeline | [INDEX.md](INDEX.md)                                                                               |
| Set up the backend              | [docs/setup/BACKEND_SETUP_COMPLETE.md](docs/setup/BACKEND_SETUP_COMPLETE.md)                       |
| Find development commands       | [docs/setup/DEVELOPER_QUICK_REFERENCE.md](docs/setup/DEVELOPER_QUICK_REFERENCE.md)                 |
| Understand dashboard features   | [docs/guides/PHASE_3_DASHBOARD_IMPLEMENTATION.md](docs/guides/PHASE_3_DASHBOARD_IMPLEMENTATION.md) |
| Review architecture             | [INDEX.md](INDEX.md)                                                                               |
| Check past fixes                | [docs/archive/FIXES_APPLIED.md](docs/archive/FIXES_APPLIED.md)                                     |
| Review phase history            | [docs/archive/](docs/archive/)                                                                     |

---

## 📊 Project Status

**Status**: 95% Complete  
**Phase**: 4 (LLM Orchestration Engine Complete)  
**Architecture**: 5-stage pipeline fully implemented
**Tests**: 100+

---

## 📞 Key Files Reference

| File              | Purpose                           |
| ----------------- | --------------------------------- |
| **INDEX.md**      | Master index & pipeline overview  |
| **docs/setup/**   | Setup & development guides        |
| **docs/guides/**  | Feature implementation docs       |
| **docs/archive/** | Phase history & technical reviews |

---

**All documentation organized, archived, and accessible** ✅

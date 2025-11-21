# 📚 vibeforge-backend Documentation Map

**Last Updated**: November 21, 2025  
**Status**: ✅ All documentation organized & accessible

---

## 🎯 START HERE

### Quick Navigation by Role

| Role               | Document                                                                 | Time   |
| ------------------ | ------------------------------------------------------------------------ | ------ |
| **New Developer**  | [README.md](README.md)                                                   | 5 min  |
| **Quick Start**    | [docs/setup/DEVELOPER_QUICKSTART.md](docs/setup/DEVELOPER_QUICKSTART.md) | 10 min |
| **Architecture**   | [ARCHITECTURE.md](ARCHITECTURE.md)                                       | 15 min |
| **API Reference**  | [docs/guides/API_REFERENCE.md](docs/guides/API_REFERENCE.md)             | 15 min |
| **Integration**    | [docs/guides/INTEGRATION_GUIDE.md](docs/guides/INTEGRATION_GUIDE.md)     | 20 min |
| **Project Status** | [INDEX.md](INDEX.md)                                                     | 10 min |

---

## 📂 Documentation Structure

### Root Level (Active Documents)

**Core Guides:**

- `README.md` - Project overview & setup
- `ARCHITECTURE.md` - System design & Rust integration
- `INDEX.md` - Master index
- `QUICKSTART.md` - Quick start guide
- `SETUP.md` - Installation & configuration
- `BUILD_INSTRUCTIONS.md` - Build procedures
- `DEPLOYMENT_GUIDE.md` - Production deployment

### docs/setup/ (Setup & Development)

**Getting started & development guides:**

- `DEVELOPER_QUICKSTART.md` - Quick start commands
- `BUILD_INSTRUCTIONS.md` - Building Rust extensions
- Setup & environment configuration

### docs/guides/ (Integration & API)

**API reference & integration procedures:**

- `API_REFERENCE.md` - All REST endpoints
- `API_IMPLEMENTATION_SUMMARY.md` - Implementation overview
- `INTEGRATION_GUIDE.md` - Integration procedures
- `INTEGRATION_INDEX.md` - Integration reference
- `INTEGRATION_SETUP.md` - Integration setup
- `DEPLOYMENT_GUIDE.md` - Deployment procedures
- `FORGE_ECOSYSTEM_INTEGRATION_ARCHITECTURE.md` - Ecosystem integration
- `LLM_SERVICE_DOCS_INDEX.md` - LLM service reference

### docs/archive/ (Historical Documentation)

**Implementation & delivery history:**

- `*_DELIVERY*.md` - Delivery summaries & manifests
- `*_COMPLETE.md` - Completion reports
- `*_IMPLEMENTATION*.md` - Implementation guides
- `*_CHECKLIST.md` - Task checklists

### docs/references/ (Technical Reviews)

**Technical due diligence & executive summaries:**

- `TECHNICAL_DUE_DILIGENCE_EXECUTIVE_SUMMARY.md` - Executive summary

---

## 🎯 The Unified LLM Service

**Tech Stack:**

- FastAPI (Python backend)
- PyO3 + Rust extensions
- Maturin (build tool)
- Multi-provider LLM routing

**Rust Crates:**

- `forge_core` - Core types
- `forge_prompt` - Prompt building & token estimation
- `forge_data` - Document ingestion
- `forge_eval` - Evaluation & scoring

---

## 🎯 API Endpoints

**Main Endpoints:**

- `/v1/vibeforge/run` - Create model runs
- `/v1/vibeforge/context` - Manage context blocks
- `/v1/vibeforge/history` - Run history & retrieval
- `/v1/dataforge/*` - DataForge integration
- `/v1/neuroforge/*` - NeuroForge integration

**See**: [docs/guides/API_REFERENCE.md](docs/guides/API_REFERENCE.md) for complete reference

---

## 🎯 Common Tasks

### I want to...

| Goal                           | Location                                                                 |
| ------------------------------ | ------------------------------------------------------------------------ |
| Set up development environment | [README.md](README.md) → Setup section                                   |
| Quick start with examples      | [docs/setup/DEVELOPER_QUICKSTART.md](docs/setup/DEVELOPER_QUICKSTART.md) |
| Understand system architecture | [ARCHITECTURE.md](ARCHITECTURE.md)                                       |
| See all API endpoints          | [docs/guides/API_REFERENCE.md](docs/guides/API_REFERENCE.md)             |
| Integrate with Forge ecosystem | [docs/guides/INTEGRATION_GUIDE.md](docs/guides/INTEGRATION_GUIDE.md)     |
| Deploy to production           | [docs/guides/DEPLOYMENT_GUIDE.md](docs/guides/DEPLOYMENT_GUIDE.md)       |
| Build Rust extensions          | [docs/setup/BUILD_INSTRUCTIONS.md](docs/setup/BUILD_INSTRUCTIONS.md)     |
| Review implementation          | [docs/archive/](docs/archive/)                                           |

---

## 📊 Project Status

**Status**: 95% Complete  
**Framework**: FastAPI + Python/Rust hybrid
**APIs**: Unified LLM service with multi-provider routing
**Build**: Maturin-based Rust compilation

---

## 📞 Key Files Reference

| File                                 | Purpose                    |
| ------------------------------------ | -------------------------- |
| **README.md**                        | Project overview           |
| **ARCHITECTURE.md**                  | System design              |
| **INDEX.md**                         | Master index               |
| **docs/setup/**                      | Setup & build guides       |
| **docs/guides/API_REFERENCE.md**     | Complete API documentation |
| **docs/guides/INTEGRATION_GUIDE.md** | Integration procedures     |
| **docs/guides/DEPLOYMENT_GUIDE.md**  | Production deployment      |
| **docs/archive/**                    | Implementation history     |

---

**All documentation organized, archived, and accessible** ✅

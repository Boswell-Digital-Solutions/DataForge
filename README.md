<p align="center">
  <img src="https://firebasestorage.googleapis.com/v0/b/endless-fire-467204-n2.firebasestorage.app/o/Forge%2FForge_Ecosystem_icon.avif?alt=media&token=4f342440-6299-46c0-a825-c37b1f75170d"
       alt="Forge Ecosystem Logo"
       width="200"
       style="border-radius: 12px;" />
</p>

<h1 align="center">🔥 The Forge Ecosystem</h1>
<h3 align="center">Professional AI Development Platform</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active%20Development-blue" />
  <img src="https://img.shields.io/badge/License-Commercial-red" />
  <img src="https://img.shields.io/badge/Products-8%20Applications-blue" />
  <img src="https://img.shields.io/badge/VibeForge-Freeware-purple" />
  <img src="https://img.shields.io/badge/Documentation-12%2C300%2B%20lines-green" />
</p>

---

> **License:** Commercial – All products except VibeForge are proprietary commercial software.  
> **VibeForge:** Freeware with restrictions (entry product).  
> **© 2025 Boswell Digital Solutions LLC. All Rights Reserved.**  
> All intellectual property, code, datasets, and documentation are owned by BDS.  
> See individual product READMEs for specific licensing terms.

---

## 📑 Table of Contents

1. [Forge Ecosystem Overview](#-forge-ecosystem-overview)
2. [Core Products](#-core-products)
3. [System Architecture](#-system-architecture)
4. [Getting Started](#-getting-started)
5. [DataForge (Core Engine)](#-dataforge-core-engine)
6. [Project Status](#-project-status)
7. [Documentation](#-documentation)
8. [Technology Stack](#-technology-stack)
9. [Security & Compliance](#-security--compliance)
10. [License & Copyright](#-license--copyright)
11. [Support & Contact](#-support--contact)

---

## 🔥 Forge Ecosystem Overview

**The Forge Ecosystem** is a cathedral-level development platform comprising eight specialized products for AI-driven content creation, intelligent project automation, market intelligence, and data management. All products share a unified backend architecture powered by **DataForge** (data engine) and **NeuroForge** (AI orchestration).

### What is Forge?

Forge is an **integrated professional platform** where:

- 🔓 **VibeForge** (Freeware) – AI prompt engineering workbench (entry product)
- 🔒 **DataForge** (Commercial) – Core data engine and knowledge layer
- 🔒 **NeuroForge** (Commercial) – LLM orchestration and model routing
- 🔒 **ForgeAgents** (Commercial) – Autonomous agent orchestration layer
- 🔒 **AuthorForge** (Commercial) – Genre-aware creative writing assistant
- 🔒 **TradeForge** (Commercial) – Market intelligence and financial datasets
- 🔒 **Leopold/Livy** (Commercial) – Ecological and historical analysis modules
- 🔍 **Cortex** (Standalone) – Desktop file intelligence and search

### Unified Architecture

- ✅ **Shared Intelligence Layer** – DataForge stores all product knowledge
- ✅ **Centralized AI Orchestration** – NeuroForge routes LLM requests across all products
- ✅ **Autonomous Agents** – ForgeAgents coordinates cross-service automation
- ✅ **Commercial Backend** – All products (including VibeForge) connect to commercial services
- ✅ **Enterprise-Grade Security** – OAuth2, field-level encryption, audit logs
- ✅ **Production Observability** – Prometheus, OpenTelemetry, Grafana monitoring

### Quick Facts

| Metric                       | Value                                      |
| ---------------------------- | ------------------------------------------ |
| **Ecosystem Status**         | 🔵 Active Development (Alpha/Beta)         |
| **Free Entry Product**       | VibeForge (Freeware with restrictions)     |
| **Commercial Products**      | 6 (DataForge, NeuroForge, ForgeAgents, AuthorForge, TradeForge, Leopold/Livy) |
| **Standalone Product**       | Cortex (Desktop file intelligence)         |
| **DataForge Version**        | 5.2 (18/18 core phases complete)           |
| **ForgeAgents Version**      | 0.1.0 (Phase 7 complete, production-ready) |
| **VibeForge Version**        | 5.6 (695 tests, Jan 2026 launch)           |
| **RAG Pipeline**             | Production Ready ✅                         |
| **Total Documentation**      | 12,300+ lines                              |
| **Production Code**          | 53,250+ lines (includes ForgeAgents 20K)   |
| **Ecosystem Version**        | 5.3                                        |

---

## 🧩 Core Products

The Forge Ecosystem consists of 8 specialized products with unified backend infrastructure:

### 1. VibeForge 🎨 – AI Prompt Engineering Workbench (FREEWARE)

- **Purpose:** Pro-grade prompt creation and testing environment
- **Status:** 🟣 **Beta** - Free download, restricted modifications
- **Repository:** `./vibeforge/`
- **License:** Freeware with restrictions (see VibeForge README)
- **Backend:** Uses commercial NeuroForge + DataForge services
- **Key Features:**
  - 3-column prompt builder with Monaco editor
  - Multi-model test runner (local + cloud)
  - 15 languages across 4 categories
  - 10 production-ready stack profiles
  - Learning-based recommendations with success prediction
  - Export to JSON/Markdown/Claude/Augment
  - MCP support and plugin system
  - **Code Analysis & GitHub Integration:**
    - Architecture analysis (complexity, code smells, god functions)
    - Security scanning (vulnerabilities, secrets, XSS, SQL injection)
    - Performance detection (nested loops, memory leaks, blocking operations)
    - Repository health scoring and recommendations
- **Launch:** January 2026 as freeware for Linux community
- **Documentation:** [vibeforge/README.md](./vibeforge/README.md)

### 2. DataForge 🗄️ – Core Data Engine (COMMERCIAL)

- **Purpose:** Unified data storage, semantic retrieval, event auditing
- **Status:** 🔒 **Advanced Alpha** (18/18 phases complete)
- **Repository:** `./DataForge/`
- **License:** Commercial - All rights reserved
- **Key Features:**
  - **🔍 Hybrid Search** - Combines semantic (vector) + keyword (BM25) search with RRF
  - PostgreSQL with pgvector embeddings
  - Field-level AES-256 encryption
  - Immutable audit logs
  - 6-type anomaly detection
  - GDPR/CCPA/HIPAA compliance frameworks
  - Prometheus + OpenTelemetry observability
- **Role:** Shared intelligence layer for all Forge products
- **Documentation:** [DataForge/README.md](./DataForge/README.md)

### 3. NeuroForge 🧠 – AI Orchestration Engine (COMMERCIAL)

- **Purpose:** LLM routing, inference optimization, model management
- **Status:** 🔒 **Advanced Alpha**
- **Repository:** `./NeuroForge/`
- **License:** Commercial - All rights reserved
- **Key Features:**
  - Multi-provider LLM routing (Anthropic, OpenAI, Ollama)
  - Champion model selection system
  - Five-stage LLM pipeline (Retrieve → Prepare → Execute → Score → Return)
  - Domain-specific adapters
  - Circuit breakers and retry logic
  - Performance tracking and optimization
  - Context integration with DataForge
- **Role:** Centralized AI orchestration for all products
- **Documentation:** [NeuroForge/neuroforge_backend/README.md](./NeuroForge/neuroforge_backend/README.md)

### 4. ForgeAgents 🤖 – Autonomous Agent Orchestration (COMMERCIAL)

- **Purpose:** Orchestration layer enabling autonomous AI agents within the Forge Ecosystem
- **Status:** 🔒 **Advanced Alpha** - Phase 7 Complete (100%) ✅
- **Repository:** `./ForgeAgents/`
- **Version:** 0.1.0
- **License:** Commercial - All rights reserved
- **Production Code:** ~20,050 lines (Python)
- **Key Features:**
  - **Agent Lifecycle Management** - Plan → Act → Observe → Reflect → Decide → Next/Finish
  - **Multi-Provider LLM Integration** - OpenAI GPT-4 + Anthropic Claude 3 with automatic failover
  - **Tool System** - 23 tools across 4 adapters (Rake, NeuroForge, DataForge, Filesystem)
  - **Memory System** - Short-term (in-memory), Long-term (DataForge), Episodic (timeline)
  - **Policy Engine** - 11 production policies (Safety, Domain, Resource)
  - **Authentication** - JWT + RBAC with multi-tenancy support
  - **Monitoring** - 19 Prometheus metrics across all systems
  - **Testing** - 61 automated tests with coverage reporting
  - **Reference Agents (5 Production-Ready):**
    - AssistantAgent (Writer) - General-purpose task assistance (629 lines)
    - DeveloperAgent (Coder) - Code generation and refactoring (582 lines)
    - AnalystAgent (Analyst) - Data analysis and reporting (312 lines)
    - ResearchAgent (Researcher) - Information gathering (385 lines)
    - CoordinatorAgent (Orchestrator) - Multi-agent coordination (380 lines)
- **Service Integration:**
  - DataForge (8001) - Memory persistence, semantic search
  - NeuroForge (8000) - LLM inference and routing
  - Rake (8002) - Background job processing
  - Coordinates all services via unified API
- **Role:** Production-ready autonomous coordination across all ecosystem services
- **Port:** 8003
- **Documentation:** [ForgeAgents/README.md](./ForgeAgents/README.md)

### 5. AuthorForge ✍️ – AI Writing Platform (COMMERCIAL)

- **Purpose:** Genre-aware creative writing with narrative structuring
- **Status:** 🔒 **Alpha** - Active Development
- **Repository:** `./AuthorForge/`
- **License:** Commercial - All rights reserved
- **Key Features:**
  - Multi-genre writing framework (Fantasy, Sci-Fi, Christian Fiction)
  - Seven themed workspaces (Hearth, Foundry, Smithy, Anvil, Lore, Bloom, Tempering)
  - AI-powered research assistant
  - Character and scene management
  - Pacing and structure analysis
  - Full DataForge + NeuroForge integration
- **Role:** Professional writing suite for authors
- **Documentation:** [AuthorForge/README.md](./AuthorForge/README.md)

### 6. TradeForge 📈 – Market Intelligence (COMMERCIAL)

- **Purpose:** Market signals, historical feeds, financial datasets
- **Status:** 🔒 **Planned**
- **License:** Commercial - All rights reserved
- **Key Features:**
  - Real-time market data integration
  - Historical feed management
  - Structured financial datasets
  - Risk analysis and trading signals
  - Full DataForge + NeuroForge integration
- **Role:** Professional market intelligence for traders and analysts
- **Documentation:** Commercial module - details pending public release

### 7. Leopold & Livy 🌿📚 – Analysis Modules (COMMERCIAL)

- **Leopold:** Ecological observations, biological datasets, environmental tracking
- **Livy:** Historical data, geospatial narratives, temporal analysis
- **Status:** 🔒 **Planned**
- **License:** Commercial - All rights reserved
- **Role:** Specialized domain analysis tools
- **Documentation:** Commercial modules - details pending public release

### 8. Cortex 🔍 – Desktop File Intelligence (STANDALONE)

- **Purpose:** Fast, offline-first file indexing and intelligent search
- **Status:** ✅ **Alpha** (Phase 0: 82% complete)
- **Repository:** `./cortex/`
- **License:** TBD (standalone desktop application)
- **Key Features:**
  - **Lightning-fast search** - Sub-100ms FTS5 queries, 50+ files/sec indexing
  - **VS Code Claude Export** - Export indexed content for AI coding assistants
  - **Offline-first** - All data stored locally in SQLite
  - **Cross-platform** - Linux, macOS, Windows support via Tauri
  - **Content extraction** - txt, md, pdf, docx, source code
  - **Real-time progress** - Live indexing status with progress tracking
- **Technology:** Rust/Tauri 2.0 + SvelteKit
- **Role:** Personal search engine for developers, writers, researchers
- **Documentation:** [cortex/README.md](./cortex/README.md)

---

## 🏗️ System Architecture

### 5-Layer Forge Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         Application Layer (Client-Facing Products)          │
│  AuthorForge · VibeForge · TradeForge · Leopold · Livy     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│     ForgeAgents Orchestration Layer                          │
│  Autonomous Agents · Task Coordination · Cross-Service API  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│     API Gateway / Load Balancer Layer                        │
│  Authentication · Rate Limiting · Request Routing · TLS    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│     Core Services Layer                                      │
│  NeuroForge (AI) · DataForge (Data) · Rake (Ingestion)     │
└──────────┬──────────────────┬──────────────────┬────────────┘
           │                  │                  │
      ┌────▼─────┐    ┌──────▼──────┐    ┌─────▼──────┐
      │PostgreSQL│    │    Redis     │    │  RabbitMQ  │
      │+ pgvector│    │  (Cache)     │    │  (Queue)   │
      └──────────┘    └──────────────┘    └────────────┘

           │                  │                  │
     ┌─────▼──────────────────▼──────────────────▼─────┐
     │  Observability Layer                            │
     │  Prometheus · OpenTelemetry · Grafana · Alerts │
     └─────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Layered & Modular** – Clear separation of concerns
2. **Zero-Trust Security** – All traffic encrypted, mutual TLS, secrets rotation
3. **Compliance-First** – GDPR, CCPA, HIPAA, SOC2, PCI-DSS automation built-in
4. **Cloud-Agnostic** – Deploy on AWS, GCP, Azure, or on-premises
5. **Observable & Transparent** – Every action logged, traced, and alerted

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.11+
- **PostgreSQL** 13+ (with pgvector extension)
- **Redis** 6+ (caching and sessions)
- **RabbitMQ** 3.8+ (async task processing)
- **Docker** 24+ (for containerized deployment)
- **Linux/macOS/WSL2** (Windows native not supported)

### Quick Start with DataForge (Core Engine)

```bash
# Clone DataForge
git clone https://github.com/Boswecw/DataForge.git
cd DataForge

# Setup environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Verify installation
curl http://localhost:8000/health
open http://localhost:8000/docs
```

### Deployment Options

| Option                     | Setup Time | Nodes | SLA    | Best For                  |
| -------------------------- | ---------- | ----- | ------ | ------------------------- |
| **Development**            | 15 min     | 1     | -      | Local testing             |
| **Single-Node Production** | 30 min     | 1     | 99.0%  | Small-scale production    |
| **Multi-Node Production**  | 2 hours    | 3+    | 99.99% | Enterprise deployments    |
| **Kubernetes**             | 1–2 hours  | 3+    | 99.99% | Cloud-native environments |

**Full deployment guide:** [DataForge/docs/guides/DEPLOYMENT_GUIDE.md](./DataForge/docs/guides/DEPLOYMENT_GUIDE.md)

---

## 🗄️ DataForge: Core Engine

DataForge is the **unified data and knowledge engine** powering all Forge products.

### Core Capabilities

- **Hybrid search** – Combines semantic (vector) + keyword (BM25) search with Reciprocal Rank Fusion (+40% accuracy)
- **High-availability data storage** – 99.99% uptime SLA with automatic failover
- **Semantic retrieval** – pgvector embeddings for intelligent similarity search
- **Event auditing** – Immutable, cryptographically-signed logs with 90+ day retention
- **Field-level encryption** – AES-256 for sensitive data with automatic key rotation
- **Anomaly detection** – 6 detector types (impossible travel, brute force, data exfiltration, suspicious patterns, after-hours, bulk mutations)
- **Compliance automation** – GDPR, CCPA, HIPAA, SOC2, PCI-DSS ready
- **Production observability** – Prometheus metrics, OpenTelemetry tracing, Grafana dashboards, 24/7 alerting

### DataForge Status

| Metric              | Value                  |
| ------------------- | ---------------------- |
| **Completion**      | 18/18 phases (100%) ✅ |
| **Tests Passing**   | 296/296 (100%) ✅      |
| **Production Code** | 28,257 lines           |
| **Documentation**   | 5,742+ lines           |
| **RAG Features**    | Hybrid Search ✅       |
| **Version**         | 5.2                    |
| **SLA Target**      | 99.99% (multi-node)    |

### Documentation

- 📖 **README:** [DataForge/README.md](./DataForge/README.md)
- 📋 **API Reference:** [DataForge/docs/guides/API_REFERENCE.md](./DataForge/docs/guides/API_REFERENCE.md)
- 🛠️ **Deployment:** [DataForge/docs/guides/DEPLOYMENT_GUIDE.md](./DataForge/docs/guides/DEPLOYMENT_GUIDE.md)
- 📚 **Operations:** [DataForge/docs/guides/OPERATIONS_RUNBOOK.md](./DataForge/docs/guides/OPERATIONS_RUNBOOK.md)
- 🔒 **Security:** [DataForge/SECURITY.md](./DataForge/SECURITY.md)
- 🏛️ **Architecture:** [DataForge/ARCHITECTURE.md](./DataForge/ARCHITECTURE.md)

---

## 📊 Project Status

### Product Status Summary

| Product      | Status           | Tests | Notes                        |
| ------------ | ---------------- | ----- | ---------------------------- |
| DataForge    | Advanced Alpha ✅ | 296   | v5.2, 18/18 phases complete  |
| NeuroForge   | Advanced Alpha ✅ | 100+  | 89% coverage                 |
| Rake         | Production ✅     | 77    | v1.0, 80%+ coverage          |
| ForgeAgents  | Advanced Alpha ✅ | 61    | v0.1.0, Phase 7 complete     |
| VibeForge    | Beta ✅           | 695   | v5.6, Jan 2026 launch        |
| Cortex       | Alpha            | 60    | Phase 0: 82% complete        |
| AuthorForge  | Alpha            | —     | SolidStart boilerplate       |
| TradeForge   | Planned          | —     | —                            |
| Leopold/Livy | Planned          | —     | —                            |

### Development Roadmap

**Tier 1: Foundation (Complete)**
- ✅ DataForge – Memory substrate for everything
- ✅ NeuroForge – Inference engine with pipeline

**Tier 2: Pipeline (Complete)**
- ✅ Rake – Ingestion pipeline feeding DataForge
- ✅ VibeForge – January 2026 launch product

**Tier 3: Local Applications (In Progress)**
- 🔄 Cortex – Local file management bridge (82%)
- 🔄 AuthorForge – Writing OS (started)

**Tier 4: Orchestration (Complete)**
- ✅ ForgeAgents – Autonomous agent coordination (Phase 7: 100%)

**Tier 5: Future Products**
- 📋 TradeForge – Stock analysis
- 📋 Leopold – Wildlife biology
- 📋 Livy – Historical tours

### Key Milestones

| Timeline      | Milestone           | Deliverable                      |
| ------------- | ------------------- | -------------------------------- |
| December 2025 | ForgeAgents v0.1.0  | Phase 7 complete, production-ready ✅ |
| January 2026  | VibeForge Launch    | Freeware for Linux community     |
| Q2 2026       | AuthorForge Beta    | MVP with core workspaces         |
| Q3 2026       | ForgeAgents v1.0    | Enhanced features, scale-up      |
| 2027          | Revenue Target      | 500+ users, $50K+ revenue        |

### Feature Coverage

**Security & Compliance:**

- ✅ OAuth2 / OIDC authentication
- ✅ Multi-factor authentication (TOTP + backup codes)
- ✅ Field-level AES-256 encryption
- ✅ Immutable audit logs
- ✅ 6-type anomaly detection
- ✅ GDPR, CCPA, HIPAA, SOC2, PCI-DSS compliance frameworks

**High Availability:**

- ✅ Multi-node replication with automatic failover
- ✅ Redis Sentinel for cache failover
- ✅ RabbitMQ mirroring for queue reliability
- ✅ Circuit breakers and retry mechanisms
- ✅ Automated backups (hourly/daily/weekly/monthly)
- ✅ Point-in-time recovery capability
- ✅ 99.99% SLA for multi-node deployments

**Observability:**

- ✅ Prometheus metrics (40+ application metrics)
- ✅ OpenTelemetry distributed tracing
- ✅ Structured JSON logging with correlation IDs
- ✅ Grafana pre-built dashboards
- ✅ Real-time alerting (Slack, PagerDuty, email)

---

## 📚 Documentation

### Master Index

**Complete Documentation Index:** [CONSOLIDATED_DOCUMENTATION_INDEX.md](./CONSOLIDATED_DOCUMENTATION_INDEX.md)

### DataForge Documentation Suite

| Document                         | Purpose               | Lines |
| -------------------------------- | --------------------- | ----- |
| README.md                        | Enterprise overview   | 562   |
| COMPREHENSIVE_DOCUMENTATION.md   | Complete architecture | 1,158 |
| API_REFERENCE.md                 | 24 API endpoints      | 884   |
| DEPLOYMENT_GUIDE.md              | Deployment procedures | 729   |
| OPERATIONS_RUNBOOK.md            | Daily operations      | 686   |
| TROUBLESHOOTING_GUIDE.md         | Problem diagnostics   | 752   |
| SECURITY.md                      | Security architecture | 117   |
| ARCHITECTURE.md                  | System design         | 164   |
| **Total**                        | **All guides**        | **5,742** |

### VibeForge Documentation Suite

| Document                           | Purpose                      | Lines |
| ---------------------------------- | ---------------------------- | ----- |
| PHASE_3_2_COMPLETION_SUMMARY.md    | Backend integration summary  | 450   |
| PHASE_3_3_COMPLETION_SUMMARY.md    | Frontend integration summary | 580   |
| TECHNICAL_DUE_DILIGENCE_REVIEW.md  | Quality assessment           | 620   |
| TECHNICAL_ISSUES_RESOLVED.md       | Issue resolution log         | 463   |
| VIBEFORGE_ROADMAP.md               | Product roadmap              | 1,200 |
| **Total**                          | **Phase 3 docs**             | **3,313** |

### Directory Structure

```
Forge/
├── DataForge/                          # Core data engine (18 phases complete)
│   ├── README.md                       # DataForge overview
│   ├── LICENSE.md, LEGAL.md            # Commercial licensing
│   ├── SECURITY.md, ARCHITECTURE.md    # Technical documentation
│   ├── docs/
│   │   ├── setup/                      # Installation & setup guides
│   │   ├── guides/                     # Comprehensive operational guides
│   │   ├── references/                 # Technical references
│   │   └── archive/                    # Historical documentation
│   └── app/                            # Python application code
│
├── NeuroForge/                         # AI orchestration engine
│   └── neuroforge_backend/
│
├── ForgeAgents/                        # Autonomous agent orchestration (v0.1.0, Phase 7 complete)
│   ├── README.md                       # Complete overview (960+ lines)
│   ├── PHASE_7_COMPLETE.md             # Phase 7 summary
│   ├── docs/phases/                    # Phase completion reports (2-7)
│   ├── docs/ARCHITECTURE.md            # System architecture
│   ├── docs/API.md                     # API reference
│   └── app/                            # Python application code
│
├── AuthorForge/                        # AI writing platform
│   └── README.md
│
├── vibeforge/                          # Prompt engineering workbench
│   └── README.md
│
├── cortex/                             # Desktop file intelligence
│   └── README.md
│
├── CONSOLIDATED_DOCUMENTATION_INDEX.md # Master documentation index
└── README.md                           # This file
```

---

## 🧪 Technology Stack

### Core Technologies

| Layer                 | Technology    | Version | Purpose                   |
| --------------------- | ------------- | ------- | ------------------------- |
| **Language**          | Python        | 3.11+   | Backend application       |
| **Web Framework**     | FastAPI       | 0.104+  | REST API and routing      |
| **ORM**               | SQLAlchemy    | 2.0+    | Database abstraction      |
| **Database**          | PostgreSQL    | 13+     | Primary datastore         |
| **Vector Search**     | pgvector      | 0.5+    | Embeddings storage        |
| **Cache**             | Redis         | 6+      | Session & cache layer     |
| **Queue**             | RabbitMQ      | 3.8+    | Async message broker      |
| **Task Worker**       | Celery        | 5.3+    | Background job processing |
| **Metrics**           | Prometheus    | 2.48+   | Performance monitoring    |
| **Tracing**           | OpenTelemetry | 1.21+   | Distributed tracing       |
| **Dashboards**        | Grafana       | 10.2+   | Visualization & alerts    |
| **Orchestration**     | Kubernetes    | 1.28+   | Container orchestration   |
| **Container Runtime** | Docker        | 24+     | Containerization          |
| **Testing**           | pytest        | 7.4+    | Unit & integration tests  |

### Frontend Technologies

| Layer       | Technology | Purpose                  |
| ----------- | ---------- | ------------------------ |
| **Web**     | SvelteKit  | VibeForge frontend       |
| **Desktop** | Tauri      | Cross-platform apps      |
| **Alt Web** | SolidJS    | AuthorForge frontend     |
| **Styling** | Tailwind   | Utility-first CSS        |

### Port Assignments

| Service     | Port | Status           |
| ----------- | ---- | ---------------- |
| NeuroForge  | 8000 | Advanced Alpha   |
| DataForge   | 8001 | Advanced Alpha   |
| Rake        | 8002 | Production Ready |
| ForgeAgents | 8003 | Advanced Alpha   |

---

## 🔒 Security & Compliance

### Enterprise Security Features

**Authentication & Authorization:**

- OAuth2 / OIDC integration for enterprise identity
- Multi-factor authentication (TOTP + backup codes)
- Device tracking and session management
- Role-based access control (RBAC)
- Resource-level permission enforcement

**Data Protection:**

- AES-256 encryption at rest (field-level)
- TLS 1.3 for all in-transit communication
- Automatic key rotation
- Certificate pinning for external APIs
- Secure secret storage (HashiCorp Vault / AWS KMS compatible)

**Audit & Compliance:**

- Immutable, cryptographically-signed event logs
- HMAC-SHA256 signatures on all audit records
- 90+ day event retention
- Real-time anomaly detection (6 detector types)
- Compliance reports (GDPR, CCPA, HIPAA, SOC2, PCI-DSS)

**Infrastructure Security:**

- Zero-trust architecture with network segmentation
- Rate limiting on all public endpoints
- Fail2Ban integration for brute-force protection
- Automated vulnerability scanning
- Supply chain integrity (pinned dependencies)

**See Also:**

- 🔐 [DataForge/SECURITY.md](./DataForge/SECURITY.md) – Complete security documentation
- ⚖️ [DataForge/LICENSE.md](./DataForge/LICENSE.md) – Commercial licensing terms
- 📋 [DataForge/LEGAL.md](./DataForge/LEGAL.md) – IP protections and legal framework

---

## 📋 License & Copyright

### Commercial Products (DataForge, NeuroForge, ForgeAgents, AuthorForge, TradeForge, Leopold, Livy)

**📄 License (Commercial)**

These products are commercial, closed-source applications owned and licensed by **Boswell Digital Solutions LLC (BDS)**.

**You may not:**

- Redistribute, resell, sublicense, or publish the source code
- Modify, reverse engineer, decompile, or derive competing products
- Host as a service or provide multi-tenant access
- Train AI models on the code, datasets, workflows, or documentation
- Bundle this software into third-party products

**All rights reserved © 2025 Boswell Digital Solutions LLC.**  
Commercial licensing inquiries: charlesboswell@boswelldigitalsolutions.com

### VibeForge (Freeware Entry Product)

**📄 License (Freeware With Restrictions)**

VibeForge is released as **freeware** by Boswell Digital Solutions LLC.

**You may:**

- Download and use the official unmodified binaries for free
- Redistribute the exact binaries
- Use the software for personal, academic, or commercial development

**You may not:**

- Modify, decompile, reverse engineer, or extract code
- Redistribute modified versions
- Bundle VibeForge into SaaS or commercial tools
- Use its design or workflow to create competing products
- Train AI models on VibeForge's UI, workflows, or logic

**Note:** All backend orchestration (NeuroForge) and data engines (DataForge) remain commercial.

**© 2025 Boswell Digital Solutions LLC — All Rights Reserved.**

### Intellectual Property

All code, documentation, schemas, diagrams, algorithms, and business logic across the entire Forge Ecosystem are protected intellectual property of Boswell Digital Solutions LLC. See [DataForge/LEGAL.md](./DataForge/LEGAL.md) for comprehensive IP protections.

---

## 📞 Support & Contact

### Enterprise Support

- **Technical Support:** charlesboswell@boswelldigitalsolutions.com
- **Licensing & Sales:** Same email
- **Security Issues:** Report with [SECURITY] prefix in subject
- **Documentation Issues:** Submit via GitHub (private repo)

### Resources

- 📖 **DataForge Documentation** – [./DataForge/README.md](./DataForge/README.md)
- 🗺️ **Full Documentation Index** – [CONSOLIDATED_DOCUMENTATION_INDEX.md](./CONSOLIDATED_DOCUMENTATION_INDEX.md)
- 🐛 **Known Issues & Solutions** – [DataForge/docs/guides/TROUBLESHOOTING_GUIDE.md](./DataForge/docs/guides/TROUBLESHOOTING_GUIDE.md)
- 📊 **Architecture Overview** – [DataForge/ARCHITECTURE.md](./DataForge/ARCHITECTURE.md)
- 🔒 **Security Policy** – [DataForge/SECURITY.md](./DataForge/SECURITY.md)

---

## 🎯 Summary

**The Forge Ecosystem** is a professional development platform comprising eight specialized AI products with unified backend architecture. The platform features VibeForge as a freeware entry product, supported by commercial backend services (DataForge + NeuroForge), autonomous orchestration (ForgeAgents), and professional domain tools (AuthorForge, TradeForge, Leopold, Livy), plus the standalone Cortex desktop application.

### Key Achievements

✅ **8 Specialized Products** – Unified architecture with commercial backend
✅ **VibeForge (Freeware)** – Free entry product launching January 2026
✅ **DataForge Engine** – Advanced Alpha with 18/18 core phases complete
✅ **NeuroForge Orchestration** – Advanced Alpha with multi-provider LLM routing
✅ **ForgeAgents (NEW)** – Production-ready autonomous agent orchestration (Phase 7: 100%)
✅ **Enterprise Security** – OAuth2, JWT, field-level encryption, audit logs, anomaly detection
✅ **Full Compliance** – GDPR, CCPA, HIPAA frameworks with automation
✅ **Complete Documentation** – 12,300+ lines across 20+ guides
✅ **Production Observability** – Prometheus, OpenTelemetry, Grafana monitoring

### Development Stage

| Product        | Stage          | Notes                              |
| -------------- | -------------- | ---------------------------------- |
| DataForge      | Advanced Alpha | Maturing core engine               |
| NeuroForge     | Advanced Alpha | Production-grade orchestration     |
| Rake           | Production     | v1.0 complete                      |
| ForgeAgents    | Advanced Alpha | v0.1.0, Phase 7 complete, production-ready |
| VibeForge      | Beta           | January 2026 freeware launch       |
| Cortex         | Alpha          | Phase 0: 82% complete              |
| AuthorForge    | Alpha          | Active development                 |
| TradeForge     | Planned        | —                                  |
| Leopold/Livy   | Planned        | —                                  |

---

**Maintained by:** Boswell Digital Solutions LLC  
**Ecosystem Version:** 5.3  
**Last Updated:** December 5, 2025

**For questions, licensing, or support, contact:** charlesboswell@boswelldigitalsolutions.com
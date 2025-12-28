<p align="center">
  <img src="https://firebasestorage.googleapis.com/v0/b/endless-fire-467204-n2.firebasestorage.app/o/Forge%2FDataForge_icon.avif?alt=media&token=1e81b1bd-9cf2-4e56-9f3a-e9aa14b9cd0a"
       alt="DataForge Logo"
       width="180"
       style="border-radius: 12px;" />
</p>

<h1 align="center">DataForge</h1>
<h3 align="center">Core Data & Knowledge Engine</h3>
<h4 align="center">Unified intelligence layer for the Forge Ecosystem</h4>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen" />
  <img src="https://img.shields.io/badge/License-Commercial-red" />
  <img src="https://img.shields.io/badge/Tests-296%20Passing-brightgreen" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" />
  <img src="https://img.shields.io/badge/Version-5.2-blue" />
  <img src="https://img.shields.io/badge/Core%20Phases-18/18-brightgreen" />
  <img src="https://img.shields.io/badge/Coverage-82%25-green" />
</p>

---

> **📄 License (Commercial)**  
> This product is commercial, closed-source software owned by **Boswell Digital Solutions LLC (BDS)**.  
> You may not redistribute, modify, reverse engineer, or use in derivative products.  
> All rights reserved © 2025 Boswell Digital Solutions LLC.  
> See [LICENSE.md](./LICENSE.md) and [LEGAL.md](./LEGAL.md) for complete terms.

---

## 📘 Table of Contents

1. [Overview](#-overview)
2. [Ecosystem Integration](#-ecosystem-integration)
3. [Ecosystem Role](#-ecosystem-role)
4. [Key Features](#-key-features)
5. [System Architecture](#%EF%B8%8F-system-architecture)
6. [Quick Start](#-quick-start)
7. [API Quick Reference](#-api-quick-reference)
8. [Technology Stack](#-technology-stack)
9. [Project Phases](#-project-phases)
10. [Deployment](#-deployment)
11. [Performance & Scaling](#-performance--scaling)
12. [Documentation](#-documentation)
13. [Troubleshooting](#-troubleshooting)
14. [Security & Compliance](#-security--compliance)
15. [Development Workflow](#-development-workflow)
16. [Support](#-support)

---

## 📘 Overview

**DataForge** is the central data and knowledge engine powering the entire **Forge Ecosystem**. As **production-ready infrastructure**, it serves as the shared memory layer and single source of truth for all Forge products: VibeForge (freeware), NeuroForge, AuthorForge, TradeForge, and specialized analysis modules.

Built with enterprise security, high availability, and compliance as first-class requirements, DataForge provides the persistent storage layer that enables stateless, horizontally-scalable applications across the Forge suite.

### Core Capabilities

- **🎯 Unified Intelligence Layer** – Single source of truth for all Forge products
- **🔍 Hybrid Search (NEW)** – Combines semantic (vector) + keyword (BM25) search using Reciprocal Rank Fusion for +40% better accuracy
- **🧠 Semantic Retrieval** – pgvector embeddings for context-aware search and RAG pipelines
- **🤖 AI Planning Learning** – Multi-AI orchestration with continuous learning and model performance tracking
- **📝 Event Auditing** – Immutable, cryptographically signed logs with 90+ day retention
- **🔐 Field-Level Encryption** – AES-256 encryption for sensitive data with automatic key rotation
- **🚨 Anomaly Detection** – 6 detector types (impossible travel, brute force, data exfiltration, suspicious patterns, after-hours access, bulk mutations)
- **⚖️ Compliance Frameworks** – GDPR, CCPA, HIPAA, SOC2, PCI-DSS automation with extensible policy engine
- **📊 Production Observability** – Prometheus metrics, OpenTelemetry tracing, Grafana dashboards
- **🚀 High Availability** – Multi-node replication, automatic failover, 99.99% SLA
- **⚡ Performance** – Sub-100ms API latency, 1,000+ RPS sustained throughput

### Project Status at a Glance

| Metric                  | Value                         |
| ----------------------- | ----------------------------- |
| **Development Stage**   | **Production Ready** ✅       |
| **Core Phases**         | 18/18 complete (100%) ✅      |
| **Tests Passing**       | 296/296 (100%) ✅             |
| **Test Coverage**       | 82% (critical paths)          |
| **Production Code**     | 28,257+ lines                 |
| **Total Documentation** | 7,242+ lines                  |
| **Current Version**     | 5.2                           |
| **API Endpoints**       | 24 REST endpoints             |
| **Commercial License**  | ✅ [LICENSE.md](./LICENSE.md) |
| **IP Protection**       | ✅ [LEGAL.md](./LEGAL.md)     |
| **Uptime SLA**          | 99.99% (multi-node)           |

---

## 🌐 Ecosystem Integration

**DataForge is part of the complete Forge Ecosystem (as of December 19, 2025):**

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **DataForge** | 8001 | ✅ HEALTHY | Vector search & embeddings (this service) |
| **NeuroForge** | 8000 | ✅ HEALTHY | Multi-model AI routing (5 models) |
| **ForgeAgents** | 8787 | ✅ HEALTHY | AI agents & EcosystemAgent (35 tools) |
| **Rake** | 8002 | ✅ HEALTHY | Data ingestion pipeline |
| **Forge Command** | 1420 | ✅ HEALTHY | Mission control dashboard |
| **VibeForge_BDS** | - | ✅ HEALTHY | AI prompt engineering workbench (Tauri) |
| **Cortex BDS** | - | ✅ HEALTHY | AI-powered semantic file search |
| **PostgreSQL** | 5432 | ✅ HEALTHY | Shared telemetry database |
| **Redis** | 6379 | ✅ HEALTHY | Distributed cache & sessions |

**System Grade:** A (100% functional) - All services operational

**Note:** Forge Command now routes all ecosystem operations through ForgeAgents EcosystemAgent (`POST /api/v1/tasks/ecosystem`) instead of connecting to services directly.

### Quick Links to Ecosystem Documentation

- **[Quick Start Guide](../QUICK_START_GUIDE.md)** - Complete API reference & get all services running
- **[Next Steps & Roadmap](../NEXT_STEPS.md)** - Production deployment guide
- **[Quick Reference](../QUICK_REFERENCE.md)** - Command cheatsheet for all services
- **[Ecosystem Architecture](../docs/architecture/FORGE_UNIFIED_ARCHITECTURE.md)** - Complete system design
- **[Latest Session Report](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)** - Dec 11 bug fixes (100% operational)
- **[Organized Documentation](../docs/README.md)** - Complete documentation index

---

## 🔗 Ecosystem Role

DataForge acts as the **shared intelligence layer** for the Forge Suite of products:

| Product         | Port | Role                                                                                          | Integration Status |
| --------------- | ---- | --------------------------------------------------------------------------------------------- | ------------------ |
| **NeuroForge**  | 8000 | Model routing, embeddings generation, context retrieval, inference tracking                   | ✅ Complete        |
| **VibeForge**   | -    | Project creation wizard, code analysis, GitHub integration, stack analytics, language tracking | ✅ Complete        |
| **AuthorForge** | -    | Writing knowledge, narrative structures, pacing, genre-level analysis                         | 🚧 Planned         |
| **TradeForge**  | -    | Market signals, historical feeds, structured financial datasets                               | 🚧 Planned         |
| **Leopold**     | -    | Ecological observations, biological datasets, environmental tracking                          | 🚧 Planned         |
| **Livy**        | -    | Historical data, geospatial narratives, temporal analysis                                     | 🚧 Planned         |

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Forge Products (Clients)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  NeuroForge (Port 8000)     VibeForge Tauri App            │
│  • LLM execution logs        • Project sessions             │
│  • Context retrieval         • Stack outcomes               │
│  • Model performance         • Language preferences         │
│                                                              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST API
                         │ JWT Authentication
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  DataForge (Port 8001)                       │
│                  Single Source of Truth                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Runs API    │  │VibeForge API │  │  Search API  │     │
│  │ (NeuroForge) │  │  (Projects)  │  │   (Vector)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          PostgreSQL + pgvector + Redis                       │
│          Persistent Storage Layer                            │
└─────────────────────────────────────────────────────────────┘
```

### Current Integrations

**NeuroForge → DataForge:**

- Logs all LLM execution runs (`/api/v1/runs`)
- Stores prompt/chain/deployment data
- Retrieves context from knowledge base
- Tracks model performance metrics

**VibeForge → DataForge:**

- Saves project creation sessions (`/api/vibeforge/projects`)
- Tracks wizard interaction patterns
- Records stack outcomes (success/failure)
- Analyzes language preferences
- Monitors build/test/deploy results
- Stores code analysis results and quality metrics
- Caches GitHub repository metadata and file contents

### Benefits of Shared Intelligence Layer

Every Forge product consumes DataForge as the **source of truth**, ensuring:

- ✅ **Consistency** – All products see the same data
- ✅ **Stateless Applications** – Products can scale horizontally
- ✅ **Enterprise Compliance** – Unified audit trails and encryption
- ✅ **Cross-Product Analytics** – Insights across the entire ecosystem
- ✅ **Unified Security** – Single authentication and authorization layer
- ✅ **Data Persistence** – Survives application restarts
- ✅ **Shared Context** – Products can leverage each other's data

---

## ✨ Key Features

### 🔐 Security & Compliance

- **OAuth2 + OIDC** – Enterprise identity provider integration
- **Multi-factor authentication** – TOTP, backup codes, device tracking, SSO
- **Field-level encryption** – AES-256 encryption at rest with transparent decryption
- **Immutable audit logs** – HMAC-SHA256-signed events with 90+ day retention
- **Automatic key rotation** – Secrets and certificate rotation without downtime
- **6-type anomaly detection** – Impossible travel, brute force, bulk extraction, suspicious patterns, after-hours, mutations
- **Full compliance frameworks** – GDPR, CCPA, HIPAA, SOC2 Type II, PCI-DSS
- **Zero-trust architecture** – Certificate pinning, rate limiting, Fail2Ban, segmented networks

### 📦 Data Management

- **PostgreSQL 13+** – Battle-tested relational database
- **pgvector extension** – Vector embeddings with similarity search
- **Field-level encryption** – Transparent AES-256 for sensitive columns
- **Automated migrations** – Alembic-managed schema evolution with zero-downtime
- **Row-level access control** – Fine-grained permission enforcement at DB layer
- **Connection pooling** – PgBouncer for optimal resource utilization

### 🧠 Semantic Capabilities

#### New Hybrid Search (Dec 2025) 🔍

DataForge now includes production-ready hybrid search combining:
- **Semantic Search**: Vector similarity (pgvector) for contextual matching
- **Keyword Search**: PostgreSQL full-text search with BM25-style ranking
- **Hybrid Search**: Reciprocal Rank Fusion combining both methods (+40% accuracy)

**API Endpoints:**
- `POST /api/search/semantic` - Pure vector search
- `POST /api/search/keyword` - Pure BM25 keyword search (requires PostgreSQL)
- `POST /api/search/hybrid` - Hybrid search (default, recommended)

**Performance:**
- Semantic search: 20-50ms
- Keyword search: 10-30ms
- Hybrid search: 30-80ms (combined)

**See:** [RAG_PIPELINE_REFACTORING_COMPLETE.md](../RAG_PIPELINE_REFACTORING_COMPLETE.md) for technical details.

#### Core Semantic Features

- **Vector embeddings** – OpenAI, Anthropic, or local model support
- **Similarity search** – Fast cosine/L2 distance queries over embeddings
- **Context retrieval** – Intelligent chunk selection for RAG pipelines
- **Knowledge base queries** – Natural language QA over documents
- **Semantic caching** – Redis-backed deduplication for repeated queries
- **Embedding versioning** – Track embedding model changes over time

### 🤖 Multi-AI Planning Learning Layer

- **Planning outcome tracking** – Complete session records with stage-by-stage metrics
- **Model performance analytics** – EMA-based continuous learning for optimal model selection
- **Time estimation feedback** – AI execution time predictions that improve with usage
- **Multi-stage orchestration** – 4-stage ChatGPT ↔ Claude planning workflows
- **Recommendation engine** – Data-driven model selections based on historical success
- **Feedback loops** – User ratings, execution results, and plan modifications recorded
- **Confidence scoring** – Sample-size weighted recommendations (1.0 at 10+ samples)
- **Task complexity analysis** – Simple/medium/complex categorization with tailored estimates

### 🚀 High Availability & Reliability

- **Multi-node replication** – Streaming replication with automatic failover
- **Redis Sentinel** – Automatic cache cluster failover
- **RabbitMQ mirroring** – High-availability message broker
- **Circuit breakers** – Graceful degradation under load
- **Automatic retries** – Exponential backoff with jitter
- **Dead-letter queues** – Failed job recovery and debugging
- **99.99% SLA** – Multi-node deployments with geo-redundancy
- **Automated backups** – Hourly, daily, weekly, monthly snapshots
- **Point-in-time recovery** – Restore to any point in the last 90 days

### 📊 Observability & Operations

- **Prometheus metrics** – 40+ application-level metrics
- **OpenTelemetry tracing** – Distributed traces for all HTTP requests and database operations
- **Structured logging** – JSON logs with correlation IDs and trace context
- **Grafana dashboards** – Pre-built dashboards for performance, security, business metrics
- **Real-time alerting** – Slack, PagerDuty, email, webhook integrations
- **Alert automation** – 12+ alert categories with intelligent thresholding
- **SLO tracking** – Built-in SLA calculations and reporting
- **Incident playbooks** – Automated runbook procedures for common issues

### ⚙️ Async Processing

- **Celery task queue** – Background jobs for heavy computations, exports, notifications
- **RabbitMQ integration** – Reliable message delivery with persistent queues
- **Job scheduling** – Periodic tasks (health checks, cache warming, log rotation)
- **Progress tracking** – Real-time job status and result retrieval
- **Task prioritization** – Multiple queues for different workload types

### 🔄 Kubernetes & Cloud-Native

- **Kubernetes-native** – Full Helm charts and manifests
- **Liveness/readiness probes** – Automatic pod health checking
- **Horizontal pod autoscaling** – Scale based on CPU/memory/custom metrics
- **StatefulSet support** – Persistent volumes for database/cache layers
- **Ingress integration** – Nginx/HAProxy compatible routing
- **ConfigMap/Secret management** – Environment-safe secrets handling
- **Resource limits & requests** – Proper QoS configuration

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│         Client Layer                            │
│  AuthorForge · NeuroForge · VibeForge · Apps   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│     API Gateway / Load Balancer                 │
│  Routing · Rate Limiting · TLS Termination     │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│     Application Layer (FastAPI)                 │
│  ┌────────────────────────────────────────┐    │
│  │  Authentication & Authorization        │    │
│  │  Business Logic & Validation           │    │
│  │  Event Audit & Compliance              │    │
│  │  Anomaly Detection & Rate Limiting     │    │
│  └────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────┘
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼─────┐  ┌────▼────┐  ┌─────▼───────┐
│ PostgreSQL  │  │  Redis   │  │  RabbitMQ   │
│ + pgvector  │  │ (Cache & │  │  (Queue)    │
│ (Primary)   │  │ Sessions)│  │             │
└─────────────┘  └──────────┘  └─────────────┘

      ▼               ▼               ▼
  ┌─────────────────────────────────────┐
  │  Observability Layer                │
  │  Prometheus · OpenTelemetry         │
  │  Grafana · Alertmanager             │
  └─────────────────────────────────────┘
```

**5-Layer Architecture:**

1. **Client Layer** – Forge products and external applications
2. **Gateway Layer** – Load balancing, rate limiting, TLS
3. **Application Layer** – FastAPI services, business logic, validation
4. **Data Layer** – PostgreSQL (primary), Redis (cache), RabbitMQ (queue)
5. **Observability Layer** – Prometheus, OpenTelemetry, alerting

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+
- **PostgreSQL** 13+ (with `pgvector` extension)
- **Redis** 6+ (for caching and sessions)
- **RabbitMQ** 3.8+ (optional, for async tasks)
- **Linux/macOS/WSL2** (Windows native not supported)

### Installation (Development)

```bash
# 1. Clone the repository
cd /path/to/Forge/DataForge

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# 5. Setup PostgreSQL with pgvector
sudo apt-get install postgresql-13 postgresql-contrib
sudo -u postgres psql -c "CREATE DATABASE dataforge;"
sudo -u postgres psql -d dataforge -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 6. Run database migrations
alembic upgrade head

# 7. Start Redis (if not already running)
redis-server

# 8. Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Verify Installation

```bash
# Health check
curl http://localhost:8001/health

# Expected response:
{
  "status": "healthy",
  "version": "5.2",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-11-23T..."
}

# Interactive API docs
open http://localhost:8001/docs

# ReDoc documentation
open http://localhost:8001/redoc

# Prometheus metrics
curl http://localhost:8001/metrics
```

### Running with Other Forge Products

DataForge is typically used as a dependency for other Forge products:

**Terminal 1: DataForge**

```bash
cd DataForge
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Terminal 2: NeuroForge (example)**

```bash
cd NeuroForge/neuroforge_backend
source .venv/bin/activate
# Set DATAFORGE_BASE_URL=http://localhost:8001 in .env
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Configuration

Create `.env` in the DataForge root directory:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dataforge

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ (optional)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Security
SECRET_KEY=your-secret-key-here  # Use strong random key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key  # For field-level encryption

# API Keys (for integrations)
OPENAI_API_KEY=sk-...  # For embeddings
ANTHROPIC_API_KEY=sk-ant-...  # Alternative embeddings

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development  # development, staging, production
API_VERSION=v1
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Observability
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=false  # Set true for distributed tracing
```

### Next Steps

- **Read the full setup guide:** [docs/setup/SETUP.md](./docs/setup/SETUP.md)
- **Deploy to production:** [docs/guides/DEPLOYMENT_GUIDE.md](./docs/guides/DEPLOYMENT_GUIDE.md)
- **Explore the API:** [docs/guides/API_REFERENCE.md](./docs/guides/API_REFERENCE.md)
- **Run operational tasks:** [docs/guides/OPERATIONS_RUNBOOK.md](./docs/guides/OPERATIONS_RUNBOOK.md)
- **Load testing:** [docs/guides/LOAD_TESTING_GUIDE.md](./docs/guides/LOAD_TESTING_GUIDE.md)

---

## 📑 Project Phases

All **18 phases completed (100%)**:

| Phase   | Focus Area              | Status      |
| ------- | ----------------------- | ----------- |
| **0**   | Automated Backups       | ✅ Complete |
| **1**   | Operational Excellence  | ✅ Complete |
| **2**   | Fault Tolerance         | ✅ Complete |
| **3**   | High Availability       | ✅ Complete |
| **4**   | Security Hardening      | ✅ Complete |
| **5**   | Documentation & Testing | ✅ Complete |
| **5.1** | Final Deployment Polish | ✅ Complete |

---

## 🧪 Technology Stack

| Layer                       | Technology    | Version | Purpose                  |
| --------------------------- | ------------- | ------- | ------------------------ |
| **Language**                | Python        | 3.11+   | Core application         |
| **Web Framework**           | FastAPI       | 0.104+  | API and routing          |
| **ORM**                     | SQLAlchemy    | 2.0+    | Database abstraction     |
| **Migration**               | Alembic       | 1.13+   | Schema management        |
| **Primary Database**        | PostgreSQL    | 13+     | Main datastore           |
| **Vector Search**           | pgvector      | 0.5+    | Embeddings storage       |
| **Cache & Sessions**        | Redis         | 6+      | High-speed data access   |
| **Message Queue**           | RabbitMQ      | 3.8+    | Async task processing    |
| **Task Worker**             | Celery        | 5.3+    | Background jobs          |
| **Metrics**                 | Prometheus    | 2.48+   | Performance monitoring   |
| **Tracing**                 | OpenTelemetry | 1.21+   | Distributed tracing      |
| **Dashboards**              | Grafana       | 10.2+   | Visualization            |
| **Container Orchestration** | Kubernetes    | 1.28+   | Deployment (optional)    |
| **Container Runtime**       | Docker        | 24+     | Containerization         |
| **Testing Framework**       | pytest        | 7.4+    | Unit & integration tests |
| **Load Testing**            | k6            | 0.48+   | Performance benchmarks   |
| **API Documentation**       | OpenAPI 3.0   | -       | Auto-generated docs      |

---

## 🔍 API Quick Reference

DataForge exposes **24 REST endpoints** organized by domain. All endpoints (except `/health`) require JWT authentication.

### Authentication

**Get Access Token:**

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'

# Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Use Token in Requests:**

```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  http://localhost:8001/api/v1/runs
```

### Core Endpoints

#### Health & Status (No Auth Required)

```bash
# System health check
GET /health

# Readiness check with dependency validation (FPVS Phase 1)
GET /ready
# Headers: X-Correlation-ID (optional)
# Returns: ready | degraded | unavailable

# Service version and build metadata (FPVS Phase 1)
GET /version

# API documentation
GET /docs              # Swagger UI
GET /redoc             # ReDoc
```

**GET /ready Response:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:45Z",
  "version": "1.0.0",
  "correlation_id": "abc-123-def",
  "dependencies": {
    "database": {"status": "ok", "latency_ms": 5},
    "pgvector": {"status": "ok", "latency_ms": 3},
    "redis": {"status": "ok", "latency_ms": 2}
  }
}
```

**GET /version Response:**
```json
{
  "service_name": "dataforge",
  "version": "1.0.0",
  "build_sha": "abc123def456789012345678901234567890abcd",
  "deployed_at": "2024-01-15T10:00:00Z",
  "schema_version": "1.0.0",
  "python_version": "3.11.6"
}
```

#### Authentication (4 endpoints)

```bash
# Login
POST /api/v1/auth/login
{
  "username": "user",
  "password": "password"
}

# Token refresh
POST /api/v1/auth/token/refresh
{
  "refresh_token": "..."
}

# MFA setup
POST /api/v1/auth/mfa/setup
GET /api/v1/auth/mfa/verify
```

#### NeuroForge Integration - Runs API (8 endpoints)

```bash
# Log LLM execution
POST /api/v1/runs
{
  "user_id": "user123",
  "operation_type": "prompt_execution",
  "project_name": "my-project",
  "model_name": "gpt-4",
  "input_data": {"prompt": "..."},
  "output_data": {"response": "..."},
  "metadata": {
    "tokens_used": 450,
    "latency_ms": 1234
  }
}

# Get single run
GET /api/v1/runs/{run_id}

# List runs
GET /api/v1/runs?user_id=user123&limit=50

# Filter by operation type
GET /api/v1/runs?operation_type=prompt_execution

# Get usage metrics
GET /api/v1/runs/usage/metrics?user_id=user123&days=30

# Delete run
DELETE /api/v1/runs/{run_id}
```

#### VibeForge Integration - Projects API (8 endpoints)

```bash
# Create project
POST /api/vibeforge/projects
{
  "user_id": "user123",
  "project_name": "My App",
  "project_type": "web_app",
  "selected_languages": ["javascript", "python"],
  "selected_stack": "next-js-gpt",
  "team_size": "solo",
  "timeline_weeks": 8
}

# Get project by ID
GET /api/vibeforge/projects/{project_id}

# List user projects
GET /api/vibeforge/projects?user_id=user123

# Project sessions (wizard tracking)
POST /api/vibeforge/sessions
GET /api/vibeforge/sessions/{session_id}
PATCH /api/vibeforge/sessions/{session_id}

# Stack outcomes (success metrics)
POST /api/vibeforge/outcomes
GET /api/vibeforge/outcomes/stack/{stack_id}

# Analytics
GET /api/vibeforge/analytics/stack-success
GET /api/vibeforge/analytics/language-trends
```

#### Vector Search (4 endpoints)

```bash
# Semantic search
POST /api/v1/search/semantic
{
  "query": "What is quantum computing?",
  "top_k": 5,
  "filters": {
    "user_id": "user123"
  }
}

# Store document with embedding
POST /api/v1/documents
{
  "content": "Document text...",
  "metadata": {...}
}

# Get document
GET /api/v1/documents/{document_id}

# Delete document
DELETE /api/v1/documents/{document_id}
```

#### Telemetry Events (ForgeCommand Integration)

```bash
# Query telemetry events (via telemetry_events view)
SELECT * FROM telemetry_events
WHERE service = 'neuroforge'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

# Get metric baselines for anomaly detection
SELECT * FROM metric_baselines
WHERE service = 'dataforge'
ORDER BY window_end DESC
LIMIT 1;

# View detected anomalies
SELECT * FROM detected_anomalies
WHERE severity IN ('high', 'critical')
  AND acknowledged = false
ORDER BY detected_at DESC;
```

**Tables/Views for ForgeCommand:**

- `events` - Base telemetry table for all Forge services
- `telemetry_events` - View alias for ForgeCommand compatibility
- `metric_baselines` - Statistical baselines for anomaly detection
- `detected_anomalies` - Anomalies detected via Z-score analysis

#### Audit & Compliance (3 endpoints)

```bash
# Get audit logs
GET /api/v1/audit/logs?user_id=user123&start_date=2025-01-01

# Compliance report
GET /api/v1/audit/compliance/report?framework=GDPR

# Anomaly detection events
GET /api/v1/audit/anomalies?severity=high
```

#### Multi-AI Planning Learning API (8 endpoints)

```bash
# Record planning outcome
POST /api/v1/learning/planning-outcomes
{
  "session_id": "abc123",
  "workflow_type": "multi_ai_planning",
  "task_type": "feature",
  "request_complexity": "medium",
  "stages": [
    {
      "stage": 1,
      "type": "initial",
      "model": "gpt-4",
      "provider": "openai",
      "duration_ms": 5000,
      "tokens_in": 1500,
      "tokens_out": 2000
    }
  ],
  "total_duration_ms": 25000,
  "total_tokens_used": 7500,
  "total_cost_cents": 85
}

# Update execution result
PATCH /api/v1/learning/planning-outcomes/{id}/execution
{
  "success": true,
  "duration_seconds": 180,
  "tasks_completed": 5,
  "tasks_failed": 0
}

# Record user feedback
PATCH /api/v1/learning/planning-outcomes/{id}/feedback
{
  "rating": 5,
  "feedback": "Excellent plan!",
  "plan_was_modified": false
}

# Get model performance metrics
GET /api/v1/learning/model-performance?model=gpt-4&stage_type=initial

# Get stage model recommendations
GET /api/v1/learning/recommendations/stage-models?task_type=feature

# Get time estimate
GET /api/v1/learning/recommendations/time-estimate?task_category=feature&task_complexity=medium

# Get iteration count recommendation
GET /api/v1/learning/recommendations/iteration-count?task_type=feature&complexity=complex

# Record estimation feedback
POST /api/v1/learning/estimation-feedback
[
  {
    "task_category": "feature",
    "task_complexity": "medium",
    "executor_type": "claude_code",
    "estimated_minutes": 60,
    "actual_minutes": 55,
    "accuracy_ratio": 0.92
  }
]
```

### Response Formats

**Success Response (200):**

```json
{
  "status": "success",
  "data": {...},
  "timestamp": "2025-11-23T12:00:00Z"
}
```

**Error Response (4xx/5xx):**

```json
{
  "status": "error",
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Run with ID abc123 not found",
    "details": {...}
  },
  "timestamp": "2025-11-23T12:00:00Z"
}
```

**Full API documentation:** [docs/guides/API_REFERENCE.md](./docs/guides/API_REFERENCE.md) or http://localhost:8001/docs

---

## 🛠️ Deployment

Three deployment options with increasing complexity and reliability:

| Mode                       | Setup Time | Nodes | SLA    | Best For                 |
| -------------------------- | ---------- | ----- | ------ | ------------------------ |
| **Development**            | 15 min     | 1     | -      | Local testing            |
| **Single-Node Production** | 30 min     | 1     | 99.0%  | Small-scale production   |
| **Multi-Node Production**  | 2 hours    | 3+    | 99.99% | Enterprise deployments   |
| **Kubernetes**             | 1–2 hours  | 3+    | 99.99% | Cloud-native deployments |

### Quick Deploy Commands

```bash
# Single-node production
bash scripts/deploy-single-node.sh

# Multi-node production
bash scripts/deploy-multi-node.sh

# Kubernetes (requires Helm)
helm install dataforge ./k8s/helm-chart -f values-prod.yaml
```

**Detailed instructions:** [docs/guides/DEPLOYMENT_GUIDE.md](./docs/guides/DEPLOYMENT_GUIDE.md)

---

## 📈 Performance & Scaling

### Target Metrics

- **API Latency:** <100ms (p95)
- **Throughput:** 1,000+ RPS sustained
- **Concurrent Clients:** 10,000+
- **Database Connections:** 500+ (with connection pooling)
- **Cache Hit Rate:** >95%

### Load Testing Results

Tested with **k6** framework under realistic production loads:

```bash
# Run performance tests
bash scripts/load-test.sh

# View results
cat results/k6-summary.json
```

**Load testing guide:** [docs/guides/LOAD_TESTING_GUIDE.md](./docs/guides/LOAD_TESTING_GUIDE.md)

### Scaling Strategies

**Vertical Scaling:**

- Increase CPU/memory allocation
- Tune database parameters (shared_buffers, work_mem)
- Optimize connection pooling
- Enable compression for large payloads

**Horizontal Scaling:**

- Multiple application instances behind load balancer
- PostgreSQL read replicas
- Redis Sentinel for cache failover
- RabbitMQ clustering for queue redundancy

---

## 📂 Project Structure

```
DataForge/
├── app/                          # Application source code
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Configuration management
│   ├── database.py               # Database connection and session
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py               # User and authentication
│   │   ├── run.py                # NeuroForge execution runs
│   │   ├── vibeforge_models.py   # VibeForge projects/sessions
│   │   └── audit.py              # Audit logging
│   ├── schemas/                  # Pydantic validation schemas
│   │   ├── run_schemas.py
│   │   ├── vibeforge_schemas.py
│   │   └── user_schemas.py
│   ├── routers/                  # API route handlers
│   │   ├── runs.py               # /api/v1/runs endpoints
│   │   ├── vibeforge.py          # /api/vibeforge endpoints
│   │   ├── auth.py               # /api/v1/auth endpoints
│   │   └── search.py             # /api/v1/search endpoints
│   ├── services/                 # Business logic layer
│   │   ├── run_service.py
│   │   ├── vibeforge_service.py
│   │   └── search_service.py
│   └── utils/                    # Utility functions
│       ├── security.py           # Encryption, hashing
│       ├── embeddings.py         # Vector generation
│       └── metrics.py            # Prometheus metrics
├── alembic/                      # Database migrations
│   ├── versions/                 # Migration files
│   └── env.py                    # Alembic configuration
├── tests/                        # Test suite (296 tests)
│   ├── unit/                     # Unit tests
│   ├── test_integration/         # Integration tests
│   │   ├── test_api_endpoints.py
│   │   ├── test_e2e_workflows.py
│   │   └── test_infrastructure_health.py
│   ├── test_security/            # Security tests
│   │   └── test_vulnerability_scanning.py
│   └── load/                     # Load testing
│       ├── test_k6_load.py
│       └── k6_test.js            # k6 load test script
├── docs/                         # Documentation
│   ├── guides/                   # How-to guides
│   │   ├── COMPREHENSIVE_DOCUMENTATION.md
│   │   ├── API_REFERENCE.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── OPERATIONS_RUNBOOK.md
│   │   ├── TROUBLESHOOTING_GUIDE.md
│   │   └── LOAD_TESTING_GUIDE.md
│   └── setup/                    # Setup guides
│       └── SETUP.md
├── k8s/                          # Kubernetes manifests
│   ├── helm-chart/               # Helm charts
│   └── manifests/                # Raw K8s YAML
├── scripts/                      # Operational scripts
│   ├── deploy-single-node.sh
│   ├── deploy-multi-node.sh
│   ├── db_check.py
│   └── rotate-audit-logs.sh
├── ops/                          # Operations configs
│   ├── prometheus/               # Prometheus configuration
│   └── grafana/                  # Grafana dashboards
├── static/                       # Static files
├── templates/                    # Email/report templates
├── logs/                         # Application logs
├── venv/                         # Python virtual environment
├── .env                          # Environment variables (not in git)
├── .env.example                  # Example environment file
├── requirements.txt              # Python dependencies
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # Docker development setup
├── docker-compose.prod.yml       # Docker production setup
├── Dockerfile                    # Container image
├── pytest.ini                    # Pytest configuration
├── mypy.ini                      # Type checking config
├── README.md                     # This file
├── ARCHITECTURE.md               # Architecture documentation
├── SECURITY.md                   # Security policy
├── LICENSE.md                    # Commercial license
└── LEGAL.md                      # Legal protections
```

### Key Files to Know

- **`app/main.py`** - Application entry point, router registration
- **`app/config.py`** - All configuration variables
- **`app/database.py`** - Database connection management
- **`alembic/versions/`** - Database schema migrations
- **`requirements.txt`** - All Python dependencies
- **`.env`** - Environment-specific configuration (create from `.env.example`)

---

## 📚 Documentation

All guides, references, and runbooks are organized consistently:

| Guide                                                                              | Purpose                                            | Lines |
| ---------------------------------------------------------------------------------- | -------------------------------------------------- | ----- |
| **[COMPREHENSIVE_DOCUMENTATION.md](./docs/guides/COMPREHENSIVE_DOCUMENTATION.md)** | Complete system overview, all phases, architecture | 1,158 |
| **[API_REFERENCE.md](./docs/guides/API_REFERENCE.md)**                             | All 24 endpoints with examples, error codes        | 884   |
| **[DEPLOYMENT_GUIDE.md](./docs/guides/DEPLOYMENT_GUIDE.md)**                       | Step-by-step deployment procedures                 | 729   |
| **[OPERATIONS_RUNBOOK.md](./docs/guides/OPERATIONS_RUNBOOK.md)**                   | Daily ops, monitoring, incident response           | 686   |
| **[TROUBLESHOOTING_GUIDE.md](./docs/guides/TROUBLESHOOTING_GUIDE.md)**             | Diagnostics and solutions for common issues        | 752   |
| **[LOAD_TESTING_GUIDE.md](./docs/guides/LOAD_TESTING_GUIDE.md)**                   | Performance testing procedures                     | -     |
| **[SETUP.md](./docs/setup/SETUP.md)**                                              | Development environment setup                      | 340   |
| **[SECURITY.md](./SECURITY.md)**                                                   | Security architecture and audit procedures         | 117   |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)**                                           | System design, components, scaling                 | 165   |
| **[LICENSE.md](./LICENSE.md)**                                                     | Commercial license terms                           | 93    |
| **[LEGAL.md](./LEGAL.md)**                                                         | IP rights and legal protections                    | 113   |

**Master index:** [../docs/README.md](../docs/README.md) - Complete organized documentation hub

**Ecosystem Documentation:**
- **[Quick Start Guide](../QUICK_START_GUIDE.md)** - Get all services running
- **[Next Steps & Roadmap](../NEXT_STEPS.md)** - Production deployment
- **[Quick Reference](../QUICK_REFERENCE.md)** - Command cheatsheet
- **[Latest Status](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)** - Dec 11, 2025 updates

---

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use (8001)

**Problem:** `Address already in use` error

**Solution:**

```bash
# Find process using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --port 8002
```

#### PostgreSQL Connection Failed

**Problem:** `Connection to database failed`

**Solutions:**

1. Check PostgreSQL is running:

   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql  # If not running
   ```

2. Verify DATABASE_URL in `.env`:

   ```bash
   # Correct format:
   DATABASE_URL=postgresql://username:password@localhost:5432/dataforge
   ```

3. Test connection manually:

   ```bash
   psql -h localhost -U username -d dataforge
   ```

4. Check pgvector extension:
   ```bash
   sudo -u postgres psql -d dataforge -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

#### Redis Connection Refused

**Problem:** `Error connecting to Redis`

**Solutions:**

1. Start Redis:

   ```bash
   sudo systemctl start redis
   # Or manually:
   redis-server
   ```

2. Test connection:

   ```bash
   redis-cli ping
   # Should return: PONG
   ```

3. Check REDIS_URL in `.env`:
   ```bash
   REDIS_URL=redis://localhost:6379/0
   ```

#### Migration Errors

**Problem:** `alembic upgrade head` fails

**Solutions:**

1. Check current migration state:

   ```bash
   alembic current
   ```

2. Reset to base (⚠️ destroys data):

   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

3. Generate new migration if schema changed:
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

#### Slow API Responses

**Problem:** API latency > 100ms

**Solutions:**

1. Enable PostgreSQL slow query logging:

   ```sql
   ALTER SYSTEM SET log_min_duration_statement = 100;
   SELECT pg_reload_conf();
   ```

2. Check Redis memory:

   ```bash
   redis-cli INFO memory
   ```

3. Review Prometheus metrics:

   ```bash
   curl http://localhost:8001/metrics | grep latency
   ```

4. Check database connection pool:
   ```python
   # In config, increase pool size:
   SQLALCHEMY_POOL_SIZE = 20
   SQLALCHEMY_MAX_OVERFLOW = 40
   ```

#### Authentication Errors

**Problem:** 401 Unauthorized responses

**Solutions:**

1. Get fresh token:

   ```bash
   curl -X POST http://localhost:8001/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user", "password": "pass"}'
   ```

2. Check token expiration:

   ```bash
   # Tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES (default: 1440 = 24 hours)
   ```

3. Verify SECRET_KEY is set in `.env`

#### Import Errors

**Problem:** `ModuleNotFoundError` or import errors

**Solutions:**

1. Reinstall dependencies:

   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. Check virtual environment is activated:

   ```bash
   which python
   # Should show: /path/to/DataForge/venv/bin/python
   ```

3. Install in development mode:
   ```bash
   pip install -e .
   ```

#### NeuroForge Can't Connect to DataForge

**Problem:** NeuroForge shows "DataForge connection failed"

**Solutions:**

1. Verify DataForge is running on port 8001:

   ```bash
   curl http://localhost:8001/health
   ```

2. Check NeuroForge `.env`:

   ```bash
   DATAFORGE_BASE_URL=http://localhost:8001
   ```

3. Check firewall rules:
   ```bash
   sudo ufw status
   sudo ufw allow 8001/tcp
   ```

### Testing & Debugging

```bash
# Run all tests with verbose output
pytest tests/ -v -s

# Run specific test file
pytest tests/test_integration/test_api_endpoints.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Enable debug logging
LOG_LEVEL=DEBUG python -m uvicorn app.main:app

# Check database state
python scripts/db_check.py

# View recent logs
tail -f logs/dataforge.log
```

**Detailed troubleshooting:** [docs/guides/TROUBLESHOOTING_GUIDE.md](./docs/guides/TROUBLESHOOTING_GUIDE.md)

---

## 🔒 Security & Compliance

DataForge is built with enterprise security as a first-class requirement:

### Authentication & Authorization

- OAuth2 / OIDC integration for enterprise identity
- Multi-factor authentication (TOTP + backup codes)
- Device tracking and session management
- Role-based access control (RBAC) with resource-level checks
- Automatic token expiration and revocation

### Data Protection

- AES-256 encryption at rest (field-level)
- TLS 1.3 for all in-transit communication
- Automatic key rotation without downtime
- Certificate pinning for external APIs
- Secure secret storage (HashiCorp Vault / AWS KMS compatible)

### Audit & Logging

- Immutable, cryptographically-signed event logs
- HMAC-SHA256 signatures on all audit records
- 90+ day event retention
- Real-time anomaly detection (6 detector types)
- Compliance reports (GDPR, CCPA, HIPAA, SOC2, PCI-DSS)

### Infrastructure Security

- Zero-trust architecture with network segmentation
- Rate limiting on all public endpoints
- Fail2Ban integration for brute-force protection
- Automated vulnerability scanning
- Supply chain integrity (pinned dependencies, no SaaS)

**Full security details:** [SECURITY.md](./SECURITY.md)

---

## 🙌 Support

### For Enterprise Customers

- **Technical Support:** charlesboswell@boswelldigitalsolutions.com
- **Licensing & Sales:** Same email
- **Security Issues:** Report via email with [SECURITY] prefix
- **Documentation Updates:** Submit via GitHub issues (private repo)

### Community

- Internal development only
- External contributions require written permission from Boswell Digital Solutions LLC
- Feature requests welcome via email

### Resources

- 📖 **Full Documentation** – [docs/guides/](./docs/guides/)
- 🐛 **Known Issues** – See [TROUBLESHOOTING_GUIDE.md](./docs/guides/TROUBLESHOOTING_GUIDE.md)
- 📊 **Architecture Overview** – [ARCHITECTURE.md](./ARCHITECTURE.md)
- 🔐 **Security Policy** – [SECURITY.md](./SECURITY.md)
- 🌐 **Ecosystem Docs** – [../docs/README.md](../docs/README.md)
- 🚀 **Quick Start All Services** – [../QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)

---

## 📋 License & Copyright

**DataForge** is a commercial product owned by **Boswell Digital Solutions LLC**.

- ✅ Licensed for internal use and private infrastructure deployment
- ✅ Licensed for integration with other Forge Ecosystem products
- ❌ Not licensed for redistribution, resale, or public access
- ❌ Not licensed for reverse engineering or derivative products

See [LICENSE.md](./LICENSE.md) for complete license terms.

See [LEGAL.md](./LEGAL.md) for intellectual property protections.

---

## 🎯 Final Notes

**DataForge** is the backbone of the Forge Ecosystem. This repository contains:

✅ **Complete architecture** with 5-layer design
✅ **Full deployment guides** for single-node, multi-node, and Kubernetes
✅ **Comprehensive documentation** (7,242+ lines)
✅ **Fully-passing test suite** (296/296 tests, 100% pass rate)
✅ **Enterprise security** with OAuth2, MFA, encryption, audit logs
✅ **High availability** with 99.99% SLA for multi-node deployments
✅ **Production-ready** with observability, monitoring, and alerting

**Status:** ✅ **Production Ready**  
**Maintained by:** Boswell Digital Solutions LLC  
**Version:** 5.2 (18/18 phases complete)

---

## 🚦 Quick Links

- 🌐 **API Server**: http://localhost:8001
- 🔧 **API Docs**: http://localhost:8001/docs
- 📊 **Metrics**: http://localhost:8001/metrics
- 📖 **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 📚 **Full Documentation**: [docs/guides/](./docs/guides/)
- 🔒 **Security Policy**: [SECURITY.md](./SECURITY.md)
- ⚖️ **License**: [LICENSE.md](./LICENSE.md)

---

## 📋 Development Workflow

### Daily Development

```bash
# Start DataForge
cd DataForge
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# In another terminal: Run tests
pytest tests/ -v

# In another terminal: Monitor logs
tail -f logs/dataforge.log
```

### Making Changes

```bash
# 1. Create new branch
git checkout -b feature/my-feature

# 2. Make changes to code

# 3. Create migration (if models changed)
alembic revision --autogenerate -m "Add new field"
alembic upgrade head

# 4. Run tests
pytest tests/ -v

# 5. Check code quality
black app/ tests/
flake8 app/ tests/
mypy app/

# 6. Commit and push
git add .
git commit -m "feat: description"
git push origin feature/my-feature
```

### Testing Strategy

```bash
# Unit tests (fast, no external dependencies)
pytest tests/unit/ -v

# Integration tests (require database)
pytest tests/test_integration/ -v

# Security tests
pytest tests/test_security/ -v

# Load tests (k6 required)
k6 run tests/load/k6_test.js --vus 50 --duration 5m

# Coverage report
pytest tests/ --cov=app --cov-report=html
```

---

**Last Updated:** December 21, 2025
**System Status:** ✅ HEALTHY (100% Operational - All 4 Forge services running)
**Next Review:** Q1 2026

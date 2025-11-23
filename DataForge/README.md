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
  <img src="https://img.shields.io/badge/Status-Advanced%20Alpha-blue" />
  <img src="https://img.shields.io/badge/License-Commercial-red" />
  <img src="https://img.shields.io/badge/Tests-296%20Passing-brightgreen" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" />
  <img src="https://img.shields.io/badge/Version-5.2-blue" />
  <img src="https://img.shields.io/badge/Core%20Phases-18/18-brightgreen" />
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
2. [Ecosystem Role](#-ecosystem-role)
3. [Key Features](#-key-features)
4. [System Architecture](#%EF%B8%8F-system-architecture)
5. [Quick Start](#-quick-start)
6. [Technology Stack](#-technology-stack)
7. [Project Phases](#-project-phases)
8. [API Quick Reference](#-api-quick-reference)
9. [Deployment](#-deployment)
10. [Performance & Scaling](#-performance--scaling)
11. [Documentation](#-documentation)
12. [Troubleshooting](#-troubleshooting)
13. [Security & Compliance](#-security--compliance)
14. [Support](#-support)

---

## 📘 Overview

**DataForge** is the central data and knowledge engine powering the entire **Forge Ecosystem**. As an **advanced alpha** maturing into production-grade infrastructure, it serves as the shared memory layer and source of truth for all Forge products: VibeForge (freeware), NeuroForge, AuthorForge, TradeForge, and specialized analysis modules.

### Core Capabilities

- **Unified Intelligence Layer** – Single source of truth for all Forge products
- **Semantic Retrieval** – pgvector embeddings for context-aware search and RAG pipelines
- **Event Auditing** – Immutable, cryptographically signed logs with 90+ day retention
- **Field-Level Encryption** – AES-256 encryption for sensitive data with key rotation
- **Anomaly Detection** – 6 detector types (travel, brute force, exfiltration, patterns, after-hours, bulk mutations)
- **Compliance Frameworks** – GDPR, CCPA, HIPAA automation with extensible policy engine
- **Production Observability** – Prometheus metrics, OpenTelemetry tracing, Grafana dashboards

### Project Status at a Glance

| Metric                  | Value                         |
| ----------------------- | ----------------------------- |
| **Development Stage**   | **Advanced Alpha** (Maturing) |
| **Core Phases**         | 18/18 complete ✅             |
| **Tests Passing**       | 296/296 (100%) ✅             |
| **Production Code**     | 27,857+ lines                 |
| **Total Documentation** | 10,800+ lines                 |
| **Current Version**     | 5.2                           |
| **Commercial License**  | ✅ [LICENSE.md](./LICENSE.md) |
| **IP Protection**       | ✅ [LEGAL.md](./LEGAL.md)     |

---

## 🔗 Ecosystem Role

DataForge acts as the **shared intelligence layer** for the Forge Suite of products:

| Product         | Role                                                                        |
| --------------- | --------------------------------------------------------------------------- |
| **AuthorForge** | Writing knowledge, narrative structures, pacing, genre-level analysis       |
| **NeuroForge**  | Model routing, embeddings generation, context retrieval, inference tracking |
| **VibeForge**   | Execution context, prompt performance analytics, evaluation datasets        |
| **TradeForge**  | Market signals, historical feeds, structured financial datasets             |
| **Leopold**     | Ecological observations, biological datasets, environmental tracking        |
| **Livy**        | Historical data, geospatial narratives, temporal analysis                   |

Every Forge product consumes DataForge as the **source of truth**, ensuring:

- ✅ Consistency across the ecosystem
- ✅ Enterprise-grade compliance
- ✅ Cross-product intelligence and analytics
- ✅ Unified security and audit trails

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

- **Vector embeddings** – OpenAI, Anthropic, or local model support
- **Similarity search** – Fast cosine/L2 distance queries over embeddings
- **Context retrieval** – Intelligent chunk selection for RAG pipelines
- **Knowledge base queries** – Natural language QA over documents
- **Semantic caching** – Redis-backed deduplication for repeated queries
- **Embedding versioning** – Track embedding model changes over time

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
- **RabbitMQ** 3.8+ (for async tasks)
- **Linux/macOS/WSL2** (Windows native not supported)

### Installation (5 minutes)

```bash
# Clone the repository
git clone https://github.com/YOUR_PRIVATE_REPO/DataForge.git
cd DataForge

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Interactive API docs
open http://localhost:8000/docs

# ReDoc documentation
open http://localhost:8000/redoc
```

### Next Steps

- **Read the full setup guide:** [docs/setup/SETUP.md](./docs/setup/SETUP.md)
- **Deploy to production:** [docs/guides/DEPLOYMENT_GUIDE.md](./docs/guides/DEPLOYMENT_GUIDE.md)
- **Explore the API:** [docs/guides/API_REFERENCE.md](./docs/guides/API_REFERENCE.md)
- **Run operational tasks:** [docs/guides/OPERATIONS_RUNBOOK.md](./docs/guides/OPERATIONS_RUNBOOK.md)

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

DataForge exposes **24 REST endpoints** organized by domain:

### Categories

- **Health & Status** (2 endpoints) – System status, readiness
- **Authentication** (4 endpoints) – Login, token refresh, MFA setup
- **Data Operations** (8 endpoints) – CRUD operations on core entities
- **Search & Retrieval** (4 endpoints) – Vector search, semantic queries
- **Audit & Compliance** (3 endpoints) – Event logs, compliance reports
- **Admin** (3 endpoints) – System management, diagnostics

### Example Endpoints

```bash
# Health check (no auth required)
GET /health

# Interactive API documentation
GET /docs
GET /redoc

# Login
POST /auth/login
POST /auth/token/refresh

# Get all entities
GET /api/v1/entities
GET /api/v1/entities/{id}

# Semantic search (vector similarity)
POST /api/v1/search/semantic

# Audit logs
GET /api/v1/audit/logs
```

**Full API documentation:** [docs/guides/API_REFERENCE.md](./docs/guides/API_REFERENCE.md)

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

## 📚 Documentation

All guides, references, and runbooks are organized consistently:

| Guide                                                                              | Purpose                                            | Lines |
| ---------------------------------------------------------------------------------- | -------------------------------------------------- | ----- |
| **[COMPREHENSIVE_DOCUMENTATION.md](./docs/guides/COMPREHENSIVE_DOCUMENTATION.md)** | Complete system overview, all phases, architecture | 1,158 |
| **[API_REFERENCE.md](./docs/guides/API_REFERENCE.md)**                             | All 24 endpoints with examples, error codes        | 884   |
| **[DEPLOYMENT_GUIDE.md](./docs/guides/DEPLOYMENT_GUIDE.md)**                       | Step-by-step deployment procedures                 | 729   |
| **[OPERATIONS_RUNBOOK.md](./docs/guides/OPERATIONS_RUNBOOK.md)**                   | Daily ops, monitoring, incident response           | 686   |
| **[TROUBLESHOOTING_GUIDE.md](./docs/guides/TROUBLESHOOTING_GUIDE.md)**             | Diagnostics and solutions for common issues        | 752   |
| **[SETUP.md](./docs/setup/SETUP.md)**                                              | Development environment setup                      | 340   |
| **[SECURITY.md](./SECURITY.md)**                                                   | Security architecture and audit procedures         | 117   |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)**                                           | System design, components, scaling                 | 164   |
| **[LICENSE.md](./LICENSE.md)**                                                     | Commercial license terms                           | 93    |
| **[LEGAL.md](./LEGAL.md)**                                                         | IP rights and legal protections                    | 113   |

**Master index:** [CONSOLIDATED_DOCUMENTATION_INDEX.md](../CONSOLIDATED_DOCUMENTATION_INDEX.md) (project root)

---

## 🔧 Troubleshooting

Common issues and solutions:

| Issue                            | Solution                                                          |
| -------------------------------- | ----------------------------------------------------------------- |
| **Port already in use**          | `lsof -i :8000` and kill the process, or use different port       |
| **PostgreSQL connection failed** | Check `DATABASE_URL` in `.env`, verify PostgreSQL is running      |
| **Redis connection refused**     | Verify Redis is running on `localhost:6379`, check firewall rules |
| **RabbitMQ connection error**    | Check `RABBITMQ_URL`, ensure RabbitMQ service is running          |
| **Slow API responses**           | Enable slow query logging in PostgreSQL, check Redis memory       |
| **MFA code invalid**             | Verify system clock is synchronized, check TOTP secret            |
| **Audit log bloat**              | Run `python scripts/rotate-audit-logs.sh` monthly                 |

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
✅ **Comprehensive documentation** (10,221+ lines)
✅ **Fully-passing test suite** (296/296 tests, 100% pass rate)
✅ **Enterprise security** with OAuth2, MFA, encryption, audit logs
✅ **High availability** with 99.99% SLA for multi-node deployments
✅ **Production-ready** with observability, monitoring, and alerting

**Status:** ✅ **Production Ready**  
**Maintained by:** Boswell Digital Solutions LLC  
**Version:** 5.1 (18/18 phases complete)

---

**Last Updated:** January 2025  
**Next Review:** Q2 2025

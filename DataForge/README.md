<p align="center">
  <img src="https://firebasestorage.googleapis.com/v0/b/endless-fire-467204-n2.firebasestorage.app/o/Forge%2FDataForge_icon.avif?alt=media&token=1e81b1bd-9cf2-4e56-9f3a-e9aa14b9cd0a"
       alt="DataForge Logo"
       width="180"
       style="border-radius: 12px;" />
</p>

<h1 align="center">DataForge</h1>
<h3 align="center">Enterprise-Grade Data & Knowledge Engine for the Forge Ecosystem</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen" />
  <img src="https://img.shields.io/badge/License-Commercial-red" />
  <img src="https://img.shields.io/badge/Tests-296%20Passing-brightgreen" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" />
</p>

---

> **License:** Commercial – Not open-source.  
> © 2025 Boswell Digital Solutions LLC. All Rights Reserved.

---

# 📘 Overview

**DataForge** is the central data and knowledge engine powering the entire **Forge Ecosystem**, including AuthorForge, NeuroForge, VibeForge, TradeForge, Livy, and Leopold.  
It provides high-availability data storage, semantic retrieval, event auditing, field-level encryption, anomaly detection, compliance automation, and production-grade observability.

This system is built for **enterprise-level workloads**, with a layered architecture that emphasizes:

- Security  
- Reliability  
- Compliance  
- High availability  
- Performance  
- Full operational transparency  

**Current Project Status:**  
- **Version:** 5.1  
- **Phases Completed:** 18/18 (100%)  
- **Total Tests:** 296 (100% passing)  
- **Documentation:** 4,200+ lines across 18 guides  
- **Production Readiness:** **✅ Fully Ready**

---

# 🔗 Quick Links

### Core Documentation  
- **Comprehensive Architecture & Phases**  
  `docs/guides/COMPREHENSIVE_DOCUMENTATION.md`  
- **API Reference (24 Endpoints)**  
  `docs/guides/API_REFERENCE.md`  
- **Deployment Guide**  
  `docs/guides/DEPLOYMENT_GUIDE.md`  
- **Operations Runbook**  
  `docs/guides/OPERATIONS_RUNBOOK.md`  
- **Troubleshooting Guide**  
  `docs/guides/TROUBLESHOOTING_GUIDE.md`  

---

# 🧠 Ecosystem Role

DataForge acts as the **shared memory layer** for the Forge Suite:

- **AuthorForge** – writing knowledge, genre structures, pacing, scene-level analysis  
- **NeuroForge** – model routing, embeddings, context retrieval  
- **VibeForge** – execution context, prompt analytics, evaluation data  
- **TradeForge** – market signals, historical feeds, structured datasets  
- **Leopold** – ecological observations, biological datasets  
- **Livy** – historical data, geospatial narratives  

Every Forge product consumes DataForge as the **source of truth**, ensuring consistency, compliance, and cross-product intelligence.

---

# 🏗️ System Architecture

┌───────────────────────────────────────────────┐
│ Client Layer │
│ AuthorForge · NeuroForge · VibeForge · Apps │
└───────────────────────────┬────────────────────┘
│
┌───────────────────────────▼────────────────────┐
│ API Gateway │
│ Routing · Rate Limiting · Load Balancing │
└───────────────────────────┬────────────────────┘
│
┌───────────────────────────▼────────────────────┐
│ Application Layer │
│ FastAPI · Auth · Business Logic · Validation │
│ │
│ ┌────────┬──────────────┬──────────────┬─────┐│
│ │ Auth │ Data Access │ Event Audit │ Comp ││
│ └────────┴──────────────┴──────────────┴─────┘│
└───────────────────────────┬────────────────────┘
│
┌───────────────────▼──────────────┐
│ PostgreSQL │
│ Encrypted Fields · Replication │
└───────────────────┬──────────────┘
│
┌───────────────────▼──────────────┐
│ Redis │
│ Cache · Rate Limits · Sessions │
└──────────────────────────────────┘

markdown
Copy code

---

# ⭐ Key Features

### 🔐 **Security**
- OAuth2/OIDC, MFA (TOTP), backup codes  
- AES-256 field-level encryption  
- Automatic key rotation  
- Immutable audit logs (HMAC-SHA256)  
- 6-type anomaly detection  
- Full GDPR/CCPA/HIPAA/SOC2/PCI-DSS compliance

### ⚙️ **Reliability & HA**
- PostgreSQL replication + auto-failover  
- Redis Sentinel & cluster failover  
- Circuit breaker, retries, DLQs  
- 99.99% multi-region SLA design  
- Automatic backups (hourly/daily/weekly/monthly)

### 📡 **Observability**
- Prometheus metrics  
- OpenTelemetry distributed tracing  
- 24/7 alerting  
- Full operational runbook and incident playbooks

### 📚 **Knowledge & Data Layer**
- pgvector embeddings  
- Optimized query layer  
- Canonical search & ranking  
- Compliance logging & provenance tracking  

---

# 🚀 Quick Start

### Prerequisites
- Python 3.11+  
- PostgreSQL 13+ (with pgvector)  
- Redis 6+  
- Linux/macOS/WSL2  

### Install & Run
```bash
git clone https://github.com/YOUR_PRIVATE_REPO/DataForge.git
cd DataForge

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8000
Verify
bash
Copy code
curl http://localhost:8000/health
open http://localhost:8000/docs
📑 Project Phases
All phases completed (100%):

Phase	Area	Status
0	Automated Backups	✅
1	Operational Excellence	✅
2	Fault Tolerance	✅
3	High Availability	✅
4	Security	✅
5	Documentation & Testing	✅

🧪 Technology Stack
Backend: FastAPI, Python 3.11+, SQLAlchemy, Alembic
Database: PostgreSQL + pgvector
Cache: Redis 6+
Queue: Celery + RabbitMQ
Monitoring: Prometheus, Grafana
Tracing: OpenTelemetry
Containerization: Docker, Kubernetes optional

🔍 API Quick Reference
See full API docs in:
docs/guides/API_REFERENCE.md

🛠️ Deployment
Deployment options:

Mode	Time	Nodes	SLA
Development	15 min	1	-
Single-Node Production	30 min	1	99.0%
Multi-Node Production	2 hrs	3+	99.99%
Kubernetes	1–2 hrs	3+	99.99%

Full instructions → docs/guides/DEPLOYMENT_GUIDE.md

📈 Performance & Scaling
<100ms target API latency

1,000+ RPS sustained

10,000+ concurrent clients

Graceful degradation with circuit breakers

Load tested with k6.

🔧 Troubleshooting
Detailed troubleshooting is located in:
docs/guides/TROUBLESHOOTING_GUIDE.md

Includes solutions for:

Startup failures

DB connectivity

Redis issues

Slow API responses

Authentication failures

Anomaly spikes

Backup/restore issues

🔒 License (Commercial)
pgsql
Copy code
Copyright (c) 2025
Boswell Digital Solutions LLC
All Rights Reserved.

This software is licensed for commercial use only.
Unauthorized copying, distribution, modification,
or resale is strictly prohibited.
🙌 Contributing
Internal development only.
External contributions require written permission from:

charlesboswell@boswelldigitalsolutions.com

🏁 Final Notes
DataForge is the backbone of the entire Forge ecosystem.
This repository contains:

Complete architecture

Full deployment & ops guides

4,200+ lines of documentation

296 fully-passing tests

Proven HA, security, and compliance layers

Status: Production-Ready ✔️
Maintained by Boswell Digital Solutions LLC

yaml
Copy code

---

If you want:  
✨ A branded PDF version  
✨ A DOCX + letterhead version  
✨ A matching LICENSE.md, LEGAL.md, SECURITY.md, or ARCHITECTURE.md  
✨ Or a fully auto-generated GitHub Pages docs site  

Just say **“generate it.”**-m
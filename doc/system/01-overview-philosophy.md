# §1 — Overview & Philosophy

## Service Identity

**DataForge** is the unified data and knowledge engine of the Forge Ecosystem. It runs on port **8001** and serves as the single, authoritative source of truth for all durable state across every Forge service.

- **Version:** v5.2
- **Status:** 18/18 phases complete
- **Scale:** 42,732 LOC across 133 Python files
- **Tests:** 296/296 passing, 82% coverage
- **Port:** 8001

## The Source-of-Truth Contract

DataForge is not a cache. It is not a secondary store. It is not a convenience API. It is the truth.

Every service in the Forge Ecosystem that produces durable state writes to DataForge. This is a non-negotiable architectural invariant:

- **NeuroForge** writes all LLM run results, model performance metrics, and inference records.
- **VibeForge** writes project sessions, stack outcomes, and code analysis results.
- **AuthorForge** writes all narrative content: books, chapters, scenes, characters, arcs, locations, manuscripts.
- **ForgeAgents / BugCheck** writes findings, lifecycle events, enrichment artifacts, and progress events.
- **Forge:SMITH** writes planning sessions, portfolio projects, evaluation snapshots, and governance events.
- **ForgeCommand** writes run records, lifecycle transitions, and finalization states.

No service maintains a local truth cache. No service treats its own database as canonical. All reads for authoritative state flow through DataForge. All writes that create or mutate durable state flow through DataForge.

**If DataForge is unavailable, runs do not start. This is by design.**

## Ecosystem Role

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Forge Ecosystem                                 │
│                                                                       │
│   NeuroForge  VibeForge  AuthorForge  ForgeAgents  SMITH  BugCheck   │
│       │           │           │            │          │        │      │
│       └───────────┴───────────┴────────────┴──────────┴────────┘      │
│                                   │                                   │
│                            ┌──────▼──────┐                           │
│                            │  DataForge  │  ← The Source of Truth    │
│                            │   (8001)    │                           │
│                            └──────┬──────┘                           │
│                                   │                                   │
│                    ┌──────────────┼──────────────┐                   │
│                    │              │              │                   │
│             ┌──────▼─────┐  ┌────▼────┐  ┌─────▼────┐             │
│             │ PostgreSQL  │  │  Redis  │  │ pgvector  │             │
│             │  (primary)  │  │ (cache) │  │  (ANN)    │             │
│             └─────────────┘  └─────────┘  └──────────┘             │
└───────────────────────────────────────────────────────────────────────┘
```

## Core Responsibilities

### 1. Durable State Persistence
All service state — run records, findings, projects, content, events — is stored in PostgreSQL via SQLAlchemy ORM models. State is never ephemeral unless explicitly designed to be (e.g., Redis cache).

### 2. Semantic Knowledge Retrieval
DataForge stores documents with 1536-dimensional vector embeddings. It provides hybrid search combining cosine similarity (Voyage AI embeddings) with BM25 keyword scoring via Reciprocal Rank Fusion (RRF), delivering +40% accuracy over pure semantic search.

### 3. Authentication & Authorization
DataForge manages the full auth stack: JWT issuance, OAuth2/OIDC flows, TOTP 2FA, API key management, and scoped run tokens. Every write operation to DataForge requires a valid credential.

### 4. Audit & Compliance
An append-only, HMAC-SHA256-signed audit log captures all significant events. Field-level AES-256 Fernet encryption protects PII. Anomaly detection covers six threat patterns. Compliance targets include GDPR, CCPA, HIPAA, SOC2, and PCI-DSS.

### 5. Lifecycle Enforcement
DataForge enforces the BugCheck finding lifecycle state machine at the API level. Invalid transitions return 409 Conflict. After a run is finalized, new findings are rejected with 409. These are invariants, not policies.

### 6. Observability Infrastructure
Prometheus metrics at `/metrics`, OpenTelemetry distributed tracing, structured JSON logging, and a dead-letter queue for failed async tasks.

## What DataForge Is Not

- **Not a message bus.** It does not replace Celery/Redis for async task queuing, though it operates a DLQ.
- **Not a CDN.** Static assets live elsewhere; DataForge serves document content, not binary blobs.
- **Not an orchestrator.** ForgeCommand orchestrates runs; DataForge persists their state.
- **Not an LLM gateway.** NeuroForge routes LLM inference; DataForge stores the results.

## Performance Targets

| Metric | Target |
|--------|--------|
| API latency (p95) | < 100ms |
| Throughput | 1,000+ RPS |
| Uptime SLA | 99.99% |
| PostgreSQL failover | < 30 seconds |
| Redis failover | < 10 seconds |

*See §11 for critical constraints and invariants that must never be violated.*

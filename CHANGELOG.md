# Forge Ecosystem Changelog

All notable changes to the Forge Ecosystem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added - CSSA Phase 0 (Authority Lock)

Landed the DataForge-resident authority artifacts for the ForgeAgents **Cloud Service Security
Authority (CSSA)** subsystem. Documentation/acceptance only — per the Phase 0 "no advance" rule, **no
contract schemas, Pydantic models, or `app/security/` code are introduced.**

- `docs/cloud-security/CSSA_AUTHORITY_PLAN.md` — canonical authority model (invariants, identity/
  entitlement/quota/data-boundary law, decision/authorization/outcome/incident contracts, 11-phase
  rollout plan, verification matrix).
- `docs/cloud-security/PHASE_0_ACCEPTANCE.md` — Phase 0 gate checklist, consistency review against
  DataForge critical rules and telemetry trust laws, cross-repo ownership sign-off matrix, and
  DataForge-side acceptance of the immutable-audit, quota-reservation, and quarantine boundaries.
- `docs/cloud-security/OPEN_DECISIONS.md` — status/owners/resolutions for the seven open decisions;
  signing authority identified (ForgeCommand for production, repo-trusted dev key for Phases 2–7).
- `docs/cloud-security/README.md` — index and reading order.

Phase 1 (Contract kernel) is gated on full countersignature of the ownership matrix.

---

## [6.0.0] - 2026-02-24

### Added - Multi-Provider Pipeline Infrastructure

**New Database Tables (6 tables)**:

- `model_catalog` — 14-model catalog across 4 providers (OpenAI, Anthropic, Google, xAI) with 3 tiers (budget, workhorse, flagship)
- `pricing_snapshot` — Historical pricing snapshots per model with raw content hash
- `pricing_alert` — Price change alerts with severity levels (info, warning, critical)
- `pricing_monitor_run` — Pricing monitor agent run tracking (trigger, status, changes detected)
- `cost_ledger` — Per-inference cost recording (model, provider, tokens, cost_usd, cached_tokens, batch_savings)
- `batch_queue` — Batch inference job tracking (batch_id, provider, model_id, status, item counts, cost)

**Migrations**:

- `012_add_multi_provider_tables.py` — Creates model_catalog, pricing_snapshot, pricing_alert, pricing_monitor_run, cost_ledger tables
- `014_add_batch_queue_table.py` — Creates batch_queue table with UUID PK and status indexes

**API Routers (3 new)**:

- `model_catalog` — CRUD for model catalog entries (GET list, GET by id, POST, PUT, DELETE)
- `pricing` — Pricing snapshots, alerts, monitor runs (GET/POST snapshots, GET/POST alerts, POST/PATCH runs)
- `cost_ledger` — Cost entry recording and aggregation (POST record, GET by run, GET aggregations, GET by-task-type)

**Seed Script**:

- `scripts/seed_model_catalog.py` — Seeds all 14 models:
  - Budget: gpt-5-nano, gpt-4.1-nano, gemini-2.5-flash-lite, grok-4-1-fast-non-reasoning
  - Workhorse: gemini-2.5-flash, gemini-3-flash, gpt-5-mini, gpt-4.1-mini, grok-4-1-fast-reasoning, claude-haiku-4.5
  - Flagship: gemini-2.5-pro, gemini-3-pro, claude-sonnet-4.5, claude-opus-4.5
- All cost fields use `Decimal` precision
- Includes per-model capabilities: `supports_batch`, `supports_structured_output`, `cache_read_discount`, `max_context`

---

## [5.3.0] - 2025-11-23

### Added - DataForge Phase 3.1: VibeForge Learning Layer Backend

**Core Implementation**:

- Complete database schema with 4 tables (`vibeforge_projects`, `project_sessions`, `stack_outcomes`, `model_performance`)
- Alembic migration with foreign key relationships and indexes
- SQLAlchemy ORM models (123 lines) with proper type hints
- Pydantic schemas (305 lines) with comprehensive validation
- Service layer (263 lines) with 20 CRUD methods
- FastAPI router (472 lines) with 30+ RESTful endpoints

**API Endpoints**:

- Project CRUD: 5 endpoints (create, list, get, update, delete)
- Session tracking: 6 endpoints (create, get, update, complete, abandon)
- Outcome logging: 4 endpoints (create, get, update by project/stack)
- Performance tracking: 4 endpoints (create, get, update by session)
- Preferences & analytics: 8+ endpoints (user prefs, favorites, stack success, model acceptance)
- Health check: 1 endpoint

**Testing**:

- 20 comprehensive integration tests (100% passing)
- FastAPI TestClient with SQLite in-memory testing
- Test coverage: 68% (router), 69% (service), 100% (models/schemas)
- Edge case validation and error handling tests
- All tests running in CI/CD pipeline

**Documentation**:

- Complete Phase 3.1 completion certificate (471 lines)
- API endpoint coverage matrix
- Technical implementation details
- Production readiness checklist

### Fixed

- Test status code assertions (200 → 201) for POST endpoints
- Schema field name correction (`tests_pass_rate` → `test_pass_rate`)
- Timestamp field alignment (`created_at` → `recorded_at` for outcomes)

---

## [5.2.0] - 2025-11-23

### Added - VibeForge Learning Layer (Phase 3.2 & 3.3)

**Backend Integration (Phase 3.2)**:

- DataForge schema with 5 learning tables (`vibeforge_projects`, `project_sessions`, `stack_outcomes`, `model_performance`, `language_preferences`)
- 41 CRUD service methods across 5 service classes
- 9 RESTful API endpoints for learning data management
- Alembic migration with 23+ indexes for query optimization
- Pydantic schemas with comprehensive validation

**Frontend Integration (Phase 3.3)**:

- Real-time learning data collection throughout wizard flow
- Adaptive recommendation engine based on historical data
- Success prediction using ML analysis
- Pattern detection for user preferences
- Complete API client with TypeScript types
- Learning analytics dashboard components

**Documentation**:

- Complete Phase 3.2 summary (17KB)
- Complete Phase 3.3 summary (15KB)
- Session summary for November 23, 2025 (15KB)
- Technical due diligence review (20KB)
- Updated README with licensing restructure

### Changed

- Root README: Updated to reflect licensing (commercial vs freeware)
- VibeForge README: Complete redesign as freeware entry product
- DataForge README: Positioned as Advanced Alpha, maturing core
- NeuroForge README: Removed MIT license, added commercial terms
- AuthorForge README: Added commercial licensing and cathedral integration
- Documentation organization: Moved session summaries to `docs/references/`
- Documentation organization: Moved phase completions to `docs/archive/phase-X/`
- Documentation organization: Moved blueprints to `docs/guides/`

### Fixed

- Documentation consolidation: 24+ root-level docs moved to appropriate locations
- Duplicate PHASE summaries consolidated
- Outdated completion docs archived
- README licensing inconsistencies resolved

---

## [5.1.0] - 2025-11-22

### Added - LLM Provider Integration (Phase 1.2)

**NeuroForge Enhancements**:

- Ollama provider for local model execution
- Llama 3.2, Mistral, Code Llama model support
- Provider status endpoint (`GET /api/v1/providers`)
- Model catalog expanded to 8 models (5 API + 3 local)

**VibeForge Enhancements**:

- JWT authentication integration
- Frontend API client with auth support
- Secure token management

**Documentation**:

- LLM Provider Integration Complete (11KB)
- Updated API documentation
- Security policy updates

### Changed

- Model routing logic enhanced for multi-provider support
- Authentication flow unified across products
- Environment-based configuration improved

---

## [5.0.0] - 2025-11-21

### Added - Authentication & Security

**NeuroForge**:

- JWT authentication for workbench
- Rate limiting on login endpoints (5 attempts/min per IP)
- Environment-based security controls
- DataForge stateless integration

**Security Features**:

- OAuth2/OIDC authentication
- Multi-factor authentication (TOTP + backup codes)
- Field-level AES-256 encryption
- Immutable audit logs with HMAC-SHA256 signatures

**Compliance**:

- GDPR automation
- CCPA compliance frameworks
- HIPAA-ready infrastructure
- SOC2 controls implementation

### Documentation

- Authentication complete (comprehensive guide)
- Security policy (SECURITY.md)
- Legal framework (LEGAL.md)

---

## [4.5.0] - 2025-11-20

### Added - DataForge Phase 4 (High Availability)

**Infrastructure**:

- Multi-node replication with automatic failover
- Redis Sentinel for cache failover
- RabbitMQ mirroring for queue reliability
- Circuit breakers and retry mechanisms

**Backup & Recovery**:

- Automated backups (hourly/daily/weekly/monthly)
- Point-in-time recovery capability
- 99.99% SLA for multi-node deployments

**Observability**:

- Prometheus metrics (40+ application metrics)
- OpenTelemetry distributed tracing
- Grafana pre-built dashboards
- Real-time alerting (Slack, PagerDuty, email)
- SLO tracking and reporting

### Documentation

- Deployment guide (729 lines)
- Operations runbook (686 lines)
- Troubleshooting guide (752 lines)
- Kubernetes deployment guide

---

## [4.0.0] - 2025-11-15

### Added - DataForge Core (18 Phases Complete)

**Phase 1-3: Foundation**:

- PostgreSQL with pgvector embeddings
- SQLAlchemy ORM with async support
- FastAPI REST API (24 endpoints)
- Redis caching layer
- RabbitMQ message queue
- Celery task worker

**Phase 4-6: Security**:

- OAuth2/OIDC authentication
- Field-level encryption (AES-256)
- Audit logging system
- Rate limiting and circuit breakers

**Phase 7-9: Advanced Features**:

- Semantic search with vector embeddings
- RAG pipeline integration
- Anomaly detection (6 detector types)
- Compliance frameworks

**Phase 10-12: Enterprise**:

- Multi-tenant support
- Resource quotas and limits
- API versioning
- Webhook system

**Phase 13-15: Resilience**:

- Database replication
- Automatic failover
- Backup and recovery
- Disaster recovery planning

**Phase 16-18: Observability**:

- Prometheus monitoring
- OpenTelemetry tracing
- Grafana dashboards
- Automated alerting

**Testing**:

- 296 tests passing (100%)
- Unit, integration, and end-to-end coverage
- Load testing with k6
- Security testing

**Documentation**:

- 10,800+ lines of documentation
- Comprehensive API reference (884 lines)
- Architecture documentation (164 lines)
- 5 operational guides

---

## [3.0.0] - 2025-11-10

### Added - VibeForge Phase 2 (Project Creation Wizard)

**Milestone 2.1-2.3**:

- Wizard architecture with state management
- Step 1: Project Intent (templates, validation, timeline estimation)
- Step 2: Language Selection (15 languages, 4 categories)
- Step 3: Stack Selection (10 production-ready stack profiles)

**Features**:

- Multi-step wizard with progress tracking
- Template system with 10 professional templates
- Smart validation and conflict detection
- Real-time compatibility checking
- Search and filter functionality
- Responsive UI with Svelte

**API Integration**:

- Language service with 5 endpoints
- Stack profile service with 9 endpoints
- Offline fallback support
- TypeScript API clients

---

## [2.0.0] - 2025-11-05

### Added - NeuroForge Foundation

**Core Features**:

- LLM routing system
- Model selection and optimization
- Context integration with DataForge
- Performance tracking
- Domain-specific adapters

**Supported Providers**:

- Anthropic (Claude models)
- OpenAI (GPT models)
- Ollama (local models)

**Integration**:

- DataForge stateless connection
- AuthorForge LLM pipeline
- VibeForge inference support

---

## [1.0.0] - 2025-11-01

### Added - Initial Forge Ecosystem

**Products Launched**:

- DataForge: Core data engine
- NeuroForge: AI orchestration
- AuthorForge: Creative writing platform
- VibeForge: Project automation wizard

**Architecture**:

- Unified backend infrastructure
- Shared PostgreSQL database
- REST API communication
- Microservices pattern

**Documentation**:

- Product READMEs
- API documentation
- Setup guides
- Architecture overview

---

## Version History

- **6.0.0** (2026-02-24): Multi-Provider Pipeline Infrastructure
- **5.2.0** (2025-11-23): Learning Layer Integration
- **5.1.0** (2025-11-22): LLM Provider Integration
- **5.0.0** (2025-11-21): Authentication & Security
- **4.5.0** (2025-11-20): High Availability
- **4.0.0** (2025-11-15): DataForge Core Complete
- **3.0.0** (2025-11-10): VibeForge Wizard
- **2.0.0** (2025-11-05): NeuroForge Foundation
- **1.0.0** (2025-11-01): Initial Release

---

© 2025 Boswell Digital Solutions LLC. All rights reserved.

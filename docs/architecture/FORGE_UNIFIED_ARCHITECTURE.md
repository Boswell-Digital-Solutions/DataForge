# Forge Ecosystem - Unified Architecture

**Date**: December 10, 2025
**Status**: ✅ Production Architecture - Backend Services Decoupled from Frontend
**Architecture Pattern**: Microservices with Single Unified Frontend

---

## Executive Summary

The Forge Ecosystem follows a **clean microservices architecture** where:
- **Backend services are API-only** (no embedded frontends)
- **ForgeCommand provides the single unified UI** for all services
- **All services communicate via REST APIs** with proper authentication
- **Each service has a dedicated port** for clear separation of concerns

This architecture enables:
- 🔧 **Independent scaling** - Scale services independently based on load
- 🔄 **Technology flexibility** - Backend services can use different tech stacks
- 🛡️ **Security isolation** - Clear API boundaries with authentication
- 🚀 **Rapid development** - Teams can work on services independently
- 📊 **Unified UX** - Single desktop app for all functionality

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FORGECOMMAND (FRONTEND)                     │
│                    Tauri Desktop App - SvelteKit 5                  │
│                                                                     │
│  Routes:                                                            │
│  • /dataforge      → DataForge Analytics & Search                  │
│  • /neuroforge     → LLM Routing & Model Management                │
│  • /forgeagents    → Agent Orchestration & PAORT Sessions          │
│  • /rake           → Data Ingestion Pipelines                      │
│                                                                     │
│  Communication: Tauri invoke() → Backend REST APIs                 │
└──────────────┬──────────────┬──────────────┬──────────────┬────────┘
               │              │              │              │
               │ Port 8788    │ Port 8000    │ Port 8787    │ Port 8002
               ▼              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
       │ DataForge │  │NeuroForge │  │ForgeAgents│  │   Rake    │
       │  Backend  │  │  Backend  │  │  Backend  │  │  Backend  │
       │ (FastAPI) │  │ (FastAPI) │  │ (FastAPI) │  │ (FastAPI) │
       └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
             │              │              │              │
             │    ┌─────────┴──────┐       │              │
             │    │                 │       │              │
             ▼    ▼                 ▼       ▼              ▼
       ┌──────────────┐      ┌──────────────────┐  ┌──────────────┐
       │  PostgreSQL  │      │ Local LLM Models │  │  Telemetry   │
       │   + pgvector │      │ (Ollama) +       │  │   Database   │
       │   Database   │      │ Remote APIs      │  │  (SQLite)    │
       │              │      │ (Anthropic/      │  │              │
       │              │      │  OpenAI)         │  │              │
       └──────────────┘      └──────────────────┘  └──────────────┘
```

---

## Service Registry

### 1. DataForge (Port 8788)

**Purpose**: Vector search, data persistence, and SAS storage
**Technology**: FastAPI (Python), PostgreSQL + pgvector
**Responsibilities**:
- Vector embeddings storage and retrieval
- Semantic search with pgvector
- Document chunk management
- Context pack fetching for LLM pipelines
- Provenance tracking and lineage

**API Endpoints**:
- `GET /health` - Health check
- `POST /api/v1/context/fetch` - Fetch context packs
- `POST /api/v1/provenance/write` - Write provenance data
- `POST /api/v1/search` - Semantic vector search
- `GET /api/v1/metrics` - Service metrics

**Configuration**:
- Port: `8788`
- Database: PostgreSQL with pgvector extension
- Environment: [DataForge/.env](DataForge/.env)

**ForgeCommand Integration**: [ForgeCommand/src/routes/dataforge/+page.svelte](ForgeCommand/src/routes/dataforge/+page.svelte)

---

### 2. NeuroForge (Port 8000)

**Purpose**: LLM routing, model selection, and inference orchestration
**Technology**: FastAPI (Python), SQLAlchemy, Ollama, Anthropic/OpenAI SDKs
**Responsibilities**:
- 5-stage inference pipeline (Context → Prompt → Router → Evaluator → Post-processor)
- Champion model tracking with automatic promotion/demotion
- Model performance evaluation and comparison
- Multi-model routing (local Ollama + remote APIs)
- Token usage and cost tracking
- Circuit breakers and retry logic

**API Endpoints**:
- `GET /health` - Health check with dependency status
- `POST /api/v1/inference` - Run inference with automatic routing
- `GET /api/v1/models` - List available models
- `GET /api/v1/champion` - Get current champion model
- `POST /api/v1/evaluate` - Evaluate model performance
- `GET /api/v1/metrics` - Usage and cost metrics

**Configuration**:
- Port: `8000`
- Database: SQLite for telemetry (`neuroforge_telemetry.db`)
- Models: Local (Ollama) + Remote (Anthropic Claude, OpenAI GPT)
- Environment: [NeuroForge/neuroforge_backend/.env](NeuroForge/neuroforge_backend/.env)

**Security Features**:
- ✅ JWT authentication with python-jose
- ✅ Production SECRET_KEY validation (fails hard if default key detected)
- ✅ API key protection for admin endpoints
- ✅ Insecure x-user-id header disabled in production
- See: [NeuroForge/SECURITY_FIXES_APPLIED.md](NeuroForge/SECURITY_FIXES_APPLIED.md)

**ForgeCommand Integration**: [ForgeCommand/src/routes/neuroforge/+page.svelte](ForgeCommand/src/routes/neuroforge/+page.svelte)

---

### 3. ForgeAgents (Port 8787)

**Purpose**: 120-skill agent orchestration with PAORT pattern
**Technology**: FastAPI (Python), Agent runtime
**Responsibilities**:
- Agent skill registry (120+ skills across domains)
- PAORT pattern execution (Plan → Act → Observe → Reflect → Transition)
- Multi-agent coordination
- Session management and task tracking
- Skill execution with error handling

**API Endpoints**:
- `GET /health` - Health check
- `POST /api/v1/sessions` - Create agent session
- `POST /api/v1/execute` - Execute skill
- `GET /api/v1/skills` - List available skills
- `GET /api/v1/sessions/{id}` - Get session status

**Configuration**:
- Port: `8787`
- Skills: 120+ skills loaded on startup
- Environment: [forge_agents_bds_api/.env](forge_agents_bds_api/.env)

**ForgeCommand Integration**: [ForgeCommand/src/routes/forgeagents/+page.svelte](ForgeCommand/src/routes/forgeagents/+page.svelte)

---

### 4. Rake (Port 8002)

**Purpose**: Automated data ingestion pipelines
**Technology**: FastAPI (Python), OpenAI embeddings, BeautifulSoup
**Responsibilities**:
- 5-stage pipeline: FETCH → CLEAN → CHUNK → EMBED → STORE
- Multi-source data ingestion:
  - File uploads (PDF, TXT, DOCX, etc.)
  - URL web scraping
  - SEC EDGAR filings
  - API data fetching
  - Database queries
- Semantic chunking with overlap
- Embedding generation (OpenAI text-embedding-3-small)
- Storage to DataForge vector DB

**API Endpoints**:
- `GET /health` - Health check with dependency status
- `POST /api/v1/jobs` - Create ingestion job
- `GET /api/v1/jobs/{id}` - Get job status
- `GET /api/v1/jobs` - List all jobs
- `POST /api/v1/jobs/{id}/cancel` - Cancel job

**Configuration**:
- Port: `8002`
- Database: PostgreSQL for job tracking
- Embeddings: OpenAI API
- DataForge: `http://localhost:8788`
- Environment: [rake/.env](rake/.env)

**Pipeline Configuration**:
- Chunk size: 500 tokens (configurable)
- Chunk overlap: 50 tokens
- Max workers: 4 concurrent pipelines
- Retry attempts: 3 with exponential backoff

**ForgeCommand Integration**: [ForgeCommand/src/routes/rake/+page.svelte](ForgeCommand/src/routes/rake/+page.svelte)

---

## Frontend: ForgeCommand

**Purpose**: Single unified desktop application for all Forge services
**Technology**: Tauri 2.x, SvelteKit 5, TypeScript, Chart.js
**Port**: Development server runs on `5173` (Vite default)

### Routes and Responsibilities

| Route | Service | Description | Key Features |
|-------|---------|-------------|--------------|
| [/dataforge](ForgeCommand/src/routes/dataforge/+page.svelte) | DataForge | Vector search analytics | Search performance, cache hits, chunk counts |
| [/neuroforge](ForgeCommand/src/routes/neuroforge/+page.svelte) | NeuroForge | LLM usage & cost tracking | Token usage charts, cost over time, model comparison |
| [/forgeagents](ForgeCommand/src/routes/forgeagents/+page.svelte) | ForgeAgents | Agent orchestration dashboard | Session tracking, skill execution, PAORT monitoring |
| [/rake](ForgeCommand/src/routes/rake/+page.svelte) | Rake | Data ingestion pipelines | Job status, records processed, error tracking |

### Communication Pattern

ForgeCommand communicates with backend services using **Tauri's invoke() API**:

```typescript
// Example: Fetching metrics from NeuroForge
const [metricsData, costData] = await Promise.all([
    invoke<NeuroForgeMetrics>('get_neuroforge_metrics'),
    invoke<CostOverTime>('get_cost_over_time', { hours: 24 })
]);
```

The Tauri backend (Rust) handles HTTP requests to backend APIs and returns responses to the frontend.

---

## Service Dependencies

```
┌─────────────────┐
│  ForgeCommand   │ (Desktop UI - consumes all backend APIs)
└────────┬────────┘
         │
         ├─────────────────────────────────────────────────────┐
         │                                                     │
         ▼                                                     ▼
┌─────────────────┐                                   ┌─────────────────┐
│   NeuroForge    │──────────── Context ────────────▶│   DataForge     │
│  (LLM Router)   │◀─────── Embeddings ──────────────│ (Vector Store)  │
└────────┬────────┘                                   └────────▲────────┘
         │                                                     │
         │ Inference Requests                                 │
         │                                                     │
         ▼                                                     │
┌─────────────────┐                                           │
│  ForgeAgents    │                                           │
│ (Agent Runtime) │                                           │
└─────────────────┘                                           │
                                                              │
┌─────────────────┐                                           │
│      Rake       │──────── Store Embeddings ────────────────┘
│ (Data Pipeline) │
└─────────────────┘
```

### Dependency Matrix

| Service | Depends On | Purpose |
|---------|-----------|---------|
| **NeuroForge** | DataForge | Fetch context packs for LLM prompts |
| **NeuroForge** | Ollama (local) | Local model inference |
| **NeuroForge** | Anthropic/OpenAI | Remote model inference |
| **ForgeAgents** | NeuroForge | Execute LLM-powered skills |
| **ForgeAgents** | DataForge | Retrieve context for agent tasks |
| **Rake** | DataForge | Store processed embeddings |
| **Rake** | OpenAI | Generate embeddings |
| **ForgeCommand** | All backends | UI for all services |

---

## Communication Protocols

### 1. REST API Communication

All backend services expose REST APIs with:
- **JSON payloads** for request/response
- **CORS enabled** for localhost development
- **JWT authentication** (NeuroForge, ForgeAgents)
- **API key authentication** for admin endpoints
- **Correlation IDs** for distributed tracing

### 2. Tauri invoke() Bridge

ForgeCommand (frontend) → Tauri (Rust) → Backend Services (HTTP)

```
SvelteKit Component
       ↓
   invoke('get_metrics')
       ↓
   Tauri Command (Rust)
       ↓
HTTP GET http://localhost:8000/api/v1/metrics
       ↓
   NeuroForge Backend
       ↓
   JSON Response
       ↓
   Return to SvelteKit
```

### 3. Error Handling

All services implement:
- **Circuit breakers** (NeuroForge, Rake)
- **Retry logic** with exponential backoff
- **Graceful degradation** (fallback to cache when services unavailable)
- **Correlation ID tracking** for debugging

---

## Port Assignments

| Service | Port | Protocol | Status |
|---------|------|----------|--------|
| **DataForge** | 8788 | HTTP | ✅ Active |
| **NeuroForge** | 8000 | HTTP | ✅ Active |
| **ForgeAgents** | 8787 | HTTP | ✅ Active |
| **Rake** | 8002 | HTTP | ✅ Active |
| **ForgeCommand** (dev) | 5173 | HTTP | ✅ Active |
| **Ollama** (local LLM) | 11434 | HTTP | ⚙️ Optional |
| **PostgreSQL** | 5432 | TCP | ⚙️ DataForge DB |

---

## Environment Configuration

Each service has its own `.env` file:

### DataForge: [DataForge/.env](DataForge/.env)
```bash
PORT=8788
DATABASE_URL=postgresql://localhost:5432/forge
PGVECTOR_ENABLED=true
```

### NeuroForge: [NeuroForge/neuroforge_backend/.env](NeuroForge/neuroforge_backend/.env)
```bash
NEUROFORGE_ENVIRONMENT=development
SECRET_KEY=<secure-random-value>  # REQUIRED in production
NEUROFORGE_ADMIN_API_KEY=<admin-key>
DATAFORGE_API_KEY=<dataforge-key>
NEUROFORGE_ALLOW_X_USER_ID_HEADER=true  # MUST be false in production
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
```

### ForgeAgents: [forge_agents_bds_api/.env](forge_agents_bds_api/.env)
```bash
PORT=8787
NEUROFORGE_API_URL=http://localhost:8000
DATAFORGE_API_URL=http://localhost:8788
```

### Rake: [rake/.env](rake/.env)
```bash
RAKE_PORT=8002
DATAFORGE_BASE_URL=http://localhost:8788
OPENAI_API_KEY=<your-key>
DATABASE_URL=postgresql+asyncpg://localhost:5432/forge
```

---

## Authentication & Security

### NeuroForge Security Model

**JWT Authentication** (User Endpoints):
- Access tokens expire in 30 minutes (configurable)
- Tokens signed with HS256 algorithm
- User endpoints require `Authorization: Bearer <token>` header

**API Key Authentication** (Admin Endpoints):
- Admin endpoints require `X-API-Key` header
- Production enforces strict key validation
- Development mode more lenient (for testing)

**Production Security Hardening**:
1. ✅ **Fails hard** if default SECRET_KEY detected
2. ✅ **Blocks insecure authentication** (x-user-id header)
3. ✅ **Validates environment-specific requirements**
4. ✅ **Logs security events** for audit trail

See [NeuroForge/SECURITY_FIXES_APPLIED.md](NeuroForge/SECURITY_FIXES_APPLIED.md) for details.

### DataForge Security Model

- API key validation for write operations
- Read-only mode for anonymous queries
- CORS configured for localhost development

### ForgeAgents Security Model

- JWT token validation (delegates to NeuroForge)
- Skill execution sandboxing
- Rate limiting per session

### Rake Security Model

- JWT authentication for job creation
- OpenAI API key for embeddings
- DataForge API key for storage
- Read-only database query mode (configurable)

---

## Data Flow Examples

### Example 1: LLM Inference with Context

```
1. User submits query via ForgeCommand /neuroforge
       ↓
2. NeuroForge receives inference request
       ↓
3. NeuroForge fetches context from DataForge
       GET /api/v1/context/fetch (vector search for relevant chunks)
       ↓
4. NeuroForge builds prompt with context
       ↓
5. NeuroForge routes to best model (local Ollama or remote API)
       ↓
6. NeuroForge evaluates response quality
       ↓
7. NeuroForge updates champion model if needed
       ↓
8. Response returned to ForgeCommand
       ↓
9. ForgeCommand displays result to user
```

### Example 2: Data Ingestion Pipeline

```
1. User initiates document upload via ForgeCommand /rake
       ↓
2. Rake receives job creation request
       ↓
3. Rake FETCH stage: Downloads/reads document
       ↓
4. Rake CLEAN stage: Normalizes text, removes boilerplate
       ↓
5. Rake CHUNK stage: Splits into semantic segments (500 tokens, 50 overlap)
       ↓
6. Rake EMBED stage: Calls OpenAI API for embeddings
       ↓
7. Rake STORE stage: Sends to DataForge
       POST /api/v1/store (chunks + embeddings)
       ↓
8. DataForge persists to PostgreSQL + pgvector
       ↓
9. Job status updated, user notified via ForgeCommand
```

### Example 3: Agent Task Execution

```
1. User creates PAORT session via ForgeCommand /forgeagents
       ↓
2. ForgeAgents PLAN: Analyze task, select skills
       Uses NeuroForge for planning LLM call
       ↓
3. ForgeAgents ACT: Execute skills sequentially
       Each skill may call NeuroForge or DataForge
       ↓
4. ForgeAgents OBSERVE: Collect execution results
       ↓
5. ForgeAgents REFLECT: Evaluate outcomes
       Uses NeuroForge for reflection LLM call
       ↓
6. ForgeAgents TRANSITION: Determine next state
       (Continue loop or complete)
       ↓
7. Session results returned to ForgeCommand
```

---

## Deployment Considerations

### Development Mode

All services run locally with:
- **Auto-reload enabled** (FastAPI, SvelteKit)
- **Debug logging** (INFO level)
- **Lenient authentication** (development keys accepted)
- **CORS allow all** (localhost:*)

**Start all services:**
```bash
# Terminal 1: DataForge
cd DataForge && uvicorn app.main:app --port 8788 --reload

# Terminal 2: NeuroForge
cd NeuroForge/neuroforge_backend && uvicorn main:app --port 8000 --reload

# Terminal 3: ForgeAgents
cd forge_agents_bds_api && uvicorn app.main:app --port 8787 --reload

# Terminal 4: Rake
cd rake && uvicorn main:app --port 8002 --reload

# Terminal 5: ForgeCommand
cd ForgeCommand && pnpm tauri dev
```

### Production Mode

For production deployment:
1. ✅ Set `ENVIRONMENT=production` in all `.env` files
2. ✅ Generate secure SECRET_KEY values
3. ✅ Configure production database URLs
4. ✅ Set real API keys (OpenAI, Anthropic)
5. ✅ Disable insecure authentication methods
6. ✅ Enable HTTPS/TLS
7. ✅ Set up reverse proxy (nginx/Caddy)
8. ✅ Configure monitoring and logging
9. ✅ Set up database backups

**Production validation checklist**: See [NeuroForge/NEUROFORGE_DUE_DILIGENCE_REPORT.md](NeuroForge/NEUROFORGE_DUE_DILIGENCE_REPORT.md)

---

## Testing Strategy

### Unit Tests
- Each service has `/tests` directory
- Pytest for Python backends
- Vitest for SvelteKit frontend

### Integration Tests
- End-to-end tests for complete workflows
- Mock external dependencies (OpenAI, Anthropic)
- Test service-to-service communication

### Health Checks
All services expose `/health` endpoint:
```bash
curl http://localhost:8788/health  # DataForge
curl http://localhost:8000/health  # NeuroForge
curl http://localhost:8787/health  # ForgeAgents
curl http://localhost:8002/health  # Rake
```

---

## Monitoring & Observability

### Telemetry Collection

- **NeuroForge**: Token usage, cost tracking, model performance
- **DataForge**: Search performance, cache hit rates, chunk counts
- **ForgeAgents**: Skill execution times, session success rates
- **Rake**: Job throughput, error rates, pipeline stage latency

### Correlation IDs

All services support `X-Correlation-ID` header for distributed tracing across the entire request flow.

### Logs

Structured logging with:
- Timestamp
- Service name
- Log level
- Correlation ID
- Message

Example:
```
2025-12-10 10:30:45 - NeuroForge - INFO - [correlation_id: abc-123] Inference completed in 1.2s
2025-12-10 10:30:46 - DataForge - INFO - [correlation_id: abc-123] Context fetch: 5 chunks retrieved
```

---

## Scalability & Performance

### Horizontal Scaling

Each backend service can be scaled independently:
- Multiple NeuroForge instances behind load balancer (for high inference load)
- Multiple Rake workers (for parallel data ingestion)
- DataForge read replicas (for high-volume searches)

### Caching Strategy

- **NeuroForge**: Context pack caching (1 hour TTL)
- **DataForge**: Vector search result caching
- **Rake**: Embedding caching (avoid re-processing same content)

### Database Optimization

- **PostgreSQL connection pooling** (20 connections, 10 overflow)
- **pgvector indexes** for fast similarity search
- **Query optimization** with EXPLAIN ANALYZE

---

## Future Enhancements

### Phase 4 Roadmap (Planned)

1. **API Gateway**: Single entry point for all services with rate limiting
2. **Service Mesh**: Istio/Linkerd for advanced traffic management
3. **Redis Distributed Cache**: Shared cache across NeuroForge instances
4. **Message Queue**: RabbitMQ/Kafka for async job processing
5. **GraphQL Gateway**: Unified query language across services
6. **OpenTelemetry**: Distributed tracing and metrics
7. **Kubernetes Deployment**: Container orchestration for production
8. **Multi-tenancy**: Tenant isolation at database and API level

---

## Troubleshooting

### Service Won't Start

1. Check port conflicts: `lsof -i :8788`
2. Verify environment variables: `cat .env`
3. Check dependencies: `pip list` or `pnpm list`
4. Review logs: Check console output for errors

### Authentication Errors

- **NeuroForge**: Ensure SECRET_KEY is set correctly
- **Production**: Verify `allow_x_user_id_header=false`
- **JWT expired**: Tokens expire after 30 minutes by default

### Service Communication Failures

- Verify all services are running on correct ports
- Check CORS configuration in backend `.env` files
- Test with curl: `curl http://localhost:8000/health`

### Database Connection Issues

- Ensure PostgreSQL is running: `systemctl status postgresql`
- Verify DATABASE_URL is correct
- Check connection pool settings

---

## Contributors

- **Architecture**: Claude AI + Human oversight
- **Security Audit**: NeuroForge Due Diligence Report (Dec 10, 2025)
- **Implementation**: Forge Development Team

---

## Related Documentation

- [NeuroForge Due Diligence Report](NeuroForge/NEUROFORGE_DUE_DILIGENCE_REPORT.md)
- [NeuroForge Security Fixes](NeuroForge/SECURITY_FIXES_APPLIED.md)
- [ForgeCommand README](ForgeCommand/README.md)
- [Rake Quickstart](rake/QUICKSTART.md)
- [DataForge API Documentation](DataForge/README.md)

---

**Last Updated**: December 10, 2025
**Architecture Version**: 2.0 (Unified Backend-Frontend Split)
**Status**: ✅ Production Ready (Security Hardened)

# Forge Ecosystem - Claude Context

## Overview

The Forge Ecosystem is a suite of interconnected services for AI-powered content creation, data management, and automation. Each component lives in its own repository but they work together as a unified platform.

## Repository Structure

```
/home/charlieboswell/Forge/
├── ecosystem/                    # Backend services
│   ├── DataForge/               # THIS REPO - Core data API
│   │   ├── DataForge/           # FastAPI application
│   │   └── forge-telemetry/     # Shared telemetry library
│   ├── NeuroForge/              # AI/ML prompt management & learning
│   ├── Forge-Agents/            # Autonomous AI agents framework
│   └── rake/                    # Data pipeline & scheduling
│
├── apps/                         # Frontend applications
│   └── Forge-Command/           # Tauri desktop app (Svelte + Rust)
│       ├── scripts/             # Ecosystem orchestration scripts
│       └── docs/                # Ecosystem-wide documentation
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| DataForge | 8000 | Core data API, multi-tenant PostgreSQL |
| NeuroForge | 8001 | Prompt storage, learning layer |
| Forge-Agents | 8002 | Agent orchestration, skill registry |
| rake | 8003 | Data pipelines, scheduling |

## Key Technologies

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL with pgvector for embeddings
- **Frontend**: Svelte 5, TypeScript, Tauri (Rust)
- **Telemetry**: OpenTelemetry, Prometheus
- **Auth**: JWT tokens, multi-tenant isolation

## DataForge (This Repository)

DataForge is the central data hub providing:

- **Multi-tenant API**: Isolated data per tenant with row-level security
- **Domain Management**: Languages, genres, tropes, characters, worlds
- **Vector Search**: pgvector for semantic similarity
- **LLM Integration**: Support for multiple providers (OpenAI, Anthropic, etc.)

### Key Directories

```
DataForge/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── core/            # Config, security, database
├── alembic/             # Database migrations
├── tests/               # Pytest test suite
└── docs/                # DataForge-specific docs
```

### Running DataForge

```bash
cd DataForge/DataForge
python -m uvicorn app.main:app --reload --port 8000
```

## Inter-Service Communication

Services communicate via REST APIs with shared authentication:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ForgeCommand│────▶│  DataForge  │────▶│  NeuroForge │
│  (Frontend) │     │  (Port 8000)│     │  (Port 8001)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Forge-Agents │
                    │  (Port 8002)│
                    └─────────────┘
```

## Ecosystem Scripts (in Forge-Command/scripts/)

- `start_all_services.sh` - Start entire ecosystem
- `stop_all_services.sh` - Stop all services
- `verify_services.sh` - Health check all services
- `test_ecosystem.py` - Integration tests
- `test_e2e_auth.sh` - End-to-end auth flow tests

## Database Schema Highlights

### Core Tables
- `tenants` - Multi-tenant isolation
- `users` - User accounts with tenant association
- `languages` - Programming/natural languages
- `genres` - Content genres with hierarchies
- `tropes` - Story/content tropes
- `characters` - Character definitions
- `worlds` - World-building data

### Vector Tables
- `embeddings` - Semantic search vectors
- `prompt_templates` - Versioned prompt storage

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/dataforge
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Common Tasks

### Run Tests
```bash
cd DataForge/DataForge
pytest tests/ -v
```

### Run Migrations
```bash
cd DataForge/DataForge
alembic upgrade head
```

### Generate New Migration
```bash
alembic revision --autogenerate -m "description"
```

## Related Repositories

| Repo | GitHub | Purpose |
|------|--------|---------|
| DataForge | Boswecw/DataForge | Core data API (this repo) |
| NeuroForge | Boswecw/NeuroForge | AI/ML services |
| Forge-Agents | Boswecw/Forge-Agents | Agent framework |
| Forge-Command | Boswecw/Forge-Command | Desktop frontend |
| rake | Boswecw/rake | Data pipelines |

## Notes for Development

1. **Always use absolute imports** within each service
2. **Tenant isolation** is enforced at the database level
3. **API versioning** uses `/api/v1/` prefix
4. **All services** emit OpenTelemetry traces
5. **JWT tokens** are shared across services for SSO

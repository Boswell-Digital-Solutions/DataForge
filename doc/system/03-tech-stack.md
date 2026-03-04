# §3 — Technology Stack

## Runtime Environment

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Type hints mandatory, async/await throughout |
| FastAPI | 0.109.0 | ASGI framework; lifespan for startup/shutdown |
| uvicorn | 0.27.0 | ASGI worker server used behind Gunicorn in production |
| gunicorn | 21.2.0 | Production process manager for multiple Uvicorn workers |

## Databases

| Component | Version | Notes |
|-----------|---------|-------|
| PostgreSQL | 13+ | Primary relational store; JSONB, TSVECTOR, arrays |
| pgvector | 0.2.4 | Vector similarity extension; IVFFlat ANN index |
| Redis | 6+ | Cache, rate limiting, session data |

## ORM & Migrations

| Component | Version | Notes |
|-----------|---------|-------|
| SQLAlchemy | 2.0.36 | Core ORM; synchronous engine/session model in the current app |
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| Alembic | 1.13.1 | Schema migrations; 11 version files |

## Data Validation

| Component | Version | Notes |
|-----------|---------|-------|
| Pydantic | >= 2.10.0 | v2 API; all schemas use model_validator, field_validator |
| Jinja2 | (latest) | Admin UI template rendering only |

## Authentication & Cryptography

| Component | Version | Notes |
|-----------|---------|-------|
| python-jose | 3.3.0 | JWT creation and validation (HS256) |
| passlib | 1.7.4 | Password hashing abstraction |
| bcrypt | 4.1.2 | Bcrypt backend for passlib |
| cryptography | (latest) | AES-256 Fernet for field-level encryption |

## AI / Embedding Providers

| Component | Version | Role |
|-----------|---------|------|
| Voyage AI | 0.2.3 | Primary embedding provider (`voyage-large-2`, 1536-dim) |
| OpenAI | 1.10.0 | Fallback embedding provider |
| Cohere | (latest) | Secondary fallback embedding provider |

## Testing

| Component | Version | Notes |
|-----------|---------|-------|
| pytest | 7.4.3 | Test runner |
| pytest-asyncio | (latest) | Async test support |
| pytest-cov | (latest) | Coverage reporting |
| pytest-mock | (latest) | Mocking utilities |
| httpx | 0.26.0 | Async HTTP client for integration tests |

## HTTP & Networking

| Component | Version | Notes |
|-----------|---------|-------|
| httpx | 0.26.0 | Async HTTP client (tests + internal calls) |
| uvicorn | 0.27.0 | ASGI worker implementation |
| gunicorn | 21.2.0 | Multi-worker production entrypoint on Render |

## Observability

| Component | Notes |
|-----------|-------|
| Prometheus client | Metrics at `/metrics` |
| OpenTelemetry | Distributed tracing with correlation IDs |
| structlog / logging | Structured JSON logging |

## Optional / Load Testing

| Component | Notes |
|-----------|-------|
| k6 | Load testing (optional, not in requirements.txt) |
| Celery | Async task queue (DLQ integration) |

## Deployment Tools

| Component | Notes |
|-----------|-------|
| Docker | Container runtime |
| Docker Compose | Local dev orchestration |
| Kubernetes | Production target (StatefulSets for PG replication) |

## Dependency File

All pinned versions are in `requirements.txt` at the repository root. The `venv/` directory holds the local virtual environment and is not committed to version control.

Key install command:
```bash
pip install -r requirements.txt
```

Never install packages directly into the venv without updating `requirements.txt`. All version pins in this document must remain synchronized with `requirements.txt`.

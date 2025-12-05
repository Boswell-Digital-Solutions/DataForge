# RAKE BY FORGE - COMPLETE VSCODE CLAUDE IMPLEMENTATION PACKAGE
**Comprehensive Context & Implementation Guide**

---

**Project:** Rake - Automated Data Ingestion Pipeline  
**Version:** 1.0  
**Date:** December 3, 2025  
**Owner:** Charles Boswell (Boswell Digital Solutions LLC)  
**Purpose:** Complete context for VSCode Claude to implement Rake backend

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [Multi-Tenancy Strategy](#6-multi-tenancy-strategy)
7. [Telemetry System](#7-telemetry-system)
8. [Pipeline Specification](#8-pipeline-specification)
9. [Data Models](#9-data-models)
10. [API Endpoints](#10-api-endpoints)
11. [Service Integrations](#11-service-integrations)
12. [Configuration Management](#12-configuration-management)
13. [Error Handling Patterns](#13-error-handling-patterns)
14. [Testing Strategy](#14-testing-strategy)
15. [Implementation Phases](#15-implementation-phases)
16. [File-by-File Implementation](#16-file-by-file-implementation)
17. [Code Style Guidelines](#17-code-style-guidelines)
18. [Quality Checklist](#18-quality-checklist)

---

## 1. EXECUTIVE SUMMARY

### What is Rake?

Rake is the **automated data ingestion pipeline** for the Forge Ecosystem. It's a 5-stage pipeline that processes documents from various sources and prepares them for semantic search in DataForge.

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAKE PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. FETCH    →  Retrieve documents from sources                 │
│                 (APIs, web scraping, files, databases)          │
│                                                                 │
│  2. CLEAN    →  Extract text, remove noise, normalize           │
│                 (HTML cleanup, deduplication)                   │
│                                                                 │
│  3. CHUNK    →  Split into semantic segments                    │
│                 (sentence/paragraph boundaries)                 │
│                                                                 │
│  4. EMBED    →  Generate vector embeddings                      │
│                 (OpenAI, Anthropic, local models)               │
│                                                                 │
│  5. STORE    →  Save to DataForge with metadata                 │
│                 (pgvector storage, full-text search)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Differentiators

- **Greenfield Telemetry:** Built with monitoring from day one
- **Multi-Tenant Ready:** Tenant isolation via PostgreSQL RLS
- **Production-Ready:** Comprehensive error handling and retry logic
- **Scalable:** Async architecture with batch processing
- **Observable:** Full distributed tracing with correlation IDs

### Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                 │
│  • SEC EDGAR Filings  • Company Websites  • PDF Documents       │
│  • GitHub Repositories  • User Uploads                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Rake (Port 8002)                               │
│  5-Stage Pipeline + Telemetry Emission                          │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│      DataForge          │     │    Command Central      │
│      (Port 8001)        │     │    (Tauri/SvelteKit)    │
│                         │     │                         │
│  • Embeddings Storage   │     │  • Job Monitoring       │
│  • Semantic Search      │     │  • Analytics Dashboard  │
│  • Document Metadata    │     │  • Performance Metrics  │
└─────────────────────────┘     └─────────────────────────┘
```

---

## 2. ARCHITECTURE OVERVIEW

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    FORGE SAAS PLATFORM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │          Command Central (Admin & Customer Portal)        │  │
│  │          SvelteKit Frontend                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                  │
│                              │ REST API / WebSocket             │
│                              ▼                                  │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │   DataForge    │   NeuroForge   │      Rake      │          │
│  │   (FastAPI)    │   (FastAPI)    │   (FastAPI)    │          │
│  │   Port 8001    │   Port 8003    │   Port 8002    │          │
│  │                │                │                │          │
│  │  TENANT-AWARE: All queries include tenant_id     │          │
│  └────────────────┴────────────────┴────────────────┘          │
│                              ▲                                  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │      PostgreSQL + pgvector (Multi-Tenant Database)        │  │
│  │      Row-Level Security (RLS) Policies Enforced           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │      Redis (Caching, Rate Limiting, Job Queue)            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
1. Request arrives with JWT token
2. JWT decoded → tenant_id extracted
3. PostgreSQL session variable set: SET app.current_tenant = 'tenant-uuid'
4. Row-Level Security automatically filters all queries
5. Usage tracked for billing
6. Response returned with telemetry emitted
```

---

## 3. TECHNOLOGY STACK

### Core Framework
```
Python 3.11+
FastAPI 0.104+
Pydantic 2.5+
Uvicorn 0.24+
```

### Database
```
PostgreSQL 14+ with pgvector extension
SQLAlchemy 2.0+ (async)
asyncpg for async PostgreSQL driver
psycopg2-binary for sync operations
```

### API Clients
```
httpx for async HTTP requests
aiohttp for WebSocket and streaming
openai SDK for embeddings
anthropic SDK for future model support
```

### Data Processing
```
pdfplumber for PDF extraction
beautifulsoup4 for HTML cleaning
tiktoken for token counting (cl100k_base encoding)
```

### Task Queue & Scheduling
```
APScheduler for cron-like scheduling
Redis for job queue (optional, future)
Celery (optional, for distributed workers)
```

### Testing
```
pytest for unit tests
pytest-asyncio for async tests
pytest-cov for coverage
httpx for API testing
```

### Utilities
```
python-dotenv for environment variables
tenacity for retry logic
structlog or standard logging
```

---

## 4. PROJECT STRUCTURE

```
rake/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management (Pydantic Settings)
├── scheduler.py               # Job scheduling (APScheduler)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── Dockerfile                # Container configuration
├── README.md                 # Project documentation
│
├── api/                      # API layer
│   ├── __init__.py
│   ├── routes.py             # API endpoints
│   ├── dependencies.py       # FastAPI dependencies
│   └── websocket.py          # WebSocket for live updates
│
├── auth/                     # Authentication
│   ├── __init__.py
│   ├── jwt_handler.py        # JWT utilities
│   └── tenant_context.py     # Tenant context management
│
├── sources/                  # Data source adapters
│   ├── __init__.py
│   ├── base.py               # Abstract base class
│   ├── file_upload.py        # PDF/document file processing
│   ├── sec_edgar.py          # SEC EDGAR filings (future)
│   ├── web_scraper.py        # Generic web scraping (future)
│   └── github_crawler.py     # GitHub repository ingestion (future)
│
├── pipeline/                 # 5-stage pipeline
│   ├── __init__.py
│   ├── orchestrator.py       # Pipeline coordination
│   ├── fetch.py              # Stage 1: Fetch
│   ├── clean.py              # Stage 2: Clean
│   ├── chunk.py              # Stage 3: Chunk
│   ├── embed.py              # Stage 4: Embed
│   └── store.py              # Stage 5: Store
│
├── services/                 # External service clients
│   ├── __init__.py
│   ├── dataforge_client.py   # DataForge API client
│   ├── embedding_service.py  # Embedding generation
│   ├── telemetry_client.py   # Telemetry emission
│   └── cost_tracker.py       # API cost tracking
│
├── models/                   # Pydantic data models
│   ├── __init__.py
│   ├── document.py           # Document representations
│   ├── job.py                # Job state models
│   ├── chunk.py              # Chunk representation
│   └── events.py             # Telemetry event models
│
├── database/                 # Database utilities
│   ├── __init__.py
│   ├── connection.py         # Connection pool management
│   └── queries.py            # Common SQL queries
│
├── utils/                    # Utilities
│   ├── __init__.py
│   ├── text_processing.py    # Text cleaning helpers
│   ├── retry.py              # Retry logic
│   └── logging.py            # Structured logging
│
└── tests/                    # Test suite
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures
    ├── unit/
    │   ├── test_clean.py
    │   ├── test_chunk.py
    │   └── test_models.py
    ├── integration/
    │   ├── test_pipeline.py
    │   └── test_api.py
    └── fixtures/
        └── sample_documents/
```

---

## 5. DATABASE SCHEMA

### Core Tables for Rake

```sql
-- Jobs (Rake pipeline jobs)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'partial', 'cancelled')),
    phase TEXT CHECK (phase IN ('fetch', 'clean', 'chunk', 'embed', 'store')),
    scheduled BOOLEAN DEFAULT false,
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    -- Statistics
    docs_fetched INTEGER DEFAULT 0,
    docs_processed INTEGER DEFAULT 0,
    docs_stored INTEGER DEFAULT 0,
    tokens_processed BIGINT DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms REAL,
    phase_timings JSONB DEFAULT '{}'::jsonb,
    
    -- Error handling
    error TEXT,
    failed_stage TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    correlation_id UUID,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enable Row-Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_jobs ON jobs
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true)::UUID);

-- Indexes
CREATE INDEX idx_jobs_tenant ON jobs(tenant_id);
CREATE INDEX idx_jobs_status ON jobs(tenant_id, status);
CREATE INDEX idx_jobs_source ON jobs(tenant_id, source);
CREATE INDEX idx_jobs_created ON jobs(tenant_id, created_at DESC);
CREATE INDEX idx_jobs_correlation ON jobs(correlation_id) WHERE correlation_id IS NOT NULL;
```

```sql
-- Schedules
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    source TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    
    -- Execution tracking
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Notifications
    notify_on_failure BOOLEAN DEFAULT true,
    notify_emails TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(tenant_id, source)
);

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_schedules ON schedules
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true)::UUID);
```

```sql
-- Telemetry Events
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    
    service TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    
    correlation_id UUID,
    trace_id TEXT,
    
    message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_tenant ON events(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_service ON events(service, timestamp DESC);
CREATE INDEX idx_events_correlation ON events(correlation_id) WHERE correlation_id IS NOT NULL;
CREATE INDEX idx_events_severity ON events(severity, timestamp DESC) 
    WHERE severity IN ('error', 'critical');

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_events ON events
    FOR ALL
    USING (
        tenant_id IS NULL  -- Platform events visible to admins only
        OR tenant_id = current_setting('app.current_tenant', true)::UUID
    );
```

```sql
-- API Costs (track external API usage)
CREATE TABLE api_costs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    service TEXT NOT NULL,  -- 'openai', 'anthropic', etc.
    model TEXT NOT NULL,
    operation TEXT NOT NULL,  -- 'embedding', 'completion', 'chat'
    
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL,
    
    job_id TEXT REFERENCES jobs(id),
    request_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_costs_tenant ON api_costs(tenant_id);
CREATE INDEX idx_api_costs_timestamp ON api_costs(tenant_id, timestamp DESC);
CREATE INDEX idx_api_costs_job ON api_costs(job_id) WHERE job_id IS NOT NULL;

ALTER TABLE api_costs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_costs ON api_costs
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true)::UUID);
```

### Helper Functions

```sql
-- Function to set tenant context (call at start of each request)
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant', p_tenant_id::TEXT, false);
END;
$$ LANGUAGE plpgsql;

-- Function to get current tenant
CREATE OR REPLACE FUNCTION get_current_tenant()
RETURNS UUID AS $$
BEGIN
    RETURN current_setting('app.current_tenant', true)::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

---

## 6. MULTI-TENANCY STRATEGY

### Tenant Context Flow

```python
# 1. Middleware extracts tenant_id from JWT
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    if token:
        payload = decode_jwt(token)
        request.state.tenant_id = payload.get("tenant_id")
    return await call_next(request)

# 2. Database connection sets tenant context
async def get_db_with_tenant(tenant_id: UUID) -> AsyncConnection:
    conn = await pool.acquire()
    await conn.execute(f"SELECT set_tenant_context('{tenant_id}')")
    return conn

# 3. All queries automatically filtered by RLS
async def get_jobs(conn: AsyncConnection):
    # No need for WHERE tenant_id = ... 
    # RLS handles it automatically!
    return await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
```

### Tenant Context Dataclass

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class TenantContext:
    tenant_id: UUID
    user_id: UUID
    role: str
    
    def __post_init__(self):
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
```

---

## 7. TELEMETRY SYSTEM

### Event Types

| Event Type | When Emitted | Severity |
|------------|--------------|----------|
| `job_started` | Beginning of pipeline job | info |
| `job_completed` | Successful completion | info |
| `job_failed` | Job failure at any stage | error |
| `phase_completed` | After each pipeline stage | info |
| `freshness_check` | Periodic data freshness report | info |

### Event Schemas

#### Job Started
```python
{
    "service": "rake",
    "event_type": "job_started",
    "severity": "info",
    "correlation_id": "uuid",
    "metadata": {
        "job_id": "rake-2025-12-03-001",
        "source": "sec_filings",
        "source_type": "api",
        "scheduled": True,
        "priority": "normal"
    }
}
```

#### Job Completed
```python
{
    "service": "rake",
    "event_type": "job_completed",
    "severity": "info",
    "correlation_id": "uuid",
    "metadata": {
        "job_id": "rake-2025-12-03-001",
        "source": "sec_filings",
        "status": "success"
    },
    "metrics": {
        "duration_ms": 138432,
        "docs_fetched": 184,
        "docs_processed": 184,
        "docs_stored": 184,
        "tokens_processed": 920000,
        "embeddings_created": 920,
        "phase_timings": {
            "fetch_ms": 45000,
            "clean_ms": 12000,
            "chunk_ms": 8000,
            "embed_ms": 52000,
            "store_ms": 21432
        }
    }
}
```

#### Job Failed
```python
{
    "service": "rake",
    "event_type": "job_failed",
    "severity": "error",
    "correlation_id": "uuid",
    "metadata": {
        "job_id": "rake-2025-12-03-001",
        "source": "sec_filings",
        "failed_stage": "fetch",
        "error": "Connection timeout after 60s",
        "retry_count": 3,
        "will_retry": False
    }
}
```

#### Phase Completed
```python
{
    "service": "rake",
    "event_type": "phase_completed",
    "severity": "info",
    "correlation_id": "uuid",
    "metadata": {
        "job_id": "rake-2025-12-03-001",
        "phase": "fetch",
        "source": "sec_filings"
    },
    "metrics": {
        "duration_ms": 45000,
        "items_processed": 184,
        "bytes_downloaded": 15728640
    }
}
```

### Telemetry Client Pattern

```python
class RakeTelemetryClient:
    """Telemetry client for Rake service."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.logger = logging.getLogger(__name__)
    
    async def emit(self, event: Dict[str, Any]) -> None:
        """Emit telemetry event to database."""
        event["timestamp"] = datetime.utcnow().isoformat()
        
        async with self._get_connection() as conn:
            await conn.execute("""
                INSERT INTO events (
                    tenant_id, service, event_type, severity,
                    correlation_id, metadata, metrics, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                event.get("tenant_id"),
                event["service"],
                event["event_type"],
                event["severity"],
                event.get("correlation_id"),
                json.dumps(event.get("metadata", {})),
                json.dumps(event.get("metrics", {})),
                event["timestamp"]
            )
        
        self.logger.info(f"Emitted {event['event_type']}", extra=event)
```

---

## 8. PIPELINE SPECIFICATION

### Stage 1: FETCH

**Purpose:** Retrieve documents from configured source

**Input:** Source name, correlation ID  
**Output:** List of RawDocument objects

**Responsibilities:**
- Route to appropriate source adapter
- Handle connection errors with retry
- Track bytes downloaded
- Emit phase_completed event

**Source Adapters:**
| Adapter | Source Type | Priority |
|---------|-------------|----------|
| `FileUploadAdapter` | PDF files | V1 (implement first) |
| `SecEdgarAdapter` | SEC EDGAR API | V2 |
| `WebScraperAdapter` | Generic web pages | V2 |
| `GitHubCrawlerAdapter` | GitHub repos | V3 |

### Stage 2: CLEAN

**Purpose:** Clean and normalize fetched documents

**Input:** List of RawDocument objects  
**Output:** List of CleanedDocument objects

**Operations:**
- Remove excessive whitespace
- Strip HTML tags
- Normalize line breaks
- Remove special characters (keep alphanumeric + basic punctuation)
- Filter documents with < 50 chars
- Calculate word count

**Text Cleaning Regex:**
```python
# Remove HTML tags
content = re.sub(r'<[^>]+>', '', content)

# Normalize whitespace
content = re.sub(r'\s+', ' ', content)

# Remove special characters (keep alphanumeric, spaces, basic punctuation)
content = re.sub(r'[^\w\s.,!?;:\'"()-]', '', content)

# Strip and normalize
content = content.strip()
```

### Stage 3: CHUNK

**Purpose:** Split documents into semantic segments for embedding

**Input:** List of CleanedDocument objects  
**Output:** List of Chunk objects

**Chunking Strategy:**
1. Split on paragraph boundaries (double newline)
2. If paragraph > 1000 tokens, split on sentence boundaries
3. If sentence > 1000 tokens, split on word boundaries
4. Target chunk size: 500-1000 tokens

**Token Counting:**
```python
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(encoding.encode(text))
```

### Stage 4: EMBED

**Purpose:** Generate vector embeddings for chunks

**Input:** List of Chunk objects  
**Output:** List of Embedding objects

**Configuration:**
| Model | Dimensions | Cost per 1M tokens |
|-------|------------|-------------------|
| text-embedding-3-small | 1536 | $0.02 |
| text-embedding-3-large | 3072 | $0.13 |

**Batching:**
- Process 100 chunks per batch
- Rate limit: 3000 RPM for OpenAI
- Retry failed batches with exponential backoff

**Embedding Request:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

response = await client.embeddings.create(
    model="text-embedding-3-small",
    input=texts,  # List of up to 100 texts
    encoding_format="float"
)

vectors = [item.embedding for item in response.data]
```

### Stage 5: STORE

**Purpose:** Persist embeddings to DataForge

**Input:** List of Embedding objects, source name  
**Output:** Storage metrics

**DataForge API Call:**
```python
# POST /api/v1/embeddings/batch
payload = {
    "collection": f"{source}_embeddings",
    "source": source,
    "embeddings": [
        {
            "id": emb.id,
            "chunk_id": emb.chunk_id,
            "vector": emb.vector,
            "metadata": emb.metadata
        }
        for emb in embeddings
    ]
}
```

---

## 9. DATA MODELS

### RawDocument
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class RawDocument(BaseModel):
    """Raw document from fetch stage."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    url: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc-001",
                "source": "file_upload",
                "content": "Document content here...",
                "metadata": {"filename": "report.pdf", "pages": 10}
            }
        }
```

### CleanedDocument
```python
class CleanedDocument(BaseModel):
    """Cleaned document from clean stage."""
    
    id: str
    source: str
    content: str  # Cleaned text
    metadata: Dict[str, Any] = Field(default_factory=dict)
    word_count: int
    cleaned_at: datetime = Field(default_factory=datetime.utcnow)
```

### Chunk
```python
class Chunk(BaseModel):
    """Text chunk from chunk stage."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    position: int  # Position in document (0-indexed)
    token_count: int
```

### Embedding
```python
from typing import List

class Embedding(BaseModel):
    """Embedding from embed stage."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chunk_id: str
    vector: List[float]
    model: str = "text-embedding-3-small"
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Job
```python
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"

class JobPhase(str, Enum):
    FETCH = "fetch"
    CLEAN = "clean"
    CHUNK = "chunk"
    EMBED = "embed"
    STORE = "store"

class Job(BaseModel):
    """Job state model."""
    
    id: str
    tenant_id: str
    source: str
    status: JobStatus
    phase: Optional[JobPhase] = None
    scheduled: bool = False
    
    # Statistics
    docs_fetched: int = 0
    docs_processed: int = 0
    docs_stored: int = 0
    tokens_processed: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    phase_timings: Dict[str, float] = Field(default_factory=dict)
    
    # Error handling
    error: Optional[str] = None
    failed_stage: Optional[str] = None
    retry_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
```

---

## 10. API ENDPOINTS

### Health & Status
```
GET /health
Response: {"status": "healthy", "service": "rake", "timestamp": "..."}

GET /api/v1/status
Response: {
    "service": "rake",
    "version": "1.0.0",
    "active_jobs": 2,
    "scheduler_running": true
}
```

### Jobs
```
POST /api/v1/jobs
Body: {"source": "file_upload", "priority": "normal"}
Response: {"job_id": "rake-...", "status": "pending"}

GET /api/v1/jobs
Query: ?status=running&source=sec_filings&limit=50
Response: [{"job_id": "...", "status": "...", ...}]

GET /api/v1/jobs/{job_id}
Response: {"job_id": "...", "status": "...", "phase_timings": {...}}

DELETE /api/v1/jobs/{job_id}
Response: {"cancelled": true}
```

### Schedules
```
GET /api/v1/schedules
Response: [{"source": "sec_filings", "cron": "0 1 * * *", "enabled": true}]

PUT /api/v1/schedules/{source}
Body: {"cron_expression": "0 */6 * * *", "enabled": true}
Response: {"updated": true}

POST /api/v1/schedules/{source}/trigger
Response: {"job_id": "rake-..."}
```

### Analytics
```
GET /api/v1/analytics/summary
Query: ?days=7
Response: {
    "total_jobs": 42,
    "success_rate": 0.95,
    "docs_processed": 1840,
    "avg_duration_ms": 45000
}

GET /api/v1/analytics/sources
Response: {
    "sec_filings": {"last_run": "...", "docs_today": 100},
    "company_website": {"last_run": "...", "docs_today": 50}
}
```

---

## 11. SERVICE INTEGRATIONS

### DataForge Client
```python
class DataForgeClient:
    """Client for DataForge API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def store_embeddings(
        self, 
        embeddings: List[Embedding],
        collection: str,
        source: str
    ) -> Dict:
        """Store embeddings in DataForge."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "collection": collection,
            "source": source,
            "embeddings": [emb.model_dump() for emb in embeddings]
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/embeddings/batch",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
```

### Embedding Service
```python
class EmbeddingService:
    """Service for generating embeddings."""
    
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "text-embedding-3-small"
        self.batch_size = 100
    
    async def generate_embeddings(
        self, 
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
                encoding_format="float"
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def calculate_cost(self, total_tokens: int) -> float:
        """Calculate cost for embedding generation."""
        # text-embedding-3-small: $0.02 per 1M tokens
        return (total_tokens / 1_000_000) * 0.02
```

---

## 12. CONFIGURATION MANAGEMENT

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://localhost:5432/forge

# Services
DATAFORGE_BASE_URL=http://localhost:8001
DATAFORGE_API_KEY=optional-api-key

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Rake Configuration
RAKE_PORT=8002
RAKE_HOST=0.0.0.0
LOG_LEVEL=INFO
MAX_WORKERS=4
RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5.0

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_EMBEDDINGS_PER_MINUTE=3000

# Scheduling
SCHEDULER_ENABLED=true
DEFAULT_TIMEZONE=UTC
```

### Pydantic Settings
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings from environment."""
    
    # Database
    database_url: str
    
    # Services
    dataforge_base_url: str = "http://localhost:8001"
    dataforge_api_key: Optional[str] = None
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Rake
    rake_port: int = 8002
    rake_host: str = "0.0.0.0"
    log_level: str = "INFO"
    max_workers: int = 4
    retry_attempts: int = 3
    retry_delay_seconds: float = 5.0
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_embeddings_per_minute: int = 3000
    
    # Scheduling
    scheduler_enabled: bool = True
    default_timezone: str = "UTC"
    
    @property
    def has_openai(self) -> bool:
        return self.openai_api_key is not None
    
    @property
    def has_anthropic(self) -> bool:
        return self.anthropic_api_key is not None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 13. ERROR HANDLING PATTERNS

### Retry Decorator
```python
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type
)
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.HTTPError, ConnectionError))
)
async def api_call_with_retry():
    """API call with automatic retry on transient failures."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

### Exception Hierarchy
```python
class RakeError(Exception):
    """Base exception for Rake errors."""
    pass

class FetchError(RakeError):
    """Error during fetch stage."""
    pass

class CleanError(RakeError):
    """Error during clean stage."""
    pass

class ChunkError(RakeError):
    """Error during chunk stage."""
    pass

class EmbedError(RakeError):
    """Error during embed stage."""
    pass

class StoreError(RakeError):
    """Error during store stage."""
    pass

class QuotaExceededError(RakeError):
    """Tenant quota exceeded."""
    pass

class RateLimitError(RakeError):
    """Rate limit exceeded."""
    pass
```

### Error Handling in Pipeline
```python
async def run_job(source: str, correlation_id: str) -> Dict:
    """Execute pipeline with comprehensive error handling."""
    job_id = generate_job_id(source)
    start_time = time.time()
    
    try:
        await telemetry.emit_job_started(job_id, source, correlation_id)
        
        # Stage 1: Fetch
        try:
            raw_docs = await fetch_stage(source, correlation_id)
        except Exception as e:
            raise FetchError(f"Fetch failed: {e}") from e
        
        # Continue with other stages...
        
        # Success
        duration_ms = (time.time() - start_time) * 1000
        await telemetry.emit_job_completed(job_id, source, correlation_id, duration_ms, metrics)
        
        return {"job_id": job_id, "status": "success", "duration_ms": duration_ms}
        
    except RakeError as e:
        # Known error - determine failed stage
        failed_stage = e.__class__.__name__.replace("Error", "").lower()
        await telemetry.emit_job_failed(job_id, source, correlation_id, failed_stage, str(e))
        raise
        
    except Exception as e:
        # Unknown error
        await telemetry.emit_job_failed(job_id, source, correlation_id, "unknown", str(e))
        raise RakeError(f"Unexpected error: {e}") from e
```

---

## 14. TESTING STRATEGY

### Unit Test Structure
```python
# tests/unit/test_clean.py
import pytest
from pipeline.clean import clean_stage
from models.document import RawDocument
from datetime import datetime

@pytest.fixture
def sample_raw_document():
    return RawDocument(
        id="test-001",
        source="test",
        content="  <p>Hello   World</p>  \n\n  ",
        metadata={"filename": "test.pdf"},
        fetched_at=datetime.utcnow()
    )

@pytest.mark.asyncio
async def test_clean_removes_html_tags(sample_raw_document):
    """Clean stage should remove HTML tags."""
    result = await clean_stage([sample_raw_document], "test-correlation")
    assert "<p>" not in result[0].content
    assert "</p>" not in result[0].content

@pytest.mark.asyncio
async def test_clean_normalizes_whitespace(sample_raw_document):
    """Clean stage should normalize whitespace."""
    result = await clean_stage([sample_raw_document], "test-correlation")
    assert "   " not in result[0].content

@pytest.mark.asyncio
async def test_clean_filters_short_documents():
    """Clean stage should filter documents with < 50 chars."""
    short_doc = RawDocument(
        id="short-001",
        source="test",
        content="Too short",
        metadata={},
        fetched_at=datetime.utcnow()
    )
    result = await clean_stage([short_doc], "test-correlation")
    assert len(result) == 0
```

### Integration Test Structure
```python
# tests/integration/test_pipeline.py
import pytest
from pipeline.orchestrator import orchestrator

@pytest.fixture
async def setup_test_data(db_connection):
    """Setup test documents in database."""
    # Create test tenant
    # Create test documents
    yield
    # Cleanup

@pytest.mark.asyncio
async def test_full_pipeline_execution(setup_test_data):
    """Test complete pipeline from fetch to store."""
    result = await orchestrator.run_job("test_source", scheduled=False)
    
    assert result["status"] == "success"
    assert result["documents_processed"] > 0
    assert "duration_ms" in result
    assert all(phase in result["phase_timings"] for phase in 
               ["fetch_ms", "clean_ms", "chunk_ms", "embed_ms", "store_ms"])

@pytest.mark.asyncio
async def test_pipeline_emits_telemetry(setup_test_data, db_connection):
    """Verify telemetry events are emitted."""
    correlation_id = await orchestrator.run_job("test_source", scheduled=False)
    
    # Check for events in database
    events = await db_connection.fetch(
        "SELECT * FROM events WHERE correlation_id = $1",
        correlation_id
    )
    
    event_types = {e["event_type"] for e in events}
    assert "job_started" in event_types
    assert "job_completed" in event_types
```

### Test Configuration
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for embedding tests."""
    mock = AsyncMock()
    mock.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    return mock

@pytest.fixture
def mock_telemetry():
    """Mock telemetry client."""
    return AsyncMock()
```

---

## 15. IMPLEMENTATION PHASES

### Phase 1: Foundation (Days 1-2)
**Goal:** Basic application structure

| File | Priority | Description |
|------|----------|-------------|
| `main.py` | High | FastAPI entry point |
| `config.py` | High | Configuration management |
| `requirements.txt` | High | Dependencies |
| `.env.example` | High | Environment template |
| `services/telemetry_client.py` | High | Telemetry emission |

**Deliverables:**
- FastAPI app running on port 8002
- Health endpoint functional
- Configuration loading from .env
- Telemetry events writing to database

### Phase 2: Data Models & Source Adapter (Days 3-4)
**Goal:** Document models and first source adapter

| File | Priority | Description |
|------|----------|-------------|
| `models/document.py` | High | All Pydantic models |
| `sources/base.py` | High | Abstract adapter base |
| `sources/file_upload.py` | High | PDF file processing |

**Deliverables:**
- All data models defined and validated
- FileUploadAdapter reads PDFs from directory
- Basic text extraction working

### Phase 3: Pipeline Stages (Days 5-7)
**Goal:** Complete 5-stage pipeline

| File | Priority | Description |
|------|----------|-------------|
| `pipeline/fetch.py` | High | Stage 1 |
| `pipeline/clean.py` | High | Stage 2 |
| `pipeline/chunk.py` | High | Stage 3 |
| `pipeline/embed.py` | High | Stage 4 |
| `pipeline/store.py` | High | Stage 5 |
| `pipeline/orchestrator.py` | High | Pipeline coordination |

**Deliverables:**
- Each stage processes data correctly
- Telemetry emitted at each phase
- Orchestrator coordinates full pipeline

### Phase 4: Services & Integration (Days 8-9)
**Goal:** External service integration

| File | Priority | Description |
|------|----------|-------------|
| `services/dataforge_client.py` | High | DataForge API |
| `services/embedding_service.py` | High | OpenAI embeddings |
| `services/cost_tracker.py` | Medium | API cost tracking |
| `api/routes.py` | High | REST API endpoints |

**Deliverables:**
- Embeddings stored in DataForge
- API costs tracked
- REST API functional

### Phase 5: Scheduling & Polish (Day 10)
**Goal:** Automation and refinement

| File | Priority | Description |
|------|----------|-------------|
| `scheduler.py` | Medium | APScheduler integration |
| `api/websocket.py` | Low | Live job updates |
| Tests | High | Unit and integration tests |

**Deliverables:**
- Scheduled jobs running
- 80%+ test coverage
- Production-ready code

---

## 16. FILE-BY-FILE IMPLEMENTATION

### File 1: main.py

**Requirements:**
- FastAPI application with CORS
- Health check endpoint
- Startup/shutdown events
- Uvicorn serving

**Implementation:**
```python
"""
Rake - Data Ingestion Pipeline
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Rake starting on port {settings.rake_port}")
    # TODO: Initialize database connection pool
    # TODO: Initialize telemetry client
    # TODO: Start scheduler if enabled
    yield
    # Shutdown
    logger.info("Rake shutting down")
    # TODO: Close database connections
    # TODO: Stop scheduler


app = FastAPI(
    title="Rake - Data Ingestion Pipeline",
    description="Automated document ingestion for Forge Ecosystem",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "rake",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/status")
async def get_status():
    """Get service status."""
    return {
        "service": "rake",
        "version": "1.0.0",
        "scheduler_running": settings.scheduler_enabled,
        "active_jobs": 0  # TODO: Get from database
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.rake_host,
        port=settings.rake_port,
        reload=True  # Disable in production
    )
```

### File 2: config.py

**Requirements:**
- Pydantic BaseSettings
- Environment variable loading
- Validation

**Implementation:**
```python
"""
Configuration management for Rake.
Uses Pydantic Settings for environment variable loading.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    
    # DataForge
    dataforge_base_url: str = "http://localhost:8001"
    dataforge_api_key: Optional[str] = None
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Rake Configuration
    rake_port: int = 8002
    rake_host: str = "0.0.0.0"
    log_level: str = "INFO"
    max_workers: int = 4
    retry_attempts: int = 3
    retry_delay_seconds: float = 5.0
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_embeddings_per_minute: int = 3000
    
    # Scheduling
    scheduler_enabled: bool = True
    default_timezone: str = "UTC"
    
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key)
    
    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.anthropic_api_key)
    
    def __repr__(self) -> str:
        """Safe representation without exposing secrets."""
        return (
            f"Settings("
            f"database_url='***', "
            f"dataforge_base_url='{self.dataforge_base_url}', "
            f"rake_port={self.rake_port}, "
            f"has_openai={self.has_openai}, "
            f"has_anthropic={self.has_anthropic})"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
```

### [Continue with remaining files...]

---

## 17. CODE STYLE GUIDELINES

### Import Organization
```python
# Standard library
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import uuid4

# Third-party
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

# Local
from config import settings
from models.document import RawDocument
from services.telemetry_client import telemetry
```

### Logging Format
```python
logger = logging.getLogger(__name__)

# Info level for major operations
logger.info(
    "Starting fetch stage",
    extra={"correlation_id": correlation_id, "source": source}
)

# Debug level for details
logger.debug(
    f"Processing document {doc_id}",
    extra={"correlation_id": correlation_id}
)

# Error level for failures
logger.error(
    f"Fetch failed: {error}",
    extra={"correlation_id": correlation_id, "source": source},
    exc_info=True
)
```

### Docstring Format (Google Style)
```python
async def fetch_stage(source: str, correlation_id: str) -> List[RawDocument]:
    """Fetch documents from the specified source.
    
    This is Stage 1 of the Rake pipeline. It routes to the appropriate
    source adapter based on the source name and retrieves raw documents.
    
    Args:
        source: Source identifier (e.g., 'file_upload', 'sec_filings')
        correlation_id: UUID for distributed tracing
        
    Returns:
        List of RawDocument objects containing fetched content
        
    Raises:
        ValueError: If source is unknown
        FetchError: If fetch operation fails
        
    Example:
        >>> correlation_id = str(uuid4())
        >>> docs = await fetch_stage("file_upload", correlation_id)
        >>> print(f"Fetched {len(docs)} documents")
    """
```

### Type Hints
```python
# Always use type hints
def process_document(
    document: RawDocument,
    options: Optional[Dict[str, Any]] = None
) -> CleanedDocument:
    ...

# Use List, Dict, Optional from typing
from typing import List, Dict, Optional, Any, Tuple

# Use Union for multiple types
from typing import Union
Value = Union[str, int, float]
```

---

## 18. QUALITY CHECKLIST

### Before Each File Commit

- [ ] All functions have type hints
- [ ] All public functions have docstrings (Google style)
- [ ] Error handling with try/except
- [ ] Logging at appropriate levels
- [ ] Telemetry events emitted where applicable
- [ ] No hardcoded secrets
- [ ] Async/await used correctly
- [ ] Imports organized properly

### Before Integration

- [ ] Unit tests written (80%+ coverage)
- [ ] Integration tests passing
- [ ] Telemetry verified in database
- [ ] Error scenarios tested
- [ ] Performance acceptable

### Before Deployment

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Environment variables documented
- [ ] Database migrations applied
- [ ] Health endpoint working
- [ ] Logs reviewed for errors

---

## CRITICAL REMINDERS

### DO:
✅ Emit telemetry for EVERY operation  
✅ Include correlation_id in ALL events  
✅ Track phase timings precisely  
✅ Test end-to-end telemetry flow  
✅ Handle all errors gracefully  
✅ Log failures with full context  
✅ Use async/await throughout  
✅ Validate input with Pydantic  

### DON'T:
❌ Skip telemetry emission (breaks Command Central)  
❌ Forget correlation IDs (breaks distributed tracing)  
❌ Hard-code credentials  
❌ Use synchronous blocking operations  
❌ Ignore retry logic for external APIs  
❌ Skip error event emission  
❌ Commit without tests  
❌ Deploy without documentation  

---

## QUICK REFERENCE

### Key Commands
```bash
# Run Rake
python main.py

# Run tests
pytest -v

# Type checking
mypy .

# Install dependencies
pip install -r requirements.txt

# Database check
psql -d forge -c "\dt"

# View recent events
psql -d forge -c "SELECT * FROM events WHERE service='rake' ORDER BY timestamp DESC LIMIT 10"
```

### Key URLs
- Rake: http://localhost:8002
- Health: http://localhost:8002/health
- DataForge: http://localhost:8001
- Command Central: http://localhost:3000 (SvelteKit)

### Event Types
- `job_started` - Pipeline begins
- `phase_completed` - Stage completes
- `job_completed` - Pipeline succeeds
- `job_failed` - Pipeline fails

---

**END OF CONTEXT DOCUMENT**

---

*This document provides complete context for implementing the Rake backend service. Reference it throughout development for architecture decisions, code patterns, and implementation details.*

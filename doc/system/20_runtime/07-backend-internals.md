# §7 — Backend Internals

## AuthorForge Analytics Boundary

`POST /api/v1/events/authorforge-analytics` validates the closed
`AuthorForgeAnalyticsEnvelope.v1` Pydantic schema before persistence to the dedicated
`authorforge_analytics_events` table. It does not write ForgeEvent.v1 or the physically retained
pre-v1 `events` table. Only named enums, bounded counts/timings/costs, opaque build/model
identifiers, and prefix-constrained rotatable pseudonyms are accepted. There is no free-form
metadata/metrics container. RFC 8785 bytes bind each event ID to its exact validated content:
exact retries are idempotent and changed content under the same ID fails with `409`. Validation
responses are generic and do not include the rejected input.

The retired AuthorForge content models remain registered in Alembic solely to recognize
pre-existing tables. Runtime package initializers do not eagerly import them, and the content
routers are not mounted. `scripts/audit_authorforge_boundary.py` is the only supported legacy
inspection path: it selects table existence, counts, primary-key column names, and bounded IDs;
it never selects content columns and never mutates records. It also flags historical `pf_*`
tables that contain explicit AuthorForge links or content-capable fields for human ownership
review without automatically classifying those rows as boundary violations.

## Supabase Log Poll Runtime

`scripts/poll_supabase_logs.py` performs configuration, connectivity, migration-table, and API
preflights before persistence. It uses the current unified `/analytics/endpoints/logs` stream
with source-filtered ClickHouse SQL, supplies explicit start/end timestamps, minimizes the
upstream SQL projection, clamps the query to Supabase's maximum 24-hour window, redacts before storage,
and deduplicates by source log ID. Failures use stable non-sensitive categories (configuration,
authentication, authorization, rate limiting, upstream, network, payload schema, database, and
database migration) without logging tokens or upstream response bodies.

## Vector Search Engine

### Overview

The hybrid search engine (`app/api/search.py`) runs two retrieval passes in parallel and merges them via Reciprocal Rank Fusion (RRF). Neither pass is optional — both run on every search request.

Each semantic, keyword, and hybrid path awaits a privacy-bounded operational
event through `app/telemetry_client.py`. The event records operation kind,
success/failure, aggregate timing, aggregate counts/ranks, and correlation
identity only. Search input, tags, domain identifiers, thresholds, and exception
values are excluded at the producer boundary. Telemetry failure does not replace
the search result or exception; it is counted and exposed as code-only health
state.

### Pass 1: Semantic (Vector) Retrieval

```python
# pgvector cosine similarity query
results = db.execute(
    select(Chunk, Document)
    .join(Document)
    .where(
        (1 - Chunk.embedding.cosine_distance(query_vector)) >= similarity_threshold
    )
    .order_by(Chunk.embedding.cosine_distance(query_vector))
    .limit(limit * 3)  # Over-fetch for RRF merging
)
```

The `<=>` operator (cosine distance) is provided by pgvector. Lower cosine distance = higher similarity. The complement `(1 - distance)` gives similarity in [0, 1].

### Pass 2: BM25 Full-Text Retrieval

```python
# PostgreSQL TSVECTOR + ts_rank
results = db.execute(
    select(Chunk, Document)
    .join(Document)
    .where(
        Chunk.tsvector.op('@@')(func.plainto_tsquery('english', query_text))
    )
    .order_by(
        func.ts_rank(Chunk.tsvector, func.plainto_tsquery('english', query_text)).desc()
    )
    .limit(limit * 3)
)
```

`TSVECTOR` columns are maintained by PostgreSQL triggers on insert/update. `plainto_tsquery` handles stopword removal and stemming automatically.

### RRF Merge

```python
def reciprocal_rank_fusion(semantic_results, bm25_results, k=60):
    scores = {}
    for rank, chunk_id in enumerate(semantic_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    for rank, chunk_id in enumerate(bm25_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

`k=60` is the standard RRF constant. A chunk appearing in both result sets gets double contribution. Chunks that rank highly in both get the highest merged scores.

---

## Embedding Pipeline

### Chunking

`app/utils/embeddings.py` implements token-aware chunking:

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    # Uses a tokenizer-aware splitter
    # Respects sentence boundaries where possible
    # Returns list of overlapping text segments
```

**Token counting:** Uses the same tokenizer as the target embedding model (Voyage AI uses a BPE tokenizer compatible with tiktoken's `cl100k_base`).

**Overlap behavior:** Each chunk shares the last `overlap` tokens with the next chunk. This prevents important context from being split across chunk boundaries and lost during retrieval.

### Embedding Generation

```python
async def generate_embedding(text: str) -> list[float]:
    if len(text) > MAX_EMBEDDING_INPUT_LENGTH:
        text = text[:MAX_EMBEDDING_INPUT_LENGTH]

    try:
        response = voyage_client.embed([text], model=EMBEDDING_MODEL)
        return response.embeddings[0]
    except VoyageError:
        # Fallback to OpenAI
        try:
            response = openai_client.embeddings.create(
                input=text, model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except OpenAIError:
            # Fallback to Cohere
            response = cohere_client.embed(texts=[text])
            return response.embeddings[0]
```

Embeddings are generated during document processing and cached as derived Redis state using
hash-addressed keys (`embed:{model}:{text_hash}`) with an explicit TTL. The preferred runtime
path is NeuroForge-first, with direct provider fallbacks retained for compatibility.

### Auto-Processing Trigger

When a document is created or its `content` field is updated via `POST /admin/documents` or `PATCH /admin/documents/{id}`, the API layer calls `process_document(document_id, db)` before returning the response. This ensures embeddings are always current when the endpoint returns.

---

## Field-Level Encryption

### AES-256 Fernet

DataForge encrypts PII fields automatically using `cryptography.fernet.Fernet`. The encryption key is derived from `SECRET_KEY`.

**Models with encrypted fields:**
- `User` — `email` (PII)
- `TeamMember` — contact fields
- `DiligenceProject` — assessment subject details
- Additional models as annotated in `models.py`

### Encryption Mechanism

```python
from cryptography.fernet import Fernet

class EncryptedField(TypeDecorator):
    """SQLAlchemy custom type that transparently encrypts/decrypts."""
    impl = LargeBinary

    def process_bind_param(self, value, dialect):
        # Encrypt before write
        if value is not None:
            return fernet.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        # Decrypt after read
        if value is not None:
            return fernet.decrypt(value.encode()).decode()
        return value
```

Encryption/decryption is transparent at the ORM layer. Application code reads and writes plaintext; the `EncryptedField` type handles the transformation. Encrypted values in PostgreSQL are stored as `TEXT` (base64-encoded Fernet tokens).

**Key rotation:** Requires an explicit migration or dedicated rotation utility to re-encrypt
existing records with the new key. Do not assume a checked-in helper script exists unless it
is present in the repo at the time of the change.

---

## Anomaly Detection

DataForge implements six threat detection patterns in the auth layer, evaluated on every authentication event:

### Detection Types

| Type | Trigger | Response |
|------|---------|---------|
| **Impossible travel** | Login from geographically impossible location within time window | Block + audit event |
| **Brute force** | >5 failed login attempts within 5 minutes | Account lockout (15 min) + audit event |
| **Bulk exfiltration** | >1000 document reads in <60 seconds from single user | Rate limit + audit event + alert |
| **Suspicious access** | Access to high-sensitivity domains outside normal hours | Audit event + optional MFA challenge |
| **After-hours access** | Admin operations outside configured business hours | Audit event |
| **Bulk mutations** | >100 writes in <60 seconds from single user | Rate limit + audit event |

### Implementation

Each detection type runs as an async check after the primary auth validation succeeds. Detection results are written to the audit log via `POST /api/v1/events`. The auth response is returned to the caller only after all anomaly checks complete (detections are non-blocking for legitimate users; blocking only on hard violations like brute force).

---

## Memory Governance

DataForge now enforces a hard cache-governance boundary:

1. Postgres/Supabase is authoritative
2. Redis is derived and disposable
3. Redis writes require TTL at write time
4. Cache keys must be deterministic and version-aware
5. Redis failures must never widen access

### Shared Helpers

`app/utils/cache_governance.py` provides:

- `redis_set_with_ttl()` / `redis_set_with_ttl_sync()` for TTL enforcement
- `canonicalize_query()` for order-insensitive query normalization
- `build_retrieval_cache_key()` for version-aware retrieval keys
- `require_authoritative_source()` helpers for fail-closed authority reads
- cache invalidation helpers that log every explicit invalidation

### Corpus Versioning

`app/utils/corpus_versioning.py` maintains monotonic corpus freshness:

- `corpus_state.current_version` is bumped atomically
- `corpus_versions` records the triggering event (`doc_insert`, `chunk_insert`, `reindex`, `doc_delete`, `initial`)
- `corpus_version:current` is cached for 60 seconds and deleted on every bump

Because retrieval keys include corpus version, version bumps invalidate old retrieval caches
without needing a mass delete.

## Rate Limiting

DataForge uses a Redis-backed sliding-window limiter for distributed enforcement.

```
Per request:
  1. Remove timestamps older than the active window
  2. Count remaining requests in the Redis sorted set
  3. If count >= limit: return 429
  4. Add the current request timestamp
  5. Set TTL to window_length + 60 seconds
```

On Redis outage, the limiter fails closed and denies the request. This is intentional: a cache
or Redis failure must never expand access.

---

## Governed LLM Policy Persistence

`app/api/policy_envelope_router.py` backs the Slice 1 and Slice 2 governance records used by
ForgeAgents:

- policy envelopes
- per-call ledger entries
- run finalization records
- bandit state partitions
- reward records and atomic outcome writes

Slice 4 rollout labeling is persisted in ledger/reward payload schemas as optional strict fields:
- `policy_mode_used`
- `policy_id_used`
- `baseline_policy_id`
- `is_canary`
- rollout reason and shadow-evaluation metadata fields

These routes intentionally use synchronous FastAPI handlers because the implementation is built
on the synchronous SQLAlchemy session from `app/database.py`. Keeping the handler itself sync
pushes the ORM work into FastAPI's threadpool, which prevents long-running governance reads or
writes from blocking the event loop and starving `/health`.

This matters most for `GET /api/v1/policy-routing/bandit-states/...` and
`POST /api/v1/policy-runs/finalize`, because ForgeAgents calls them inline during governed
execution and shutdown of policy runs.

---

## Startup Dependency Handling

`app/main.py` performs a best-effort `CREATE EXTENSION IF NOT EXISTS vector` during startup.
That step is advisory, not a boot gate. If Supabase/Postgres is temporarily unavailable, the
process now continues to start, exposes `/health`, and leaves `/ready` to report the database
or pgvector failure until connectivity recovers.

`DATAFORGE_SKIP_STARTUP_DB_INIT=1` remains available for tests and controlled operational
workarounds when startup DB initialization should be bypassed entirely.

---

## Audit Log

Every significant event — auth successes, failures, anomaly detections, lifecycle transitions, admin operations — is written to the audit log:

```python
event = AuditEvent(
    event_type="finding.lifecycle.transition",
    actor_id=user_id,
    resource_type="bugcheck_finding",
    resource_id=finding_id,
    payload={"from": "NEW", "to": "TRIAGED"},
    timestamp=utcnow(),
    hmac=hmac_sha256(event_data, SECRET_KEY)
)
```

The `hmac` field enables tamper detection. On audit log export or compliance review, each event's HMAC is re-computed and compared. Any mismatch indicates tampering.

**The audit log table has no UPDATE or DELETE operations in the ORM.** The only permitted operation is INSERT. The `/api/v1/events` router has no PATCH or DELETE endpoints.

---

## Dead Letter Queue (DLQ)

Async tasks that fail after 3 retries (exponential backoff, max 60 seconds) are written to the DLQ table. The `/dlq` router provides:

- `GET /dlq` — list failed tasks with error context
- `POST /dlq/{task_id}/replay` — manually replay a failed task
- `DELETE /dlq/{task_id}` — discard a failed task (requires admin)

DLQ entries include the full task payload, error traceback, retry count, and timestamps for each attempt. This is the recovery path for embedding failures, cache sync failures, and notification failures.

---

## CORS Configuration

CORS is configured in `app/main.py` via FastAPI's `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Run-Token"],
)
```

`allow_credentials=True` is required for JWT cookie flows. The `X-Run-Token` header is the BugCheck scoped run token. Wildcards in `allow_origins` are rejected in production builds via a startup assertion.

# §7 — Backend Internals

## Vector Search Engine

### Overview

The hybrid search engine (`app/api/search.py`) runs two retrieval passes in parallel and merges them via Reciprocal Rank Fusion (RRF). Neither pass is optional — both run on every search request.

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

Embeddings are generated synchronously per chunk during document processing. For batch operations (bulk import), chunks are embedded in parallel up to the provider's rate limit.

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

**Key rotation:** Requires a migration to re-encrypt all existing records with the new key. A key rotation script is provided in `scripts/`.

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

Each detection type runs as an async check after the primary auth validation succeeds. Detection results are written to the audit log via `POST /api/events`. The auth response is returned to the caller only after all anomaly checks complete (detections are non-blocking for legitimate users; blocking only on hard violations like brute force).

---

## Rate Limiting

DataForge uses a distributed Redis token bucket:

```
Per request:
  1. GET rate_limit:{user_id} from Redis
  2. If tokens < 1: return 429 Too Many Requests
  3. Decrement token count
  4. Set expiry if key is new (window reset)

Refill:
  Background task refills tokens at RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW_SECONDS
```

Global limits apply across all DataForge instances. A single user cannot circumvent limits by hitting different instances.

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

**The audit log table has no UPDATE or DELETE operations in the ORM.** The only permitted operation is INSERT. The `/api/events` router has no PATCH or DELETE endpoints.

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

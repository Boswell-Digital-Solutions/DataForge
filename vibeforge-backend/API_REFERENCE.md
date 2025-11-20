# VibeForge API Reference & cURL Examples

Complete API documentation with real-world examples for testing the integration.

## Base URL

```
http://localhost:8000/v1/vibeforge
```

## Authentication

Currently no authentication required. Future versions will use JWT bearer tokens.

---

## Endpoints

### Health Check

**Endpoint**: `GET /health`

**Purpose**: Verify backend is running and LLM services are available.

```bash
curl http://localhost:8000/v1/vibeforge/health
```

**Response** (200 OK):

```json
{
  "status": "ok",
  "service": "vibeforge"
}
```

---

### Create Run

**Endpoint**: `POST /run`

**Purpose**: Create and execute a new model run with optional context blocks.

**Request Headers**:

```
Content-Type: application/json
```

**Request Body**:

```json
{
  "model": "claude-3-opus-20240229",
  "prompt": "Your prompt here",
  "active_contexts": [
    {
      "id": "unique-id",
      "title": "Context Title",
      "content": "Context content",
      "kind": "code",
      "priority": 1
    }
  ],
  "data_profile_id": null,
  "eval_profile_id": null
}
```

**cURL Examples**:

**Simple run (no context)**:

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "What is TypeScript?",
    "active_contexts": []
  }'
```

**With context blocks**:

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "Review this code for bugs",
    "active_contexts": [
      {
        "id": "code-style",
        "title": "Code Review Guidelines",
        "content": "- Focus on security issues\n- Check for null pointer dereferences\n- Verify error handling",
        "kind": "code",
        "priority": 1
      },
      {
        "id": "typescript-rules",
        "title": "TypeScript Rules",
        "content": "- Must use strict mode\n- No any types\n- Explicit return types required",
        "kind": "code",
        "priority": 2
      }
    ]
  }'
```

**With profiles** (future feature):

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo-preview",
    "prompt": "Write unit tests for this component",
    "active_contexts": [],
    "data_profile_id": "profile-123",
    "eval_profile_id": "eval-456"
  }'
```

**Response** (201 Created):

```json
{
  "id": "run-550e8400-e29b-41d4-a716-446655440000",
  "model": "claude-3-opus-20240229",
  "prompt": "What is TypeScript?",
  "status": "complete",
  "output": "TypeScript is a typed superset of JavaScript...",
  "error": null,
  "tokens_used": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  },
  "created_at": "2025-11-18T14:30:00Z",
  "started_at": "2025-11-18T14:30:01Z",
  "completed_at": "2025-11-18T14:30:03Z",
  "duration_ms": 2500,
  "active_contexts": [],
  "data_profile_id": null,
  "eval_profile_id": null
}
```

**Error Response** (500 Internal Server Error):

```json
{
  "detail": "Anthropic API key not configured. Set ANTHROPIC_API_KEY in environment."
}
```

---

### Get Run

**Endpoint**: `GET /run/{run_id}`

**Purpose**: Retrieve a specific run by ID.

**Parameters**:

- `run_id` (path): The unique run identifier

**cURL Examples**:

```bash
# Get a run
curl http://localhost:8000/v1/vibeforge/run/run-550e8400-e29b-41d4-a716-446655440000

# Pretty print response
curl -s http://localhost:8000/v1/vibeforge/run/run-550e8400-e29b-41d4-a716-446655440000 | jq
```

**Response** (200 OK):

```json
{
  "id": "run-550e8400-e29b-41d4-a716-446655440000",
  "model": "claude-3-opus-20240229",
  "prompt": "What is TypeScript?",
  "status": "complete",
  "output": "TypeScript is a typed superset of JavaScript...",
  "error": null,
  "tokens_used": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  },
  "created_at": "2025-11-18T14:30:00Z",
  "started_at": "2025-11-18T14:30:01Z",
  "completed_at": "2025-11-18T14:30:03Z",
  "duration_ms": 2500,
  "active_contexts": [],
  "data_profile_id": null,
  "eval_profile_id": null
}
```

**Error Response** (404 Not Found):

```json
{
  "detail": "Run run-nonexistent not found"
}
```

---

### Fetch History

**Endpoint**: `GET /history`

**Purpose**: Retrieve paginated list of runs with optional filtering.

**Query Parameters**:

- `limit` (optional, default=10, max=100): Number of results
- `offset` (optional, default=0): Pagination offset
- `model` (optional): Filter by model name
- `status` (optional): Filter by status (pending, running, complete, error, cancelled)

**cURL Examples**:

**Basic pagination**:

```bash
# Get first 10 runs
curl http://localhost:8000/v1/vibeforge/history?limit=10&offset=0

# Get next page
curl http://localhost:8000/v1/vibeforge/history?limit=10&offset=10

# Get all data
curl http://localhost:8000/v1/vibeforge/history?limit=100&offset=0
```

**Filtering**:

```bash
# Filter by model
curl http://localhost:8000/v1/vibeforge/history?model=claude-3-opus-20240229

# Filter by status
curl http://localhost:8000/v1/vibeforge/history?status=complete

# Combine filters
curl http://localhost:8000/v1/vibeforge/history?model=gpt-4&status=error

# Pretty print
curl -s 'http://localhost:8000/v1/vibeforge/history?limit=5' | jq
```

**Response** (200 OK):

```json
{
  "total": 42,
  "limit": 5,
  "offset": 0,
  "items": [
    {
      "id": "run-abc123",
      "model": "claude-3-opus-20240229",
      "prompt": "What is TypeScript?",
      "status": "complete",
      "output": "TypeScript is a typed superset of JavaScript...",
      "error": null,
      "tokens_used": {
        "prompt_tokens": 15,
        "completion_tokens": 120,
        "total_tokens": 135
      },
      "created_at": "2025-11-18T14:30:00Z",
      "started_at": "2025-11-18T14:30:01Z",
      "completed_at": "2025-11-18T14:30:03Z",
      "duration_ms": 2500,
      "active_contexts": [],
      "data_profile_id": null,
      "eval_profile_id": null
    }
    // ... more items
  ]
}
```

---

## Common Use Cases

### 1. Test Backend Connectivity

```bash
#!/bin/bash
echo "Testing backend connectivity..."

if curl -s http://localhost:8000/health | grep -q "ok"; then
  echo "✓ Backend is running"
else
  echo "✗ Backend is not running"
  exit 1
fi
```

### 2. Batch Test Multiple Models

```bash
#!/bin/bash

MODELS=(
  "claude-3-opus-20240229"
  "claude-3-sonnet-20240229"
  "gpt-4-turbo-preview"
  "gpt-3.5-turbo"
)

PROMPT="Explain machine learning in one sentence"

for model in "${MODELS[@]}"; do
  echo "Testing $model..."

  response=$(curl -s -X POST http://localhost:8000/v1/vibeforge/run \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$model\",
      \"prompt\": \"$PROMPT\",
      \"active_contexts\": []
    }")

  status=$(echo "$response" | jq -r '.status')
  tokens=$(echo "$response" | jq -r '.tokens_used.total_tokens // "N/A"')

  echo "  Status: $status, Tokens: $tokens"
done
```

### 3. Find Longest-Running Requests

```bash
curl -s 'http://localhost:8000/v1/vibeforge/history?limit=100' | \
  jq '.items | sort_by(.duration_ms) | reverse | .[0:5] | .[] | {model, duration_ms, prompt: .prompt[0:50]}'
```

### 4. Calculate Average Token Usage

```bash
curl -s 'http://localhost:8000/v1/vibeforge/history?limit=100' | \
  jq '[.items[] | select(.tokens_used != null) | .tokens_used.total_tokens] |
      {
        count: length,
        total: add,
        average: (add / length),
        min: min,
        max: max
      }'
```

### 5. Export All Data as CSV

```bash
curl -s 'http://localhost:8000/v1/vibeforge/history?limit=1000' | \
  jq -r '.items[] | [.id, .model, .status, .duration_ms, .tokens_used.total_tokens] | @csv'
```

---

## Status Codes

| Code | Meaning             | Example                           |
| ---- | ------------------- | --------------------------------- |
| 200  | Success             | GET request returns data          |
| 201  | Created             | POST /run successfully created    |
| 400  | Bad Request         | Invalid query parameters          |
| 404  | Not Found           | Run ID doesn't exist              |
| 422  | Validation Error    | Missing required field in request |
| 500  | Server Error        | LLM API not configured            |
| 503  | Service Unavailable | Backend temporarily down          |

---

## Error Handling

### Invalid Request (Missing Model)

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Test",
    "active_contexts": []
  }'
```

**Response** (422 Unprocessable Entity):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "model"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### API Key Not Configured

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "Test",
    "active_contexts": []
  }'
```

**Response** (500 Internal Server Error) - if ANTHROPIC_API_KEY not set:

```json
{
  "detail": "Error: Anthropic API key not configured. Set ANTHROPIC_API_KEY in environment."
}
```

### Model Not Supported

```bash
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unknown-model-xyz",
    "prompt": "Test",
    "active_contexts": []
  }'
```

**Response** (500 Internal Server Error):

```json
{
  "detail": "Error: Unknown model: unknown-model-xyz. Supported: claude-*, gpt-*, ollama:*"
}
```

---

## Testing Workflow

### Step 1: Verify Backend

```bash
curl http://localhost:8000/health
```

### Step 2: Create a Test Run

```bash
RUN_ID=$(curl -s -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "Test prompt",
    "active_contexts": []
  }' | jq -r '.id')

echo "Created run: $RUN_ID"
```

### Step 3: Retrieve the Run

```bash
curl "http://localhost:8000/v1/vibeforge/run/$RUN_ID" | jq
```

### Step 4: Check History

```bash
curl 'http://localhost:8000/v1/vibeforge/history?limit=1' | jq
```

### Step 5: Verify Frontend Can Connect

```bash
# From browser console
fetch('http://localhost:8000/health').then(r => r.json()).then(console.log)
```

---

## Performance Benchmarks

### Token Estimation (Rust)

```bash
python3 << 'EOF'
from vibeforge_prompt import estimate_tokens_precise
import time

text = "The quick brown fox " * 1000
start = time.time()
for _ in range(100):
    estimate_tokens_precise(text)
elapsed = time.time() - start

print(f"100 calls: {elapsed:.2f}s ({100/elapsed:.0f} calls/sec)")
EOF
```

**Expected**: >1000 calls/sec

### API Latency

```bash
time curl -s -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "prompt": "Hello",
    "active_contexts": []
  }' > /dev/null
```

**Expected**: 1-5 seconds (depends on LLM provider)

### Database Queries

```bash
# Get history (should be <100ms for <10k runs)
time curl -s http://localhost:8000/v1/vibeforge/history?limit=10 > /dev/null
```

**Expected**: <100ms

---

## Related Documentation

- **Integration Guide**: `INTEGRATION_GUIDE.md`
- **Setup Instructions**: `INTEGRATION_SETUP.md`
- **Architecture**: `ARCHITECTURE.md`
- **AI Instructions**: `.github/copilot-instructions.md`

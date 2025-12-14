# 🌐 Forge Global Execution Contract

**Version:** 1.0  
**Effective Date:** December 8, 2025  
**Scope:** All Forge clients (VibeForge, VibeForge_BDS, AuthorForge, TradeForge, Livy, Leopold, DataForge, future apps)  
**Backend:** ForgeAgents 120-Skill API  
**Status:** OFFICIAL STANDARD

---

## 1. Purpose

This contract defines how **every Forge client** executes tasks against ForgeAgents, ensuring:

- ✅ Unified invocation format
- ✅ Consistent error handling
- ✅ Deterministic retry behavior
- ✅ Token lifecycle management
- ✅ Session tracking
- ✅ SAS + MAPO enforcement
- ✅ Model routing via NeuroForge
- ✅ Observability and logging

**Result:** No matter which Forge product you're using, every agent call behaves identically, returns the same structure, and can be debugged with the same tools.

---

## 2. Universal Execution Shape

Every ForgeAgents invocation follows this exact shape:

### 2.1 Request Format

```typescript
interface ForgeExecutionRequest {
  inputs: Record<string, any>;      // Skill-specific parameters
  options?: {
    model?: string;                 // Override model selection (optional)
    temperature?: number;           // Default 0.2
    max_tokens?: number;            // Default 4096
    stream?: boolean;               // Default false
    priority?: "normal" | "high";   // For schedulers
  };
  metadata?: {
    source: string;                 // "VibeForge"|"VibeForge_BDS"|"AuthorForge"|...
    user: string;                   // BDS email or local user identifier
    sessionId?: string;             // For continuing sessions
  };
}
```

**Example:**
```typescript
POST /api/v1/bds/skills/S1/invoke
{
  "inputs": {
    "feature": "Real-time collaboration"
  },
  "options": {
    "model": "claude-3.5-sonnet",
    "temperature": 0.7,
    "stream": true
  },
  "metadata": {
    "source": "VibeForge_BDS",
    "user": "charles@bds.com"
  }
}
```

### 2.2 Response Format (Non-Streaming)

```typescript
interface ForgeExecutionResponse {
  sessionId: string;                // Unique session identifier
  status: "success" | "error";      // Execution outcome
  output?: string;                  // Result (if successful)
  error?: string;                   // Error message (if failed)
  metadata: {
    tokens_used: number;            // LLM tokens consumed
    cost: number;                   // USD cost
    latency_ms: number;             // Wall-clock time
    model_used: string;             // Which model executed
    timestamp: string;              // ISO 8601
  };
  audit?: {
    sas: "pass" | "warn" | "fail";
    violations?: string[];          // SAS rule violations (if any)
  };
}
```

**Example Response:**
```json
{
  "sessionId": "sess_abc123xyz789",
  "status": "success",
  "output": "Feature plan: 1. Design API endpoints 2. Implement in all 3 repos...",
  "metadata": {
    "tokens_used": 2145,
    "cost": 0.0064,
    "latency_ms": 3200,
    "model_used": "claude-3.5-sonnet",
    "timestamp": "2025-12-08T22:30:45Z"
  },
  "audit": {
    "sas": "pass",
    "violations": []
  }
}
```

### 2.3 Streaming Format

Streaming responses use `text/event-stream`:

```
token_1
token_2
token_3
...
{"event": "complete", "sessionId": "sess_abc123xyz789"}
```

Each token is appended to the client sequentially. Final message signals completion.

---

## 3. Authentication & Token Lifecycle

All Forge clients must implement this exact token lifecycle:

### 3.1 Token Rules

```typescript
const TOKEN_LIFETIME = 3600000;      // 1 hour in milliseconds
const REFRESH_BUFFER = 60000;        // Refresh within 1 minute of expiry
const REFRESH_RETRIES = 1;           // Max one automatic refresh attempt
```

**Rules:**
- Access tokens valid for 1 hour
- MUST refresh within 1 minute before expiry
- Never cache expired tokens
- On token failure → retry ONCE after refresh, then fail
- If refresh fails → clear all tokens, return AUTH_ERROR

### 3.2 Refresh Endpoint

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token_here"
}

Response (200 OK):
{
  "access_token": "new_jwt_token",
  "refresh_token": "new_refresh_token",
  "expires_at": "2025-12-09T06:30:45Z"
}
```

### 3.3 Token State Machine

```
┌─────────────────┐
│  No Token       │
└────────┬────────┘
         │ Login()
         ▼
┌─────────────────────────┐
│  Token Valid            │ ← Use in all requests
│  (Expires in > 1min)    │
└────────┬────────────────┘
         │ Time passes...
         │ (Token expires in < 1min)
         ▼
┌─────────────────────────┐
│  Token Expiring         │
│  (Auto-refresh)         │
└────────┬────────────────┘
         │ Refresh succeeds
         │ OR fails
         ▼
┌─────────────────────────┐
│  Token Refreshed        │
│  OR                     │
│  Cleared (Login again)  │
└─────────────────────────┘
```

---

## 4. Retry Protocol (3-Tier Standard)

Every Forge client must implement this exact 3-tier retry protocol:

### 4.1 Tier 1 — Network Retry (Automatic)

**When:** Temporary network failures (timeout, DNS failure, connection reset)

**Configuration:**
```typescript
const NETWORK_RETRIES = 2;
const BACKOFF_BASE = 300;      // 300ms
const BACKOFF_MULTIPLIER = 4;  // 300ms → 1200ms
```

**Algorithm:**
```
Attempt 1: Execute request
  ↓ FAILS with network error
Attempt 2: Wait 300ms, retry
  ↓ FAILS with network error
Attempt 3: Wait 1200ms, retry
  ↓ FAILS
Return network_error
```

**Retry Only On:**
- ECONNRESET
- ETIMEDOUT
- ENOTFOUND (DNS)
- EHOSTUNREACH

### 4.2 Tier 2 — Token Refresh & Retry (Authentication)

**When:** Unauthorized (401)

**Algorithm:**
```
Request fails with 401
  ↓
IF token in storage AND not obviously expired:
    Attempt refresh (POST /auth/refresh)
      ↓ SUCCESS
      Retry original request (1 attempt only)
      ↓ Result (success or failure)
      Return result
      ↓ REFRESH FAILED
    Clear tokens
    Return auth_error

IF no token in storage:
    Return auth_error (user must login)
```

### 4.3 Tier 3 — No-Retry Zones

**NEVER auto-retry if:**

- ❌ SAS violation detected (403)
- ❌ MAPO safety block triggered (403)
- ❌ Input validation failed (400)
- ❌ Skill returns error (404, 500+)
- ❌ User error (422)
- ❌ Rate limited (429 — wait, don't retry immediately)

**Total Retries Per Request:**
- Network: 2 retries (Tier 1)
- Token: 1 retry (Tier 2)
- Skill errors: 0 retries
- **Maximum: 3 attempts total**

---

## 5. Unified Error Contract

All errors from ForgeAgents MUST conform to this structure:

```typescript
interface ForgeError {
  type:
    | "auth_error"          // Login failed, token invalid, refresh failed
    | "network_error"       // Connection timeout, DNS, unreachable
    | "skill_error"         // Skill execution failed
    | "sas_violation"       // SAS policy blocked this action
    | "mapo_block"          // MAPO orchestration blocked
    | "validation_error"    // Input validation failed
    | "rate_limited"        // Rate limit exceeded (429)
    | "unknown";            // Unknown error

  message: string;          // Human-readable error message
  suggestion?: string;      // What to do next
  retryable: boolean;       // Can client retry?
  metadata?: Record<string, any>;
}
```

### 5.1 Error Mapping Table

| HTTP Code | Error Type | Retryable | Client Action |
|-----------|-----------|-----------|---------------|
| 400 | validation_error | ❌ | Show error to user |
| 401 | auth_error | ✅ (1x) | Refresh token, retry once |
| 403 | sas_violation / mapo_block | ❌ | Show block reason, ask user |
| 404 | skill_error | ❌ | Skill not found (shouldn't happen) |
| 408 | network_error | ✅ | Backoff retry |
| 422 | validation_error | ❌ | Invalid input format |
| 429 | rate_limited | 🔁 | Wait for Retry-After, retry |
| 500 | skill_error | ❌ | Skill failed, show error |
| 502/503/504 | network_error | ✅ | Backoff retry |

### 5.2 Error Example

```json
{
  "type": "sas_violation",
  "message": "Request violates SAS rule: no direct data mutation on Sunday",
  "suggestion": "Schedule this task for Monday, or use SafeMutation=true flag",
  "retryable": false,
  "metadata": {
    "rule_violated": "SAS.schedule.no_prod_changes_on_weekend",
    "current_time": "2025-12-07T14:30:00Z"
  }
}
```

---

## 6. Execution Session Protocol

Every execution creates a server-side session for auditing and continuation:

### 6.1 Session Lifecycle

```
POST /api/v1/bds/skills/{id}/invoke
  ↓ Server creates session
  ↓ Returns sessionId in response
  ↓ Session logs stored in DataForge
  ↓ Queryable for 30 days
```

### 6.2 Session Management Endpoints

```
GET /api/v1/sessions/{sessionId}
  → Returns full execution record

POST /api/v1/sessions/{sessionId}/cancel
  → Cancels in-progress execution
  → Returns 200 if cancelled
  → Returns 404 if already complete

GET /api/v1/sessions/my
  → Returns all sessions for authenticated user
```

### 6.3 Continuing a Session

To continue or retry a skill invocation:

```typescript
POST /api/v1/bds/skills/{id}/invoke
{
  "inputs": {...},
  "metadata": {
    "sessionId": "sess_existing_id"  // Continue previous session
  }
}
```

---

## 7. MAPO Enforcement (Required on Every Call)

**MAPO = Moderation → Access → Policy → Orchestration**

Every ForgeAgents execution flows through this pipeline:

```
┌──────────────────┐
│  1. Moderation   │ LLM safety check + heuristics
├──────────────────┤
│  2. Access       │ PUBLIC vs BDS_ONLY enforcement
├──────────────────┤
│  3. Policy (SAS) │ SAS rule validation
├──────────────────┤
│  4. Orchestrate  │ Model routing, pipeline selection
├──────────────────┤
│  5. Execute      │ Run skill
├──────────────────┤
│  6. Post-Process │ Format, validate, log
└──────────────────┘
```

### 7.1 Client Responsibilities

**Clients MUST:**
- ✅ Display SAS warnings/blocks to user
- ✅ Respect MAPO blocks (403 errors)
- ✅ Never bypass orchestration
- ✅ Show compliance status in UI
- ✅ Log MAPO outcomes for audit

**Example UI Display:**
```
Status: ⚠️ SAS Warning
Rule: "No code changes on Sunday"
Current Time: Sunday 14:30 UTC
Action: "Allowed but logged. Re-check Monday for confirmation."
```

---

## 8. NeuroForge Model Routing Contract

Every execution follows this deterministic routing process:

### 8.1 Model Selection Flow

```
Input: skill_id, inputs, options
  ↓
1. Determine task type (from skill metadata)
  ↓
2. Select champion model (Claude 3.5, GPT-4, Llama 3.1)
  ↓
3. Apply constraints:
   - Token budget
   - Cost limits
   - Privacy requirements
   - Latency SLA
  ↓
4. Choose execution layer:
   - Local (Ollama/LM Studio)? → O9 evaluates
   - Cloud (OpenAI/Anthropic)? → L3 evaluates
  ↓
5. Execute on champion
  ↓
6. Evaluate result quality
  ↓
7. Return unified output (client sees no difference)
```

### 8.2 Client Constraints

Clients MUST NOT request models that:
- ❌ Violate SAS rules
- ❌ Break privacy requirements
- ❌ Exceed cost budget
- ❌ Violate local-only mandates

**Valid override:**
```typescript
{
  "options": {
    "model": "claude-3.5-sonnet",
    "priority": "high"  // OK
  }
}
```

**Invalid override:**
```typescript
{
  "options": {
    "model": "gpt-4-turbo"  // Violates cost budget
  }
}
// Server rejects with: model_not_allowed (SAS)
```

---

## 9. Logging & Observability Contract

Every request MUST include metadata for observability:

### 9.1 Required Metadata

```typescript
{
  "metadata": {
    "source": "VibeForge_BDS",      // Which app
    "user": "charles@bds.com",       // Who
    "device": "desktop",             // Where
    "version": "1.0.0"               // What version
  }
}
```

### 9.2 Server Logging

ForgeAgents stores in DataForge:
- ✅ Request timestamp
- ✅ Skill ID invoked
- ✅ Tokens consumed
- ✅ Model selected
- ✅ Execution time
- ✅ SAS violations
- ✅ MAPO blocks
- ✅ Success/failure outcome

**Query all logs:**
```
GET /api/v1/logs?user=charles@bds.com&days=7
```

---

## 10. Front-End Handling Rules (Universal)

Every Forge app must follow these rules when displaying skill results:

### 10.1 Loading States

```
Display ⏳ spinner for > 200ms
  ↓
If stream=true:
  Replace spinner with streaming tokens
  Append tokens in real-time
  Show final result on complete event
  ↓
If stream=false:
  Wait for full response
  Show result when arrived
```

### 10.2 Streaming UI

```typescript
// Correct:
for await (const chunk of forgeAgentsClient.invokeSkillStreaming(...)) {
  resultDiv.textContent += chunk;  // Append tokens
}

// Wrong:
const fullResponse = await aggregateStream(...);
resultDiv.textContent = fullResponse;  // Blocks UI
```

### 10.3 Error UI

```
On error:
  1. Display error type (auth / SAS / network / skill)
  2. Display human-readable message
  3. IF retryable: Show [Retry] button
  4. IF not retryable: Show [Close] or [Report Bug]
  5. NEVER auto-retry more than contract allows
```

### 10.4 Cancel UI

```
For long-running tasks (> 10 seconds):
  1. Show [Cancel] button
  2. On click: POST /api/v1/sessions/{id}/cancel
  3. Show "Cancellation requested..." state
  4. Wait for session to report cancelled status
```

---

## 11. Rate Limiting Contract

Default rate limits:

```
PUBLIC skills (VibeForge):
  100 requests/minute per IP
  1000 requests/hour per IP

BDS_ONLY skills (VibeForge_BDS):
  1000 requests/minute per authenticated user
  100,000 requests/day per authenticated user
```

### 11.1 Rate Limit Headers

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1733779200
```

### 11.2 Client Behavior on 429

```typescript
if (response.status === 429) {
  const retryAfter = parseInt(response.headers.get('Retry-After'));
  wait(retryAfter * 1000);
  // Exponential backoff: don't immediately retry
  // 1st attempt: wait 1s
  // 2nd attempt: wait 4s
  // 3rd attempt: wait 16s
}
```

---

## 12. Versioning & Backward Compatibility

API versions track breaking changes:

```
/api/v1/        Current version (stable)
/api/v2/        New major version (if needed)
```

### 12.1 Deprecation Path

Deprecated skills include:
```json
{
  "id": "A1",
  "name": "80/20 Extractor",
  "deprecated": true,
  "sunset_date": "2026-06-30",
  "replacement": "G1"
}
```

**Client behavior:**
- Hide deprecated skills by default
- Show warning if user selects deprecated skill
- Migrate to replacement before sunset date

---

## 13. Security Guarantees

ForgeAgents guarantees:

✅ **No PII in logs** — Sanitized before storage  
✅ **TLS enforced** — All connections encrypted  
✅ **Streaming safe** — Metadata never leaked in token stream  
✅ **Token safe** — Stored only in Tauri secure storage, never in localStorage  
✅ **Untrusted input** — All skill outputs validated before returning  

**Client responsibilities:**
- ✅ Never log access tokens
- ✅ Never store tokens in localStorage
- ✅ Never pass PII in skill inputs
- ✅ Treat skill outputs as untrusted until validated

---

## 14. Minimum Client Responsibilities

Every Forge app MUST implement:

✅ Token refresh logic (Section 3)  
✅ 3-tier retry protocol (Section 4)  
✅ Global error handling (Section 5)  
✅ SAS compliance display (Section 7)  
✅ MAPO block respect (Section 7)  
✅ Streaming result handling (Section 10)  
✅ Session metadata logging (Section 9)  
✅ Skill registry schema validation (Section 2)  
✅ Rate limit backoff (Section 11)  
✅ Never bypass orchestration (Always)  

---

## 15. Reference Endpoints

```
Authentication:
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/logout

Public Skills:
  GET    /api/v1/skills
  GET    /api/v1/skills/{id}
  GET    /api/v1/skills/search?query=...
  POST   /api/v1/skills/{id}/invoke

BDS Skills (authenticated):
  GET    /api/v1/bds/skills
  GET    /api/v1/bds/skills/{id}
  GET    /api/v1/bds/skills/search?query=...
  POST   /api/v1/bds/skills/{id}/invoke

Sessions:
  GET    /api/v1/sessions/{sessionId}
  POST   /api/v1/sessions/{sessionId}/cancel
  GET    /api/v1/sessions/my

Logs:
  GET    /api/v1/logs?user=...&days=...
```

---

## 16. Implementation Checklist

Use this when implementing a Forge client:

### Phase 1: Authentication
- [ ] Implement token refresh logic
- [ ] Store tokens in Tauri secure storage (not localStorage)
- [ ] Handle login/logout

### Phase 2: API Client
- [ ] Implement fetch with auth headers
- [ ] Implement retry protocol (3 tiers)
- [ ] Implement error mapping
- [ ] Implement session ID tracking

### Phase 3: Streaming
- [ ] Implement streaming token append
- [ ] Handle stream completion event
- [ ] Don't block UI during streaming

### Phase 4: UI
- [ ] Display error types correctly
- [ ] Show retry button only if retryable
- [ ] Display SAS compliance status
- [ ] Show MAPO blocks clearly
- [ ] Implement cancel for long tasks

### Phase 5: Observability
- [ ] Log metadata (source, user, device, version)
- [ ] Never log tokens
- [ ] Track session IDs
- [ ] Query execution history

---

## 17. Final Notes

**This contract is now the official standard for all Forge applications.**

It unifies:
- VibeForge (public prompt engineering)
- VibeForge_BDS (internal orchestration)
- AuthorForge (writing OS)
- TradeForge (financial analysis)
- Livy (location-aware tours)
- Leopold (wildlife biology)
- DataForge clients
- All future Forge apps (WebSafe, MoneyAI, etc.)

**Benefit:** Every agent call across your entire ecosystem behaves identically, enabling:
- ✅ Predictable engineering
- ✅ Predictable debugging
- ✅ Predictable governance
- ✅ Scalable orchestration
- ✅ Zero surprises

---

**Effective immediately. Non-negotiable. Reference in every implementation.**

**Version:** 1.0  
**Last Updated:** December 8, 2025  
**Maintained by:** Boswell Digital Solutions LLC  
**Status:** OFFICIAL STANDARD

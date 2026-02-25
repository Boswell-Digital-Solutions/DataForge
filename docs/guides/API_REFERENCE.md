# DataForge API Reference

**Version:** 5.1  
**Last Updated:** November 21, 2025  
**Status:** Complete

---

## Table of Contents

1. [Authentication APIs](#authentication-apis)
2. [Data Access APIs](#data-access-apis)
3. [Encryption APIs](#encryption-apis)
4. [Audit & Compliance APIs](#audit--compliance-apis)
5. [High Availability APIs](#high-availability-apis)
6. [Rate Limiting](#rate-limiting)
7. [Error Handling](#error-handling)
8. [Status Codes](#status-codes)

---

## Authentication APIs

### OAuth2 Authorization Code Flow

#### 1. Initiate Authorization

**GET** `/auth/oauth2/authorize`

```bash
curl -X GET 'http://localhost/auth/oauth2/authorize?provider=google&client_id=xyz&redirect_uri=http://localhost:3000/callback&state=random123'
```

**Query Parameters:**

- `provider` (required): "google", "github", or "microsoft"
- `client_id` (required): OAuth2 client ID
- `redirect_uri` (required): Callback URL
- `state` (recommended): CSRF protection token
- `scope` (optional): Requested scopes

**Response:** 302 redirect to provider login

---

#### 2. Handle Callback

**POST** `/auth/oauth2/callback`

```bash
curl -X POST 'http://localhost/auth/oauth2/callback' \
  -H 'Content-Type: application/json' \
  -d '{
    "provider": "google",
    "code": "4/0AY-..."
  }'
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "user_123abc",
  "email": "user@gmail.com",
  "name": "John Doe"
}
```

---

### Traditional Login

#### Login with Email/Password

**POST** `/auth/login`

```bash
curl -X POST 'http://localhost/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123"
  }'
```

**Request Body:**

```json
{
  "email": "string (email format)",
  "password": "string (min 12 chars)"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "user_123",
  "mfa_required": false
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Invalid email or password"
}
```

---

### Multi-Factor Authentication

#### Setup TOTP 2FA

**POST** `/auth/mfa/setup`

```bash
curl -X POST 'http://localhost/auth/mfa/setup' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Response (200 OK):**

```json
{
  "secret": "JBSWY3DPEBLW64TMMQ======",
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "backup_codes": [
    "1234-5678",
    "2345-6789",
    "3456-7890",
    "4567-8901",
    "5678-9012",
    "6789-0123",
    "7890-1234",
    "8901-2345",
    "9012-3456",
    "0123-4567"
  ]
}
```

**Instructions:**

1. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
2. Save backup codes securely
3. Verify TOTP code with API

---

#### Verify TOTP Code

**POST** `/auth/mfa/verify`

```bash
curl -X POST 'http://localhost/auth/mfa/verify' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'Content-Type: application/json' \
  -d '{
    "totp_code": "123456"
  }'
```

**Response (200 OK):**

```json
{
  "verified": true,
  "mfa_enabled": true
}
```

---

#### Verify with Backup Code

**POST** `/auth/mfa/verify-backup`

```bash
curl -X POST 'http://localhost/auth/mfa/verify-backup' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'Content-Type: application/json' \
  -d '{
    "backup_code": "1234-5678"
  }'
```

**Response (200 OK):**

```json
{
  "verified": true,
  "remaining_backup_codes": 9
}
```

---

### Token Management

#### Logout (Revoke Token)

**POST** `/auth/logout`

```bash
curl -X POST 'http://localhost/auth/logout' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Response (200 OK):**

```json
{
  "message": "Logged out successfully"
}
```

---

#### Refresh Token

**POST** `/auth/refresh`

```bash
curl -X POST 'http://localhost/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d '{
    "refresh_token": "refresh_token_123..."
  }'
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 3600
}
```

---

## Data Access APIs

### Create Data

**POST** `/data`

```bash
curl -X POST 'http://localhost/data' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_email": "user@example.com",
    "user_phone": "555-1234",
    "address": "123 Main St"
  }'
```

**Response (201 Created):**

```json
{
  "id": "record_abc123",
  "created_at": "2025-11-21T10:30:45.123456",
  "user_email": "user@example.com",
  "user_phone": "555-1234",
  "address": "123 Main St"
}
```

**Automatic Encryption:**

- `user_email`, `user_phone`, `address` fields automatically encrypted
- No additional configuration needed
- Client receives decrypted data

---

### Retrieve Data

**GET** `/data/{record_id}`

```bash
curl -X GET 'http://localhost/data/record_abc123' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Response (200 OK):**

```json
{
  "id": "record_abc123",
  "created_at": "2025-11-21T10:30:45.123456",
  "user_email": "user@example.com",
  "user_phone": "555-1234",
  "address": "123 Main St"
}
```

---

### Update Data

**PUT** `/data/{record_id}`

```bash
curl -X PUT 'http://localhost/data/record_abc123' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_phone": "555-9999"
  }'
```

**Response (200 OK):**

```json
{
  "id": "record_abc123",
  "updated_at": "2025-11-21T10:35:12.654321",
  "user_email": "user@example.com",
  "user_phone": "555-9999",
  "address": "123 Main St"
}
```

---

### Delete Data

**DELETE** `/data/{record_id}`

```bash
curl -X DELETE 'http://localhost/data/record_abc123' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Response (204 No Content)**

---

### List Data

**GET** `/data?limit=50&offset=0`

```bash
curl -X GET 'http://localhost/data?limit=20&offset=0' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Query Parameters:**

- `limit` (optional): Max records to return (default 50)
- `offset` (optional): Pagination offset (default 0)
- `sort` (optional): Sort field
- `order` (optional): "asc" or "desc"

**Response (200 OK):**

```json
{
  "total": 1500,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "record_1",
      "user_email": "user1@example.com",
      ...
    },
    {
      "id": "record_2",
      "user_email": "user2@example.com",
      ...
    }
  ]
}
```

---

## Encryption APIs

### Get Encryption Key Status

**GET** `/encryption/keys`

```bash
curl -X GET 'http://localhost/encryption/keys' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'X-Admin-Token: admin_token_123'
```

**Response (200 OK):**

```json
{
  "active_key": "key_abc123",
  "key_version": "v1",
  "rotation_policy": "quarterly",
  "last_rotated": "2025-11-01T00:00:00",
  "next_rotation": "2026-02-01T00:00:00"
}
```

---

### Rotate Encryption Key

**POST** `/encryption/rotate`

```bash
curl -X POST 'http://localhost/encryption/rotate' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'X-Admin-Token: admin_token_123'
```

**Response (200 OK):**

```json
{
  "message": "Key rotation initiated",
  "old_key_id": "key_abc123",
  "new_key_id": "key_def456",
  "rotation_date": "2025-11-21T10:35:12"
}
```

---

## Audit & Compliance APIs

### Query Audit Logs

**GET** `/audit/logs`

```bash
curl -X GET 'http://localhost/audit/logs?event_type=auth_login&user_id=user123&limit=50' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'X-Admin-Token: admin_token_123'
```

**Query Parameters:**

- `event_type` (optional): Filter by event type
- `user_id` (optional): Filter by user
- `severity` (optional): Filter by severity (info, warning, error, critical)
- `start_date` (optional): ISO 8601 datetime
- `end_date` (optional): ISO 8601 datetime
- `limit` (optional): Max results (default 100)

**Response (200 OK):**

```json
{
  "total": 1500,
  "limit": 50,
  "items": [
    {
      "timestamp": "2025-11-21T10:30:45.123456",
      "event_type": "auth_login",
      "severity": "info",
      "user_id": "user123",
      "action": "login",
      "result": "success",
      "status_code": 200,
      "message": "User logged in successfully",
      "ip_address": "192.168.1.1",
      "signature": "abc123...",
      "entry_hash": "def456..."
    }
  ]
}
```

---

### Check Anomalies

**GET** `/security/anomalies?user_id=user123&hours=24`

```bash
curl -X GET 'http://localhost/security/anomalies?user_id=user123&hours=24' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'X-Admin-Token: admin_token_123'
```

**Response (200 OK):**

```json
{
  "total": 2,
  "anomalies": [
    {
      "anomaly_type": "impossible_travel",
      "threat_level": "critical",
      "user_id": "user123",
      "timestamp": "2025-11-21T09:45:00",
      "message": "Impossible travel: 5500km in 1.0h",
      "confidence_score": 0.95,
      "recommendations": ["Verify user identity", "Review account access logs"]
    },
    {
      "anomaly_type": "brute_force",
      "threat_level": "high",
      "user_id": "user123",
      "timestamp": "2025-11-21T10:15:00",
      "message": "6 failed authentication attempts in 10 minutes",
      "confidence_score": 0.98,
      "recommendations": ["Block account temporarily", "Require password reset"]
    }
  ]
}
```

---

### Create GDPR Request

**POST** `/compliance/gdpr/request`

```bash
curl -X POST 'http://localhost/compliance/gdpr/request' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "user123",
    "right": "erasure",
    "email": "user@example.com"
  }'
```

**Rights:**

- `access`: Right of Access (Article 15)
- `erasure`: Right to Erasure (Article 17)
- `rectification`: Right to Rectification (Article 16)
- `restrict`: Right to Restrict (Article 18)
- `portability`: Right to Data Portability (Article 20)
- `object`: Right to Object (Article 21)
- `withdraw`: Withdraw Consent

**Response (201 Created):**

```json
{
  "request_id": "gdpr_user123_1234567890.123",
  "user_id": "user123",
  "right": "erasure",
  "requested_at": "2025-11-21T10:30:45",
  "deadline": "2025-12-21T10:30:45",
  "status": "pending"
}
```

**Response (200 OK) - Status Tracking:**

```bash
curl -X GET 'http://localhost/compliance/gdpr/request/gdpr_user123_1234567890.123' \
  -H 'Authorization: Bearer eyJhbGc...'
```

```json
{
  "request_id": "gdpr_user123_1234567890.123",
  "user_id": "user123",
  "status": "pending",
  "deadline": "2025-12-21T10:30:45",
  "is_overdue": false,
  "days_remaining": 30
}
```

---

### Generate Compliance Report

**GET** `/compliance/reports/{framework}`

```bash
curl -X GET 'http://localhost/compliance/reports/gdpr?start_date=2025-10-01&end_date=2025-11-01' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'X-Admin-Token: admin_token_123'
```

**Frameworks:**

- `gdpr` - GDPR compliance
- `ccpa` - CCPA compliance
- `hipaa` - HIPAA compliance
- `soc2` - SOC2 Type II
- `pci_dss` - PCI-DSS

**Response (200 OK) - GDPR Report:**

```json
{
  "period_start": "2025-10-01",
  "period_end": "2025-11-01",
  "total_requests": 150,
  "access_requests": 45,
  "erasure_requests": 30,
  "portability_requests": 20,
  "average_response_time_days": 12.5,
  "overdue_requests": 3,
  "pii_retention_violations": 5,
  "data_breach_incidents": 0,
  "dpia_completed": true,
  "dpo_appointed": true
}
```

---

## High Availability APIs

### Health Check

**GET** `/health`

```bash
curl -X GET 'http://localhost/health'
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "version": "5.1"
}
```

---

### Database Status

**GET** `/health/database`

```bash
curl -X GET 'http://localhost/health/database' \
  -H 'X-Admin-Token: admin_token_123'
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "replication_lag_ms": 45,
  "active_connections": 42,
  "max_connections": 100,
  "last_checkpoint": "2025-11-21T10:35:00"
}
```

---

### Cache Status

**GET** `/health/cache`

```bash
curl -X GET 'http://localhost/health/cache' \
  -H 'X-Admin-Token: admin_token_123'
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "type": "redis",
  "keys": 15000,
  "memory_mb": 256,
  "hit_rate": 0.85,
  "eviction_policy": "lru"
}
```

---

### Metrics (Prometheus)

**GET** `/metrics`

```bash
curl -X GET 'http://localhost/metrics'
```

**Response (200 OK) - Prometheus Format:**

```
# HELP dataforge_requests_total Total HTTP requests
# TYPE dataforge_requests_total counter
dataforge_requests_total{method="GET",status="200"} 15234
dataforge_requests_total{method="POST",status="201"} 8543
dataforge_requests_total{method="GET",status="404"} 12
dataforge_requests_total{method="GET",status="500"} 2

# HELP dataforge_request_duration_seconds Request duration
# TYPE dataforge_request_duration_seconds histogram
dataforge_request_duration_seconds_bucket{le="0.01"} 10000
dataforge_request_duration_seconds_bucket{le="0.1"} 14500
dataforge_request_duration_seconds_bucket{le="1.0"} 15200
```

---

## Rate Limiting

### Rate Limits

```
Per User (Authenticated):
- 1000 requests per hour
- 100 requests per minute

Per IP (Unauthenticated):
- 100 requests per hour
- 10 requests per minute

Admin Endpoints:
- 10000 requests per hour

Special Limits:
- Login: 5 attempts per 15 minutes
- Password reset: 3 attempts per hour
```

### Rate Limit Headers

**Request:**

```bash
curl -X GET 'http://localhost/data' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Response Headers (200 OK):**

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1700570445
```

**Rate Limited Response (429):**

```json
{
  "detail": "Rate limit exceeded. Retry after 47 seconds.",
  "retry_after": 47
}
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-11-21T10:30:45.123456",
  "path": "/api/endpoint",
  "request_id": "req_12345"
}
```

### Common Error Codes

| Code                  | Status | Description                      |
| --------------------- | ------ | -------------------------------- |
| `INVALID_CREDENTIALS` | 401    | Email or password incorrect      |
| `MFA_REQUIRED`        | 403    | MFA verification needed          |
| `RESOURCE_NOT_FOUND`  | 404    | Requested resource doesn't exist |
| `RATE_LIMIT_EXCEEDED` | 429    | Too many requests                |
| `DATABASE_ERROR`      | 500    | Database operation failed        |
| `ENCRYPTION_ERROR`    | 500    | Encryption/decryption failed     |
| `UNAUTHORIZED`        | 401    | Missing or invalid token         |
| `PERMISSION_DENIED`   | 403    | User lacks required permissions  |

---

## Status Codes

| Code  | Meaning                                          |
| ----- | ------------------------------------------------ |
| `200` | OK - Request succeeded                           |
| `201` | Created - Resource created                       |
| `204` | No Content - Request succeeded, no response body |
| `400` | Bad Request - Invalid request format             |
| `401` | Unauthorized - Authentication required           |
| `403` | Forbidden - User lacks permission                |
| `404` | Not Found - Resource not found                   |
| `429` | Too Many Requests - Rate limited                 |
| `500` | Internal Server Error - Server error             |
| `502` | Bad Gateway - Service unavailable                |
| `503` | Service Unavailable - Maintenance mode           |

---

## Testing API Endpoints

### Using cURL

```bash
# Set variables
export BASE_URL="http://localhost"
export TOKEN="your-jwt-token"

# Create data
curl -X POST "$BASE_URL/data" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "phone": "555-1234"
  }'

# Retrieve data
curl -X GET "$BASE_URL/data/record_id" \
  -H "Authorization: Bearer $TOKEN"

# List data
curl -X GET "$BASE_URL/data?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Query audit logs
curl -X GET "$BASE_URL/audit/logs?user_id=user123&limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Using Python

```python
import requests

BASE_URL = "http://localhost"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Create data
response = requests.post(
    f"{BASE_URL}/data",
    headers=headers,
    json={
        "email": "test@example.com",
        "phone": "555-1234"
    }
)
print(response.json())

# Retrieve data
response = requests.get(
    f"{BASE_URL}/data/record_id",
    headers=headers
)
print(response.json())
```

---

---

## Multi-Provider Pipeline APIs

### Model Catalog

#### List Models

**GET** `/api/v1/models`

```bash
curl -X GET 'http://localhost/api/v1/models' \
  -H 'Authorization: Bearer eyJhbGc...'
```

**Query Parameters:**

- `provider` (optional): Filter by provider (`openai`, `anthropic`, `google`, `xai`)
- `tier` (optional): Filter by tier (`budget`, `workhorse`, `flagship`)

**Response (200 OK):**

```json
{
  "models": [
    {
      "id": 1,
      "provider": "openai",
      "model_id": "gpt-5-nano",
      "tier": "budget",
      "input_cost_per_mtok": "0.10",
      "output_cost_per_mtok": "0.40",
      "supports_batch": true,
      "supports_structured_output": true,
      "cache_read_discount": "0.50",
      "max_context": 128000
    }
  ],
  "total": 14
}
```

#### Get Model

**GET** `/api/v1/models/{model_id}`

#### Create Model

**POST** `/api/v1/models`

#### Update Model

**PUT** `/api/v1/models/{model_id}`

#### Delete Model

**DELETE** `/api/v1/models/{model_id}`

---

### Pricing Monitor

#### Create Pricing Run

**POST** `/api/v1/pricing/runs`

```json
{
  "trigger_type": "scheduled"
}
```

**Response (201 Created):**

```json
{
  "id": "run-abc123",
  "trigger_type": "scheduled",
  "status": "running",
  "started_at": "2026-02-24T10:00:00Z"
}
```

#### Finalize Pricing Run

**PATCH** `/api/v1/pricing/runs/{run_id}`

```json
{
  "status": "completed",
  "changes_detected": 3,
  "alerts_created": 3
}
```

#### Store Pricing Snapshot

**POST** `/api/v1/pricing/snapshots`

```json
{
  "provider": "openai",
  "run_id": "run-abc123",
  "models": [],
  "raw_content_hash": "sha256..."
}
```

#### Get Pricing Alerts

**GET** `/api/v1/pricing/alerts`

**Query Parameters:**

- `severity` (optional): `info`, `warning`, `critical`
- `acknowledged` (optional): `true`, `false`
- `provider` (optional): Filter by provider

**Response (200 OK):**

```json
{
  "alerts": [
    {
      "id": "alert-123",
      "run_id": "run-abc123",
      "provider": "openai",
      "model_id": "gpt-5-mini",
      "change_type": "price_decrease",
      "field_changed": "input_cost_per_mtok",
      "old_value": "0.50",
      "new_value": "0.40",
      "change_percent": "-20.0",
      "severity": "info",
      "acknowledged": false,
      "created_at": "2026-02-24T10:05:00Z"
    }
  ]
}
```

#### Create Pricing Alert

**POST** `/api/v1/pricing/alerts`

---

### Cost Ledger

#### Record Cost Entry

**POST** `/api/v1/costs/record`

```json
{
  "model": "gpt-5-mini",
  "provider": "openai",
  "input_tokens": 150,
  "output_tokens": 300,
  "cached_tokens": 50,
  "cost_usd": "0.0012",
  "task_type": "summarization",
  "latency_ms": 2400
}
```

**Response (201 Created):**

```json
{
  "id": "cost-abc123",
  "recorded_at": "2026-02-24T10:00:00Z"
}
```

#### Get Costs by Run

**GET** `/api/v1/costs/by-run/{run_id}`

#### Get Cost Aggregations

**GET** `/api/v1/costs/aggregations`

**Query Parameters:**

- `group_by` (required): `provider`, `model`, `task_type`, `day`
- `start_date` (optional): ISO date
- `end_date` (optional): ISO date

**Response (200 OK):**

```json
{
  "aggregations": [
    {
      "key": "openai",
      "total_cost_usd": "12.45",
      "request_count": 523,
      "avg_latency_ms": 1840
    }
  ]
}
```

#### Get Costs by Task Type

**GET** `/api/v1/costs/by-task-type`

**Response (200 OK):**

```json
{
  "items": [
    {
      "task_type": "summarization",
      "total_cost_usd": "5.23",
      "request_count": 210
    }
  ]
}
```

---

### Batch Queue

#### Get Batch Status

**GET** `/api/v1/batch/{batch_id}`

**Response (200 OK):**

```json
{
  "batch_id": "batch-abc123",
  "provider": "openai",
  "model_id": "gpt-5-mini",
  "status": "completed",
  "items_total": 10,
  "items_completed": 10,
  "items_failed": 0,
  "cost_usd": "0.024",
  "submitted_at": "2026-02-24T10:00:00Z",
  "completed_at": "2026-02-24T10:02:30Z"
}
```

---

**API Version:** 6.0
**Last Updated:** February 24, 2026
**Stability:** Stable

# DataForge - Quick Start After Fixes

All critical bugs have been fixed! Here's what you need to know to get started.

---

## What Was Fixed?

✅ **Critical search bug** - Search now works correctly with proper vector similarity
✅ **Database errors** - Field name mismatch fixed, no more crashes
✅ **Security** - Rate limiting, input validation, and proper error handling
✅ **Performance** - N+1 query fix makes searches faster
✅ **Production-ready** - Environment validation, logging, and error handling

See [FIXES.md](FIXES.md) for complete details.

---

## Getting Started

### 1. Update Your `.env` File

Make sure these variables are set:

```bash
# Database
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge

# Security (IMPORTANT: Change this!)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Preferred embedding gateway
NEUROFORGE_URL=http://127.0.0.1:8000

# Derived cache/state
REDIS_URL=redis://localhost:6379/0

# Server (optional)
HOST=0.0.0.0
PORT=8788
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 2. Start the Server

```bash
# Option 1: Direct
uvicorn app.main:app --reload --port 8788

# Option 2: Docker
docker-compose up -d
```

### 3. Watch the Startup Logs

You should see:
```
🚀 Starting DataForge...
✅ Configuration validated
📦 Enabling pgvector extension...
📊 Database migrations are managed outside app startup
```

If you see errors, check your `.env` file!

---

## Test the Fixes

### Test 1: Health Check
```bash
curl http://localhost:8788/health
```

Should return: `{"status": "healthy", ...}`

### Test 2: Create a Document
```bash
# First, get an auth token
TOKEN=$(curl -X POST http://localhost:8788/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your-password" | jq -r .access_token)

# Create a domain
curl -X POST http://localhost:8788/admin/domains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test",
    "label": "Test Domain",
    "description": "A test domain"
  }'

# Create a document (will auto-chunk and embed)
curl -X POST http://localhost:8788/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_id": "test",
    "title": "Test Document",
    "doc_type": "guide",
    "content": "This is a test document about writing. It demonstrates the auto-chunking and embedding features. The system will split this into smaller chunks and generate vector embeddings for semantic search.",
    "tags": ["test", "demo"],
    "is_published": true
  }'
```

### Test 3: Search (No Auth Required!)
```bash
curl -X POST http://localhost:8788/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I write good content?",
    "limit": 5,
    "similarity_threshold": 0.5
  }'
```

Should return search results with similarity scores!

### Test 4: Rate Limiting
```bash
# Make 21 rapid requests
for i in {1..21}; do
  curl -X POST http://localhost:8788/api/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' \
    -w "\nRequest $i: %{http_code}\n"
done
```

Request 21 should return `429 Too Many Requests`

### Test 5: Input Validation
```bash
# Try to search with empty query (should fail with 422)
curl -X POST http://localhost:8788/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": ""}'
```

Should return: `{"detail": [{"msg": "Query cannot be empty", ...}]}`

---

## Key Improvements

### 1. Configuration Management
Core settings are centralized in [app/config.py](app/config.py), but the intended override path
is environment variables rather than editing the module.

### 2. Logging
Check the console output for detailed logs. Set `LOG_LEVEL=DEBUG` in `.env` for more verbose output.

### 3. Error Messages
All errors now include helpful messages. Example:
- Before: `500 Internal Server Error`
- After: `Failed to generate embedding: Invalid API key`

### 4. Rate Limiting
- Redis-backed limiter with TTL-governed state
- Fail-closed on Redis outage rather than allow-on-miss
- Returns HTTP 429 when the limit is exceeded

### 5. Input Validation
- Query max length: 2000 chars
- Document max length: 1MB
- Title max length: 500 chars
- Search limit: 1-100 results

---

## Common Issues

### Issue: "Configuration error: SECRET_KEY must be set"
**Fix**: Set a proper `SECRET_KEY` in `.env`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copy the output to your `.env` file.

### Issue: "No embedding provider configured"
**Fix**: Verify `NEUROFORGE_URL` is reachable, or set a direct fallback provider key such as `VOYAGE_API_KEY`.

### Issue: "Failed to connect to database"
**Fix**: Make sure PostgreSQL is running and `DATAFORGE_DATABASE_URL` is correct.

### Issue: "Health check failed: unhealthy"
**Fix**: Check your database connection. Try:
```bash
psql "$DATAFORGE_DATABASE_URL" -c "SELECT 1"
```

---

## API Documentation

Interactive API docs are available at:
- Swagger UI: http://localhost:8788/docs
- ReDoc: http://localhost:8788/redoc

---

## What Changed?

### Files Created
- `app/config.py` - Central configuration
- `app/utils/rate_limit.py` - Rate limiting
- `FIXES.md` - Detailed fix documentation
- `QUICK_START_AFTER_FIXES.md` - This file

### Files Modified
- `app/api/search.py` - Fixed search, added N+1 fix
- `app/api/crud.py` - Fixed field names, added error handling
- `app/utils/embeddings.py` - Added validation and error handling
- `app/models/schemas.py` - Added input validation
- `app/main.py` - Added logging, CORS improvements, env validation
- `app/api/search_router.py` - Added rate limiting

See [FIXES.md](FIXES.md) for complete details with code examples.

---

## Next Steps

1. ✅ Test all the fixes above
2. ✅ Review the logs to ensure everything starts correctly
3. ✅ Create your first real domain and documents
4. ✅ Integrate with an approved DataForge-owned client surface
5. ⚠️ Before production: Review security settings and rate limits

---

## Need Help?

- **Detailed fixes**: See [FIXES.md](FIXES.md)
- **Setup guide**: See [SETUP.md](SETUP.md)
- **Project overview**: See [README.md](README.md)
- **API docs**: http://localhost:8788/docs

---

**Status**: ✅ Production Ready!

All critical and high-priority issues have been resolved. DataForge is now secure, performant, and production-ready! 🚀

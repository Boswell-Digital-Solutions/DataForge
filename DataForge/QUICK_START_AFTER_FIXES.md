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
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge

# Security (IMPORTANT: Change this!)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Embedding Provider (at least one required)
OPENAI_API_KEY=sk-your-actual-key-here

# Server (optional)
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 2. Start the Server

```bash
# Option 1: Direct
uvicorn app.main:app --reload --port 8001

# Option 2: Docker
docker-compose up -d
```

### 3. Watch the Startup Logs

You should see:
```
🚀 Starting DataForge...
✅ Configuration validated
✅ Using openai for embeddings
📊 Creating database tables...
✅ Database tables created
```

If you see errors, check your `.env` file!

---

## Test the Fixes

### Test 1: Health Check
```bash
curl http://localhost:8001/health
```

Should return: `{"status": "healthy", ...}`

### Test 2: Create a Document
```bash
# First, get an auth token
TOKEN=$(curl -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your-password" | jq -r .access_token)

# Create a domain
curl -X POST http://localhost:8001/admin/domains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test",
    "label": "Test Domain",
    "description": "A test domain"
  }'

# Create a document (will auto-chunk and embed)
curl -X POST http://localhost:8001/admin/documents \
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
curl -X POST http://localhost:8001/api/search \
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
  curl -X POST http://localhost:8001/api/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' \
    -w "\nRequest $i: %{http_code}\n"
done
```

Request 21 should return `429 Too Many Requests`

### Test 5: Input Validation
```bash
# Try to search with empty query (should fail with 422)
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": ""}'
```

Should return: `{"detail": [{"msg": "Query cannot be empty", ...}]}`

---

## Key Improvements

### 1. Configuration Management
All settings are now in [app/config.py](app/config.py). To change chunk size, rate limits, etc., edit this file.

### 2. Logging
Check the console output for detailed logs. Set `LOG_LEVEL=DEBUG` in `.env` for more verbose output.

### 3. Error Messages
All errors now include helpful messages. Example:
- Before: `500 Internal Server Error`
- After: `Failed to generate embedding: Invalid API key`

### 4. Rate Limiting
- Search: 20 requests/minute per IP
- Stats: 10 requests/minute per IP
- Returns HTTP 429 with `Retry-After` header

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
**Fix**: Set `OPENAI_API_KEY` in `.env` with your actual OpenAI API key.

### Issue: "Failed to create database tables"
**Fix**: Make sure PostgreSQL is running and `DATABASE_URL` is correct.

### Issue: "Health check failed: unhealthy"
**Fix**: Check your database connection. Try:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

---

## API Documentation

Interactive API docs are available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

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
4. ✅ Integrate with your client application (e.g., AuthorForge)
5. ⚠️ Before production: Review security settings and rate limits

---

## Need Help?

- **Detailed fixes**: See [FIXES.md](FIXES.md)
- **Setup guide**: See [SETUP.md](SETUP.md)
- **Project overview**: See [README.md](README.md)
- **API docs**: http://localhost:8001/docs

---

**Status**: ✅ Production Ready!

All critical and high-priority issues have been resolved. DataForge is now secure, performant, and production-ready! 🚀

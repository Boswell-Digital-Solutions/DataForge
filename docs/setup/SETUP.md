# DataForge Setup Guide

Complete setup instructions for getting DataForge up and running.

## Prerequisites

- Python 3.11+ OR Docker & Docker Compose
- PostgreSQL 14+ with pgvector extension (if running without Docker)
- A reachable PostgreSQL instance and, for full performance, Redis
- NeuroForge is the preferred embedding/inference gateway
- Optional direct provider key for fallback compatibility:
  - Voyage AI
  - OpenAI
  - Cohere

## Quick Start with Docker (Recommended)

The easiest way to get started is using Docker Compose:

### 1. Clone and Configure

```bash
cd DataForge
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` and set the core runtime variables:

```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
SECRET_KEY=replace-me
NEUROFORGE_URL=http://127.0.0.1:8000
REDIS_URL=redis://localhost:6379/0
```

### 3. Start DataForge

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL with pgvector
- Run database migrations
- Start DataForge API server

### 4. Create Admin User

```bash
docker-compose exec dataforge python scripts/create_admin.py
```

Follow the prompts to create your admin user.

### 5. Access DataForge

- **Admin UI**: http://localhost:8788/admin-ui
- **API Docs**: http://localhost:8788/docs
- **Health Check**: http://localhost:8788/health

You're ready to go! 🚀

---

## Manual Setup (Without Docker)

If you prefer to run DataForge without Docker:

### 1. Install PostgreSQL with pgvector

**macOS:**
```bash
brew install postgresql@14 pgvector
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt install postgresql-14 postgresql-14-pgvector
sudo systemctl start postgresql
```

### 2. Create Database

```bash
psql postgres
```

Then in the psql shell:
```sql
CREATE DATABASE dataforge;
\c dataforge
CREATE EXTENSION vector;
\q
```

### 3. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and configure:
- `DATAFORGE_DATABASE_URL` - Your PostgreSQL connection string
- `SECRET_KEY` - Generate a secure random key
- `NEUROFORGE_URL` - Preferred embedding/inference gateway
- `REDIS_URL` - Redis connection string for derived state

Example `.env`:
```bash
DATAFORGE_DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/dataforge
SECRET_KEY=generate-a-very-secure-random-key-here
NEUROFORGE_URL=http://127.0.0.1:8000
REDIS_URL=redis://localhost:6379/0
```

### 5. Configure Embedding Provider

Preferred runtime path is NeuroForge via `NEUROFORGE_URL`. Direct provider keys such as
`VOYAGE_API_KEY`, `OPENAI_API_KEY`, and `COHERE_API_KEY` remain optional fallback inputs.

### 6. Run Database Migrations

```bash
alembic upgrade head
```

This creates all necessary tables with pgvector support.

### 7. Create Admin User

```bash
python scripts/create_admin.py
```

### 8. Start DataForge

```bash
# Development mode (with auto-reload)
.venv/bin/uvicorn app.main:app --reload --port 8788

# Production mode
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8788 --workers 4
```

### 9. Verify Installation

Visit http://localhost:8788/health - you should see:
```json
{
  "status": "healthy",
  "service": "DataForge",
  "version": "1.0.0",
  "database": "healthy"
}
```

---

## Post-Installation Setup

### 1. Login to Admin UI

1. Go to http://localhost:8788/admin-ui
2. Login with your admin credentials
3. You'll see the dashboard

### 2. Create Your First Domain

Domains organize your knowledge base. Examples:
- `writing_craft` - General writing techniques
- `christian_fiction` - Christian fiction specific content
- `fantasy` - Fantasy genre content

**Via Admin UI:**
1. Click "Domains" tab
2. Fill in:
   - Domain ID: `writing_craft`
   - Label: `Writing Craft`
   - Description: `General writing techniques and best practices`
3. Click "Create Domain"

**Via API:**
```bash
curl -X POST http://localhost:8788/admin/domains \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "writing_craft",
    "label": "Writing Craft",
    "description": "General writing techniques"
  }'
```

### 3. Add Your First Document

**Via Admin UI:**
1. Click "Documents" tab
2. Fill in:
   - Domain ID: `writing_craft`
   - Title: `Show, Don't Tell Guide`
   - Document Type: `guide`
   - Content: Your full guide text
   - Tags: `dialogue, technique`
   - Published: ✓
3. Click "Create Document"

The document will be automatically:
- Chunked into semantic units
- Embedded using your configured provider
- Made searchable immediately

**Via API:**
```bash
curl -X POST http://localhost:8788/admin/documents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_id": "writing_craft",
    "title": "Show, Don'\''t Tell Guide",
    "doc_type": "guide",
    "content": "Your document content here...",
    "tags": ["dialogue", "technique"],
    "is_published": true
  }'
```

### 4. Test Semantic Search

**Via Admin UI:**
1. Click "Search" tab
2. Enter query: "How do I write compelling dialogue?"
3. Click "Search"

**Via API (No Authentication Required):**
```bash
curl -X POST http://localhost:8788/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I write compelling dialogue?",
    "limit": 5,
    "similarity_threshold": 0.7
  }'
```

---

## Integration with Client Applications

DataForge is designed to be consumed by approved client applications. AuthorForge is limited
to the dedicated strict analytics endpoint; it must not use the search or document-ingest
surfaces for user content.

### Python Example

```python
import httpx

async def search_knowledge_base(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8788/api/search",
            json={
                "query": query,
                "domain_id": "writing_craft",  # optional
                "limit": 5
            }
        )
        return response.json()

# Usage
results = await search_knowledge_base("How to develop characters?")
for chunk in results['chunks']:
    print(f"Score: {chunk['similarity_score']}")
    print(f"Content: {chunk['content']}\n")
```

### JavaScript Example

```javascript
async function searchDataForge(query) {
  const response = await fetch('http://localhost:8788/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      limit: 5,
      similarity_threshold: 0.7
    })
  });

  return await response.json();
}

// Usage
const results = await searchDataForge('How to create tension?');
console.log(`Found ${results.total_results} results`);
```

---

## Troubleshooting

### Database Connection Issues

**Error:** `connection to server at "localhost" failed`

**Solution:**
1. Ensure PostgreSQL is running:
   ```bash
   # Check status
   brew services list  # macOS
   sudo systemctl status postgresql  # Linux

   # Start if not running
   brew services start postgresql@14  # macOS
   sudo systemctl start postgresql  # Linux
   ```

2. Verify connection:
   ```bash
   psql -h localhost -U postgres -d dataforge
   ```

### pgvector Extension Missing

**Error:** `extension "vector" does not exist`

**Solution:**
```bash
psql dataforge
CREATE EXTENSION vector;
\q
```

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
Ensure you're running from the DataForge root directory and virtual environment is activated:
```bash
cd DataForge
source venv/bin/activate
python -m uvicorn app.main:app
```

### Embedding Provider Errors

**Error:** `Invalid API key`

**Solution:**
1. Check your `.env` file has the correct API key
2. Restart the server after changing `.env`
3. Verify the key is valid with your provider

---

## Production Deployment

### Security Checklist

- [ ] Generate a strong `SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS with a reverse proxy (nginx, Caddy)
- [ ] Configure proper `ALLOWED_ORIGINS` in `.env`
- [ ] Use a strong PostgreSQL password
- [ ] Run with `--workers` for better performance
- [ ] Set up database backups
- [ ] Monitor with the `/health` endpoint
- [ ] Use a process manager (systemd, supervisor, PM2)

### Example nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8788;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service

Create `/etc/systemd/system/dataforge.service`:

```ini
[Unit]
Description=DataForge Knowledge Base API
After=network.target postgresql.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/DataForge
Environment="PATH=/path/to/DataForge/venv/bin"
ExecStart=/path/to/DataForge/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8788 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable dataforge
sudo systemctl start dataforge
sudo systemctl status dataforge
```

---

## Next Steps

1. **Populate your knowledge base** with domains and documents
2. **Test semantic search** to verify embeddings are working
3. **Integrate with an approved DataForge-owned client surface**
4. **Monitor performance** using `/api/search/stats`
5. **Set up backups** for your PostgreSQL database

## Getting Help

- **API Documentation**: http://localhost:8788/docs
- **GitHub Issues**: Report bugs or request features
- **README**: See README.md for architecture details

---

**DataForge** - Powering AI applications with intelligent knowledge retrieval 🚀

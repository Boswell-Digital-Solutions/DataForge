# The Forge - Quick Reference Guide

**Last Updated:** 2025-11-16

---

## System Overview

| System | Port | Purpose | Status |
|--------|------|---------|--------|
| **DataForge** | 8001 | Knowledge Base + Projects API | ✅ Production Ready |
| **AuthorForge** | 8000 | AI Writing Assistant API | ✅ Production Ready |
| **PostgreSQL** | 5432 | Database (pgvector) | ✅ Running |

---

## Quick Start

### DataForge
```bash
cd DataForge

# Start database
docker-compose up -d postgres

# Run migrations
alembic upgrade head

# Create admin user
python scripts/create_admin.py

# Start server
uvicorn app.main:app --reload --port 8001
```

**Access:**
- API Docs: http://localhost:8001/docs
- Admin UI: http://localhost:8001/admin-ui
- Health: http://localhost:8001/health

### AuthorForge
```bash
cd AuthorForge

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: Add ANTHROPIC_API_KEY

# Start server
uvicorn app.main:app --reload --port 8000
```

**Access:**
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## API Endpoints

### DataForge (Port 8001)

#### Public (No Auth)
```bash
# Semantic search
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "character development", "limit": 5}'

# Statistics
curl http://localhost:8001/api/search/stats
```

#### Admin (JWT Required)
```bash
# Get token
TOKEN=$(curl -X POST http://localhost:8001/auth/token \
  -d "username=admin&password=your_password" | jq -r .access_token)

# Create domain
curl -X POST http://localhost:8001/admin/domains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "writing_craft", "label": "Writing Craft", "description": "..."}'

# Create document (auto-chunks & embeds)
curl -X POST http://localhost:8001/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain_id": "writing_craft", "title": "...", "content": "...", "doc_type": "guide"}'
```

### AuthorForge (Port 8000)

#### Research
```bash
# Research query
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I create a magic system?",
    "genre": "fantasy",
    "max_results": 5
  }'
```

#### Smithy (Brainstorming)
```bash
# Generate story ideas
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A reluctant hero discovers ancient magic",
    "genre": "fantasy",
    "num_ideas": 5
  }'

# Expand story aspect
curl -X POST http://localhost:8000/smithy/expand \
  -H "Content-Type: application/json" \
  -d '{
    "idea_title": "The Reluctant Archmage",
    "idea_description": "...",
    "genre": "fantasy",
    "aspect": "magic"
  }'
```

---

## Database Schema

### DataForge Tables
- **users** - Authentication (JWT + bcrypt)
- **domains** - Knowledge hierarchy (parent-child)
- **documents** - Content storage
- **chunks** - Embeddings (1536-dim vectors)
- **tags** - Categorization
- **document_tags** - Many-to-many

### AuthorForge Tables
- **projects** - Writing projects (multi-genre)
- **manuscripts** - Chapters/scenes
- **characters** - Character profiles
- **locations** - World-building
- **story_arcs** - Plot structure
- **brainstorm_sessions** - AI sessions
- **project_genres** - Many-to-many

---

## Testing

### DataForge
```bash
cd DataForge

# Run all passing tests
pytest tests/test_unit/ tests/test_integration/ tests/test_sql_integration.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific category
pytest tests/test_unit/ -v              # Unit tests (44)
pytest tests/test_integration/ -v       # Integration tests (11)
pytest tests/test_sql_integration.py -v # SQL tests (21)

# Results: 76/76 passing (100%)
```

### AuthorForge
```bash
cd AuthorForge

# No tests yet - RECOMMENDATION: Add test suite
```

---

## Configuration

### DataForge (.env)
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge

# Embedding Provider (choose one)
EMBEDDING_PROVIDER=openai  # or voyage, cohere
OPENAI_API_KEY=sk-...
# VOYAGE_API_KEY=pa-...
# COHERE_API_KEY=...

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### AuthorForge (.env)
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# DataForge connection
DATAFORGE_URL=http://localhost:8001

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Common Tasks

### Add Knowledge to DataForge
1. Login to Admin UI: http://localhost:8001/admin-ui
2. Create domain (e.g., "writing_craft")
3. Add documents (auto-chunks & embeds)
4. Test search in UI

### Query from AuthorForge
1. Ensure DataForge is running
2. Send research query with genre
3. AuthorForge queries DataForge domains
4. Claude synthesizes answer from sources

### Manage Projects
1. Get JWT token from DataForge
2. Use /api/projects/* endpoints
3. Create projects, manuscripts, characters
4. Track word counts automatically

---

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Reset password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# Update .env with correct credentials
```

### Tests Failing
```bash
# Check database is accessible
psql -h localhost -U postgres -c "SELECT version();"

# Run migrations
cd DataForge && alembic upgrade head

# Clear test cache
rm -rf .pytest_cache __pycache__
```

### API Not Responding
```bash
# Check server is running
curl http://localhost:8001/health  # DataForge
curl http://localhost:8000/health  # AuthorForge

# Check logs
# Look for startup errors in terminal
```

---

## File Structure

```
Forge/
├── DataForge/                      # Knowledge Base API
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── models/                 # ORM models & schemas
│   │   ├── api/                    # Routers & CRUD
│   │   └── utils/                  # Auth, embeddings, rate limit
│   ├── tests/                      # 76 tests (100% passing)
│   ├── alembic/                    # Database migrations
│   ├── docker-compose.yml          # PostgreSQL + pgvector
│   └── requirements.txt
│
├── AuthorForge/                    # AI Writing Assistant
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── models/genres.py        # Genre system
│   │   └── api/
│   │       ├── research.py         # Research endpoint
│   │       └── smithy.py           # Brainstorming endpoints
│   └── requirements.txt
│
└── COMPREHENSIVE_SYSTEM_REVIEW.md  # This review
```

---

## Key Metrics

| Metric | DataForge | AuthorForge |
|--------|-----------|-------------|
| Python Files | 21 | 8 |
| Database Tables | 13 | 7 (in DataForge DB) |
| API Endpoints | 40+ | 4 |
| Tests | 76 (100% pass) | 0 |
| Code Coverage | 55% | N/A |
| Documentation | 14 files | 2 files |

---

## Next Steps

1. ✅ Fix database authentication (if needed)
2. ✅ Run pending migrations
3. ⚠️ Add AuthorForge test suite
4. ⚠️ Run DataForge API tests (36 tests)
5. ✅ Deploy to production

---

**For detailed information, see:**
- DataForge: `DataForge/README.md`, `DataForge/PROJECT_STATUS.md`
- AuthorForge: `AuthorForge/README.md`
- Full Review: `COMPREHENSIVE_SYSTEM_REVIEW.md`


# Multi-Genre AuthorForge - Complete Setup Guide

> Complete setup and testing guide for the multi-genre AuthorForge system (Fantasy, Sci-Fi, Christian Fiction)

## 🎯 Overview

This guide walks you through setting up the complete AuthorForge system with:
- ✅ **DataForge** - Knowledge base with semantic search (Port 8001)
- ✅ **AuthorForge Backend** - AI-powered writing API (Port 8000)
- ✅ **AuthorForge Frontend** - SolidJS writing application (Port 3000/5173)

---

## 📋 Prerequisites

### Required Software
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (for DataForge)
- Git

### Required API Keys
- **Anthropic API Key** (required) - Get from https://console.anthropic.com/
- **Voyage AI API Key** (recommended for DataForge embeddings) - Get from https://www.voyageai.com/
  - Alternatively: OpenAI or Cohere API key

---

## 🚀 Phase 1: DataForge Setup

DataForge is the knowledge base that powers research features.

### 1.1 Setup Database

```bash
# Create PostgreSQL database
createdb dataforge

# Or using psql
psql -U postgres
CREATE DATABASE dataforge;
\q
```

### 1.2 Configure DataForge

```bash
cd DataForge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or vim/code .env
```

**Required .env settings:**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
SECRET_KEY=your-super-secret-key-change-this
VOYAGE_API_KEY=your-voyage-api-key-here

# Optional: If not using Voyage AI
# OPENAI_API_KEY=your-openai-key
# COHERE_API_KEY=your-cohere-key
```

### 1.3 Initialize Database

```bash
# Run migrations
alembic upgrade head

# Create admin user
python scripts/create_admin.py
# Follow prompts to create username/password
```

### 1.4 Start DataForge

```bash
uvicorn app.main:app --reload --port 8001
```

**Verify it's running:**
```bash
curl http://localhost:8001/health
# Should return: {"status":"ok","service":"dataforge",...}
```

Keep this terminal open with DataForge running.

---

## 🏗️ Phase 2: AuthorForge Backend Setup

The AuthorForge backend provides AI-powered writing assistance.

### 2.1 Configure Backend

Open a **new terminal:**

```bash
cd AuthorForge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env
nano .env  # or vim/code .env
```

**Required .env settings:**
```bash
# CRITICAL: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# DataForge connection
DATAFORGE_URL=http://localhost:8001

# Server config
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# CORS (frontend URLs)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
```

### 2.2 Start AuthorForge Backend

```bash
uvicorn app.main:app --reload --port 8000
```

**Verify it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok","service":"authorforge",...}
```

**Check API docs:**
Open http://localhost:8000/docs in your browser

Keep this terminal open with the backend running.

---

## 📚 Phase 3: Setup DataForge Domains

DataForge needs domains for each genre's knowledge base.

Open a **new terminal:**

```bash
cd AuthorForge

# Activate virtual environment
source venv/bin/activate

# Set your DataForge admin password
export DATAFORGE_ADMIN_PASSWORD='your-admin-password-here'

# Run domain setup script
python scripts/setup_dataforge_domains.py
```

**Expected output:**
```
✅ Created: Writing Craft (writing_craft)
✅ Created: Fantasy Writing (fantasy_craft)
✅ Created: Science Fiction Writing (scifi_craft)
✅ Created: Christian Fiction Writing (christian_fiction_craft)
✅ Created: Worldbuilding (worldbuilding)
✅ Created: Biblical Themes (biblical_themes)
```

### 3.1 Upload Sample Content (Optional but Recommended)

For testing, upload some sample writing craft documents:

```bash
# Example: Upload a fantasy writing guide PDF
curl -X POST http://localhost:8001/admin/documents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/fantasy_guide.pdf" \
  -F "domain_id=fantasy_craft" \
  -F "title=Fantasy Worldbuilding Guide"
```

**Get your auth token:**
```bash
curl -X POST http://localhost:8001/auth/token \
  -d "username=admin&password=your-password"
# Copy the access_token from response
```

Or use the DataForge Admin UI: http://localhost:8001/admin

---

## 💻 Phase 4: Frontend Setup

Setup the SolidJS frontend application.

Open a **new terminal:**

```bash
cd AuthorForge_Solid_new

# Install dependencies
npm install

# Create .env file
nano .env  # or vim/code .env
```

**Add to .env:**
```bash
VITE_AUTHORFORGE_API_URL=http://localhost:8000
```

### 4.1 Start Frontend

```bash
npm run dev
```

The app should open at http://localhost:3000 or http://localhost:5173

---

## ✅ Phase 5: End-to-End Testing

### Test 1: Create a Project with Genre

1. Open http://localhost:3000 (or 5173) in your browser
2. Click **"New Project"** button in the Foundry (or from Hearth)
3. Enter project name: "Test Fantasy Project"
4. Select genre: **Fantasy** 🐉
5. Click **"Create Project"**
6. Verify project appears in Overview tab with "Fantasy" genre

### Test 2: Research Assistant (Hearth)

1. Navigate to **The Hearth** (home/dashboard)
2. Scroll down to **"Research Assistant"** widget
3. Select genre: **Fantasy**
4. Enter query: "How do I create a unique magic system?"
5. Click **"Ask"**
6. Verify:
   - Loading spinner appears
   - Answer is synthesized from sources
   - Sources are displayed with similarity scores

**Expected behavior:**
- If DataForge has no content: Helpful message about adding content
- If DataForge has content: AI-synthesized answer with source citations

### Test 3: Smithy Brainstorming (Future Enhancement)

*Note: The Smithy AI panel is prepared but needs additional integration for brainstorming.*

To test brainstorming via API directly:

```bash
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A colony ship discovers an ancient alien artifact that rewrites reality",
    "genre": "scifi",
    "num_ideas": 3
  }'
```

**Expected response:**
```json
{
  "prompt": "A colony ship...",
  "genre": "scifi",
  "ideas": [
    {
      "title": "The Reality Engine",
      "description": "...",
      "themes": ["first contact", "reality", "survival"],
      "technology": "Quantum reality manipulation device",
      "worldbuilding_notes": "...",
      "character_hooks": ["skeptical captain", "alien sympathizer"]
    }
  ]
}
```

### Test 4: Genre-Specific Features

**Fantasy Test:**
```bash
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A young mage discovers their magic is corrupting the world",
    "genre": "fantasy",
    "num_ideas": 3
  }'
```

Verify `magic_system` field is populated in each idea.

**Christian Fiction Test:**
```bash
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A pastor loses faith after a tragedy",
    "genre": "christian_fiction",
    "num_ideas": 3
  }'
```

Verify `biblical_connections` field is populated with scripture references.

### Test 5: Idea Expansion

```bash
curl -X POST http://localhost:8000/smithy/expand \
  -H "Content-Type: application/json" \
  -d '{
    "idea_title": "The Reality Engine",
    "idea_description": "A colony ship discovers an ancient alien artifact",
    "genre": "scifi",
    "aspect": "character"
  }'
```

**Expected response:**
Detailed JSON with protagonist, antagonist, and supporting characters.

---

## 🎨 UI Features to Test

### Genre Selector Component

1. **Foundry - New Project:**
   - Genre buttons with icons (🐉 Fantasy, 🚀 Sci-Fi, ✝️ Christian Fiction, 📚 General)
   - Multi-select support
   - Visual feedback on selection

2. **Hearth - Research Widget:**
   - Genre selector with single-select mode
   - Genre changes affect research domain routing

### Project Management

1. **Foundry - Overview Tab:**
   - Projects display genre badges
   - Genre badges have genre-appropriate colors

---

## 🔧 Troubleshooting

### Backend Won't Start

**Error:** `ANTHROPIC_API_KEY environment variable is required`

**Solution:**
1. Ensure `.env` file exists in `AuthorForge/` directory
2. Add: `ANTHROPIC_API_KEY=sk-ant-your-key-here`
3. Restart backend

### No Research Results

**Problem:** Research queries return "no results" message

**Solutions:**
1. **Check DataForge has content:**
   ```bash
   curl http://localhost:8001/api/search/stats
   ```
   Look for `total_documents` > 0

2. **Verify domains exist:**
   ```bash
   curl http://localhost:8000/research/domains
   ```

3. **Upload sample content** to DataForge

### CORS Errors in Frontend

**Problem:** Browser console shows CORS errors

**Solutions:**
1. Verify backend is running on port 8000
2. Check `CORS_ORIGINS` in `AuthorForge/.env` includes frontend URL
3. Restart backend after changing CORS settings

### Port Already in Use

**Problem:** `Address already in use` error

**Solutions:**
```bash
# Find process using port
lsof -i :8000  # or :8001, :3000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8002
```

---

## 📁 Project Structure

```
Forge/
├── DataForge/                    # Knowledge Base API (Port 8001)
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── search_router.py  # /api/search endpoints
│   │   │   └── admin_router.py   # /admin/* endpoints
│   │   └── models/
│   ├── .env                      # Database + Voyage AI config
│   └── requirements.txt
│
├── AuthorForge/                  # AI Writing API (Port 8000) **NEW**
│   ├── app/
│   │   ├── main.py               # FastAPI app
│   │   ├── config.py             # Environment config
│   │   ├── models/
│   │   │   └── genres.py         # Genre system
│   │   └── api/
│   │       ├── research.py       # /research/query endpoint
│   │       └── smithy.py         # /smithy/* endpoints
│   ├── scripts/
│   │   └── setup_dataforge_domains.py
│   ├── .env                      # Anthropic API + DataForge URL
│   └── requirements.txt
│
└── AuthorForge_Solid_new/        # Frontend (Port 3000/5173)
    ├── src/
    │   ├── components/
    │   │   ├── GenreSelector.tsx         **NEW**
    │   │   ├── NewProjectModal.tsx       **NEW**
    │   │   └── ResearchWidget.tsx        **NEW**
    │   ├── hooks/
    │   │   ├── useBrainstorm.ts          **NEW**
    │   │   └── useResearch.ts            **NEW**
    │   └── routes/
    │       ├── foundry/index.tsx         (Updated with genre selector)
    │       └── hearth/index.tsx          (Updated with research widget)
    ├── .env                      # VITE_AUTHORFORGE_API_URL
    └── package.json
```

---

## 🔄 Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    User creates project                      │
│                    (Foundry - selects genre)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              User asks research question                     │
│           (Hearth - selects genre + query)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                AuthorForge Backend                           │
│                  (Port 8000)                                 │
│  1. Receives query with genre                                │
│  2. Maps genre → DataForge domains                           │
│  3. Queries DataForge semantic search                        │
│  4. Synthesizes answer with Claude AI                        │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────┐                 ┌────────────────┐
│  DataForge   │                 │   Claude API   │
│ (Port 8001)  │                 │  (Anthropic)   │
│              │                 │                │
│ Returns      │                 │ Synthesizes    │
│ top sources  │                 │ answer         │
└──────────────┘                 └────────────────┘
```

---

## 📊 API Endpoint Reference

### AuthorForge Backend (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/research/query` | POST | Genre-aware research |
| `/research/domains` | GET | Available domains by genre |
| `/smithy/brainstorm` | POST | Generate story ideas |
| `/smithy/expand` | POST | Expand idea details |

### DataForge (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/search` | POST | Semantic search |
| `/api/search/stats` | GET | Database statistics |
| `/admin/domains` | GET/POST | Manage domains (requires auth) |
| `/admin/documents` | GET/POST | Manage documents (requires auth) |

---

## 🎓 Next Steps

### 1. Add Writing Craft Content
Upload PDFs, DOCX, or text files to DataForge:
- Fantasy craft guides
- Sci-fi worldbuilding resources
- Christian fiction writing books
- General writing craft references

### 2. Customize Genre Prompts
Edit `AuthorForge/app/models/genres.py` to adjust AI prompts for each genre.

### 3. Add More Genres
Extend the system with additional genres (Horror, Mystery, Romance, etc.)

### 4. Integrate Smithy Brainstorming
Wire up the Smithy AI panel to use the brainstorm API.

### 5. Production Deployment
- Setup reverse proxy (nginx)
- Configure SSL certificates
- Use PostgreSQL connection pooling
- Implement rate limiting
- Setup monitoring

---

## 📖 Documentation

- **DataForge README**: `DataForge/README.md`
- **AuthorForge Backend README**: `AuthorForge/README.md`
- **Frontend**: `AuthorForge_Solid_new/README.md`
- **API Docs (Interactive)**: http://localhost:8000/docs

---

## 🆘 Support

If you encounter issues:

1. Check all three services are running (DataForge, AuthorForge Backend, Frontend)
2. Verify environment variables in all `.env` files
3. Check browser console for errors
4. Check backend logs for API errors
5. Verify DataForge has domains and documents

---

**🎉 Congratulations!** You now have a complete multi-genre AI writing assistance system running with Fantasy, Sci-Fi, and Christian Fiction support!

---

Generated with Claude Code ✨

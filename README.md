# The Forge

A unified workspace containing the complete AuthorForge ecosystem.

## Projects

### 🔧 [DataForge](./DataForge/)
**Knowledge Base Management System with Semantic Search**

A standalone backend service that provides intelligent knowledge retrieval using vector embeddings and PostgreSQL with pgvector. Powers AuthorForge's writing craft knowledge base.

**Key Features:**
- Semantic vector search
- Auto-chunking and embedding
- Domain-based organization
- JWT authentication
- REST API + Admin UI
- Docker support

**Tech Stack:** FastAPI, PostgreSQL, pgvector, OpenAI/Voyage AI/Cohere

**Status:** ✅ Production Ready

---

### ✍️ [AuthorForge_Solid_new](./AuthorForge_Solid_new/)
**AI-Powered Writing Assistant for Christian Fiction Authors**

A comprehensive writing application built with SolidJS and Rust (Tauri), providing writers with tools, templates, and AI assistance for crafting compelling stories.

**Key Features:**
- Multi-workspace system (Smithy, Hearth, Anvil, Ember, Forge)
- AI writing assistance with Claude
- Project management and organization
- Character development tools
- Plot structuring
- Writing templates and patterns
- Dark/light theme support

**Tech Stack:** SolidJS, Tauri (Rust), TailwindCSS, Claude AI

**Status:** 🚧 Active Development

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AuthorForge                          │
│              (SolidJS + Tauri Frontend)                 │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │ Smithy   │ Hearth   │ Anvil    │ Ember    │        │
│  │ (Write)  │ (Learn)  │ (Craft)  │ (Tools)  │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
│                      │                                  │
│                      │ Search API                       │
│                      ▼                                  │
│            ┌─────────────────────┐                     │
│            │     DataForge       │                     │
│            │ (Knowledge Base)    │                     │
│            └─────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

## Getting Started

### DataForge Setup

```bash
cd DataForge

# With Docker (recommended)
docker-compose up -d
docker-compose exec dataforge python scripts/create_admin.py

# Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/create_admin.py
uvicorn app.main:app --reload --port 8001
```

See [DataForge/SETUP.md](./DataForge/SETUP.md) for detailed instructions.

### AuthorForge Setup

```bash
cd AuthorForge_Solid_new

# Install dependencies
npm install

# Development mode
npm run dev

# Build
npm run build
```

## Integration

AuthorForge connects to DataForge for knowledge base queries:

```javascript
// In AuthorForge
const response = await fetch('http://localhost:8001/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "How do I develop compelling characters?",
    domain_id: "writing_craft",
    limit: 5
  })
});
```

## Project Goals

**The Forge** is designed to provide Christian fiction authors with:

1. **Knowledge at Your Fingertips** - Semantic search of writing craft knowledge (DataForge)
2. **Structured Writing Environment** - Organized workspaces for different writing stages (AuthorForge)
3. **AI-Powered Assistance** - Integration with Claude AI for writing support
4. **Best Practices** - Templates and patterns for Christian fiction writing
5. **Project Management** - Tools to organize characters, plots, and worldbuilding

## Directory Structure

```
Forge/
├── DataForge/                  # Backend knowledge base API
│   ├── app/                    # FastAPI application
│   ├── alembic/                # Database migrations
│   ├── templates/              # Admin UI
│   ├── docker-compose.yml
│   └── README.md
│
└── AuthorForge_Solid_new/      # Frontend writing application
    ├── src/                    # SolidJS source code
    ├── src-tauri/              # Rust Tauri backend
    └── README.md
```

## Contributing

Both projects are under active development. See individual project READMEs for contribution guidelines.

## License

See individual project licenses.

---

**The Forge** - Crafting Stories, Powered by Knowledge 🔥✍️

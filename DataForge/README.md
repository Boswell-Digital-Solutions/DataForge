# DataForge

Standalone Knowledge Base Management System with Semantic Search

DataForge is a PostgreSQL-backed knowledge base management system designed to store, organize, and search documents using semantic vector search. It's built to be consumed by client applications like AuthorForge.

## Quick Start

1. **Install PostgreSQL with pgvector**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql-14 postgresql-14-pgvector

   # macOS
   brew install postgresql@14 pgvector
   ```

2. **Create Database**
   ```bash
   psql postgres
   CREATE DATABASE dataforge;
   \c dataforge
   CREATE EXTENSION vector;
   \q
   ```

3. **Setup Python Environment**
   ```bash
   cd DataForge
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Create Admin User**
   ```bash
   python scripts/create_admin.py
   ```

6. **Run DataForge**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

## API Endpoints

- Public Search API: `POST /api/search`
- Admin UI: `http://localhost:8001/admin-ui`
- API Docs: `http://localhost:8001/docs`
- Health Check: `http://localhost:8001/health`

## Architecture

```
┌─────────────┐      Search API       ┌──────────────┐
│ AuthorForge │ ←──────────────────→  │  DataForge   │
│   (Client)  │   /api/search POST    │   (Server)   │
└─────────────┘                        └──────────────┘
                                              │
                                              ↓
                                       ┌──────────────┐
                                       │ PostgreSQL + │
                                       │   pgvector   │
                                       └──────────────┘
```

## License

MIT License

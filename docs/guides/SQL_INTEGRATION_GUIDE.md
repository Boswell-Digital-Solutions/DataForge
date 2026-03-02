# SQL Integration Guide: AuthorForge → DataForge Database

This guide documents the complete SQL integration between AuthorForge and DataForge's PostgreSQL database.

> Runtime note: DataForge's current database env var is `DATAFORGE_DATABASE_URL`, and the
> default local API port is `8788`.

## Overview

AuthorForge now uses DataForge's PostgreSQL database for persistent storage of:
- Projects (with multi-genre support)
- Manuscripts (chapters/sections)
- Characters
- Locations
- Story Arcs
- Brainstorm Sessions

All AuthorForge tables share the same database as DataForge's existing tables (users, domains, documents, chunks).

## Database Schema

### Tables Created

1. **projects** - Core project data
   - Links to `users.id` (CASCADE delete)
   - Stores metadata, word counts, settings JSON
   - Many-to-many relationship with genres

2. **project_genres** - Association table
   - Links projects to multiple genres (fantasy, scifi, christian_fiction, general)

3. **manuscripts** - Chapter/section content
   - Links to `projects.id` (CASCADE delete)
   - Auto-calculates word counts
   - Ordered by chapter_number

4. **characters** - Character profiles
   - Links to `projects.id` (CASCADE delete)
   - JSON fields for profile and arc_data

5. **locations** - Worldbuilding locations
   - Links to `projects.id` (CASCADE delete)
   - JSON field for flexible details

6. **story_arcs** - Story structure
   - Links to `projects.id` (CASCADE delete)
   - JSON fields for beats and graph_data

7. **brainstorm_sessions** - AI brainstorming history
   - Links to `users.id` and `projects.id`
   - Stores prompt, genre, and generated ideas JSON

### Enums

- **genreenum**: fantasy, scifi, christian_fiction, general
- **projectstatus**: draft, active, completed, archived

## Step 1: Run Database Migration

### Prerequisites

1. PostgreSQL must be running
2. DataForge database must exist
3. Alembic must be configured (already done in DataForge)

### Run Migration

```bash
cd /home/charles/projects/Coding2025/Forge/DataForge

# Review the migration
python3 -m alembic history

# Run the migration
python3 -m alembic upgrade head

# Verify tables were created
psql -U postgres -d dataforge -c "\dt"
```

### Verify Schema

```bash
# Check projects table
psql -U postgres -d dataforge -c "\d projects"

# Check enums
psql -U postgres -d dataforge -c "\dT genreenum"
psql -U postgres -d dataforge -c "\dT projectstatus"

# Check all AuthorForge tables
psql -U postgres -d dataforge -c "
  SELECT tablename FROM pg_tables
  WHERE tablename IN ('projects', 'manuscripts', 'characters', 'locations', 'story_arcs', 'brainstorm_sessions', 'project_genres')
  ORDER BY tablename;
"
```

## Step 2: Configure AuthorForge Backend

### Database Connection

Update `AuthorForge/app/config.py` to use DataForge's database:

```python
# AuthorForge/app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Use DataForge's database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/dataforge"  # Same DB as DataForge
    )

    # DataForge API for semantic search
    DATAFORGE_API_URL: str = os.getenv("DATAFORGE_API_URL", "http://localhost:8788")

    # Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # JWT Settings (should match DataForge)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

### Create .env File

```bash
# AuthorForge/.env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/dataforge
DATAFORGE_API_URL=http://localhost:8788
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SECRET_KEY=your_jwt_secret_key_here  # Must match DataForge's secret key
```

### Database Session

Create `AuthorForge/app/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models (reuse DataForge's models)
Base = declarative_base()

# Dependency for routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Authentication Integration

AuthorForge should use DataForge's authentication:

```python
# AuthorForge/app/utils/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings

# Import DataForge's User model
import sys
sys.path.append("/home/charles/projects/Coding2025/Forge/DataForge")
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8788/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user
```

## Step 3: Update API Endpoints

### Projects API in DataForge

All project CRUD operations are now available in DataForge at:

```
GET    /api/projects                    - List user's projects
POST   /api/projects                    - Create project
GET    /api/projects/{id}               - Get project details
PATCH  /api/projects/{id}               - Update project
DELETE /api/projects/{id}               - Delete project

GET    /api/projects/{id}/manuscripts   - List manuscripts
POST   /api/projects/manuscripts        - Create manuscript
PATCH  /api/projects/manuscripts/{id}   - Update manuscript
DELETE /api/projects/manuscripts/{id}   - Delete manuscript

POST   /api/projects/characters         - Create character
PATCH  /api/projects/characters/{id}    - Update character
DELETE /api/projects/characters/{id}    - Delete character

POST   /api/projects/locations          - Create location
PATCH  /api/projects/locations/{id}     - Update location
DELETE /api/projects/locations/{id}     - Delete location

POST   /api/projects/story-arcs         - Create story arc
PATCH  /api/projects/story-arcs/{id}    - Update story arc
DELETE /api/projects/story-arcs/{id}    - Delete story arc

GET    /api/projects/brainstorm-sessions        - List sessions
POST   /api/projects/brainstorm-sessions        - Create session
```

All endpoints require JWT authentication (Bearer token).

### AuthorForge API Updates

AuthorForge's Smithy API should now save brainstorm sessions:

```python
# AuthorForge/app/api/smithy.py
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import get_current_user
import sys
sys.path.append("/home/charles/projects/Coding2025/Forge/DataForge")
from app.models.models import User
from app.api.projects_crud import create_brainstorm_session
from app.models.authorforge_schemas import BrainstormSessionCreate

@router.post("/brainstorm", response_model=BrainstormResponse)
async def brainstorm_ideas(
    request: BrainstormRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ... existing brainstorming logic ...

    # Save to database
    session_data = BrainstormSessionCreate(
        project_id=request.project_id,  # Optional
        prompt=request.prompt,
        genre=request.genre,
        subgenre=request.subgenre,
        ideas=ideas  # List of StoryIdea dicts
    )
    create_brainstorm_session(db, session_data, current_user.id)

    return BrainstormResponse(...)
```

## Step 4: Update Frontend

### Environment Variables

Update `AuthorForge_Solid_new/.env`:

```bash
# Use DataForge for project storage
VITE_DATAFORGE_API_URL=http://localhost:8788
VITE_AUTHORFORGE_API_URL=http://localhost:8000

# Authentication
VITE_AUTH_TOKEN_KEY=authorforge_token
```

### API Hooks Update

Update project hooks to use DataForge API:

```typescript
// src/hooks/useProjects.ts
const DATAFORGE_API_URL = import.meta.env.VITE_DATAFORGE_API_URL || "http://localhost:8788";

export function useProjects() {
  const [projects, setProjects] = createSignal<Project[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);

  const getAuthHeader = () => {
    const token = localStorage.getItem('authorforge_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  };

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${DATAFORGE_API_URL}/api/projects`, {
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.statusText}`);
      }

      const data = await response.json();
      setProjects(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch projects";
      setError(message);
      console.error("Fetch projects error:", err);
    } finally {
      setLoading(false);
    }
  };

  const createProject = async (projectData: ProjectCreate): Promise<Project> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${DATAFORGE_API_URL}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify(projectData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to create project: ${response.statusText}`);
      }

      const newProject = await response.json();
      setProjects([...projects(), newProject]);
      return newProject;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create project";
      setError(message);
      console.error("Create project error:", err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { projects, loading, error, fetchProjects, createProject };
}
```

### Remove IndexedDB

Remove or deprecate IndexedDB storage code in favor of API calls:

```typescript
// Remove src/lib/db.ts or mark as deprecated
// Update all components to use API hooks instead
```

## Step 5: Testing

### 1. Database Testing

```bash
# Start PostgreSQL
sudo service postgresql start

# Run migration
cd /home/charles/projects/Coding2025/Forge/DataForge
python3 -m alembic upgrade head

# Verify tables
psql -U postgres -d dataforge -c "SELECT tablename FROM pg_tables WHERE tablename LIKE '%project%' OR tablename LIKE '%manuscript%';"
```

### 2. Backend Testing

```bash
# Start DataForge (port 8788)
cd /home/charles/projects/Coding2025/Forge/DataForge
uvicorn app.main:app --reload --port 8788

# Start AuthorForge (port 8000)
cd /home/charles/projects/Coding2025/Forge/AuthorForge
uvicorn app.main:app --reload --port 8000

# Test API docs
# DataForge: http://localhost:8788/docs
# AuthorForge: http://localhost:8000/docs
```

### 3. API Testing with curl

```bash
# 1. Login to get token
TOKEN=$(curl -X POST http://localhost:8788/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass" \
  | jq -r .access_token)

# 2. Create a project
curl -X POST http://localhost:8788/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Fantasy Novel",
    "genres": ["fantasy", "general"],
    "description": "A test project",
    "target_word_count": 80000
  }'

# 3. List projects
curl -X GET http://localhost:8788/api/projects \
  -H "Authorization: Bearer $TOKEN"

# 4. Create a manuscript
curl -X POST http://localhost:8788/api/projects/manuscripts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "title": "Chapter 1: The Beginning",
    "content": "It was a dark and stormy night...",
    "chapter_number": 1
  }'

# 5. Create a character
curl -X POST http://localhost:8788/api/projects/characters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Aria Moonwhisper",
    "role": "Protagonist",
    "profile": {
      "age": 24,
      "appearance": "Silver hair, violet eyes",
      "personality": "Brave but cautious",
      "backstory": "Orphaned at age 10..."
    }
  }'
```

### 4. Database Verification

```sql
-- Connect to database
psql -U postgres -d dataforge

-- Check project was created
SELECT id, name, status, word_count FROM projects;

-- Check genres association
SELECT p.name, g.genre
FROM projects p
JOIN project_genres pg ON p.id = pg.project_id
JOIN genreenum g ON pg.genre = g.genre;

-- Check manuscript with word count
SELECT id, project_id, title, word_count, chapter_number FROM manuscripts;

-- Check characters
SELECT id, project_id, name, role FROM characters;

-- Verify cascade delete (delete project, check if manuscripts deleted)
DELETE FROM projects WHERE id = 1;
SELECT COUNT(*) FROM manuscripts WHERE project_id = 1;  -- Should be 0
```

### 5. Frontend Testing

```bash
# Start frontend dev server
cd /home/charles/projects/Coding2025/Forge/AuthorForge_Solid_new
npm run dev

# Test in browser:
# 1. Login at http://localhost:3000
# 2. Navigate to Foundry
# 3. Click "New Project"
# 4. Select genres (Fantasy, Sci-Fi, Christian Fiction)
# 5. Submit form
# 6. Verify project appears in list
# 7. Click project to verify it loads from database
```

## Troubleshooting

### Migration Fails

```bash
# Check database connection
psql -U postgres -d dataforge -c "SELECT version();"

# Check Alembic configuration
cat alembic.ini | grep sqlalchemy.url

# Reset migration (if needed)
python3 -m alembic downgrade -1
python3 -m alembic upgrade head
```

### Authentication Errors

- Verify SECRET_KEY matches between DataForge and AuthorForge
- Check token is being passed in Authorization header
- Verify user exists in DataForge's users table

### Word Count Not Updating

```sql
-- Manually trigger word count update
UPDATE projects SET word_count = (
  SELECT COALESCE(SUM(word_count), 0)
  FROM manuscripts
  WHERE project_id = projects.id
) WHERE id = 1;
```

### Foreign Key Violations

```sql
-- Check user exists before creating project
SELECT id, username FROM users;

-- Check project exists before creating manuscript
SELECT id, name FROM projects WHERE user_id = 1;
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                      │
│                        (dataforge)                           │
├─────────────────────────────────────────────────────────────┤
│  DataForge Tables:        │  AuthorForge Tables:             │
│  - users                  │  - projects ───┐                 │
│  - domains                │  - project_genres (M2M)          │
│  - documents              │  - manuscripts                   │
│  - chunks                 │  - characters                    │
│  - document_tags          │  - locations                     │
│                           │  - story_arcs                    │
│                           │  - brainstorm_sessions           │
└───────────────────────────┴──────────────────────────────────┘
                 ▲                          ▲
                 │                          │
                 │ SQLAlchemy               │ SQLAlchemy
                 │                          │
        ┌────────┴────────┐        ┌────────┴────────┐
        │   DataForge     │        │  AuthorForge    │
        │   FastAPI       │◄───────┤   FastAPI       │
        │   Port 8001     │ Research│   Port 8000     │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 │ REST API                 │ REST API
                 │                          │
        ┌────────┴──────────────────────────┴────────┐
        │         SolidJS Frontend (Vite)            │
        │           http://localhost:3000            │
        └────────────────────────────────────────────┘
```

## Summary

The SQL integration is complete with:

✅ **Database Schema**: 7 new tables + 2 enums in DataForge database
✅ **Migration**: Alembic migration ready to run
✅ **Models**: SQLAlchemy models with proper relationships
✅ **Schemas**: Pydantic schemas for validation
✅ **CRUD Operations**: Complete operations in `projects_crud.py`
✅ **API Endpoints**: RESTful endpoints in DataForge at `/api/projects/*`
✅ **Authentication**: JWT-based auth using DataForge's user system
✅ **Cascading Deletes**: Automatic cleanup of related records
✅ **Word Count Tracking**: Automatic calculation from manuscripts

Next steps:
1. Run the migration when PostgreSQL is available
2. Update AuthorForge backend configuration
3. Update frontend to use database API
4. Test end-to-end integration

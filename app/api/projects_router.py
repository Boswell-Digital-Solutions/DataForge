"""
Projects API Router for AuthorForge

Provides endpoints for project management, manuscripts, characters, etc.
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import User
from app.models.authorforge_schemas import (
    ProjectCreate, ProjectUpdate, Project as ProjectSchema, ProjectSummary,
    ManuscriptCreate, ManuscriptUpdate, Manuscript as ManuscriptSchema,
    CharacterCreate, CharacterUpdate, Character as CharacterSchema,
    LocationCreate, LocationUpdate, Location as LocationSchema,
    StoryArcCreate, StoryArcUpdate, StoryArc as StoryArcSchema,
    BrainstormSessionCreate, BrainstormSession as BrainstormSessionSchema,
    ProjectStatusEnum
)
from app.api import projects_crud
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ============================================
# Projects
# ============================================

@router.get("", response_model=List[ProjectSummary])
def list_projects(
    status: Optional[ProjectStatusEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects for the current user"""
    projects = projects_crud.get_user_projects(db, current_user.id, status=status)
    return projects


@router.post("", response_model=ProjectSchema)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    return projects_crud.create_project(db, project, current_user.id)


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific project"""
    project = projects_crud.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectSchema)
@router.patch("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project"""
    project = projects_crud.update_project(db, project_id, current_user.id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project"""
    success = projects_crud.delete_project(db, project_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


# ============================================
# Manuscripts
# ============================================

@router.get("/{project_id}/manuscripts", response_model=List[ManuscriptSchema])
def list_manuscripts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all manuscripts for a project"""
    return projects_crud.get_manuscripts(db, project_id, current_user.id)


@router.post("/manuscripts", response_model=ManuscriptSchema, status_code=status.HTTP_201_CREATED)
def create_manuscript(
    manuscript: ManuscriptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new manuscript"""
    db_manuscript = projects_crud.create_manuscript(db, manuscript, current_user.id)
    if not db_manuscript:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_manuscript


@router.patch("/manuscripts/{manuscript_id}", response_model=ManuscriptSchema)
def update_manuscript(
    manuscript_id: int,
    manuscript_update: ManuscriptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a manuscript"""
    manuscript = projects_crud.update_manuscript(db, manuscript_id, current_user.id, manuscript_update)
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    return manuscript


@router.delete("/manuscripts/{manuscript_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manuscript(
    manuscript_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a manuscript"""
    success = projects_crud.delete_manuscript(db, manuscript_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Manuscript not found")


# ============================================
# Characters
# ============================================

@router.get("/{project_id}/characters", response_model=List[CharacterSchema])
def list_characters(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all characters for a project"""
    return projects_crud.get_characters(db, project_id, current_user.id)


@router.post("/characters", response_model=CharacterSchema, status_code=status.HTTP_201_CREATED)
def create_character(
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new character"""
    db_character = projects_crud.create_character(db, character, current_user.id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_character


@router.patch("/characters/{character_id}", response_model=CharacterSchema)
def update_character(
    character_id: int,
    character_update: CharacterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a character"""
    character = projects_crud.update_character(db, character_id, current_user.id, character_update)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.delete("/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a character"""
    success = projects_crud.delete_character(db, character_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")


# ============================================
# Locations
# ============================================

@router.get("/{project_id}/locations", response_model=List[LocationSchema])
def list_locations(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all locations for a project"""
    return projects_crud.get_locations(db, project_id, current_user.id)


@router.post("/locations", response_model=LocationSchema, status_code=status.HTTP_201_CREATED)
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new location"""
    db_location = projects_crud.create_location(db, location, current_user.id)
    if not db_location:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_location


# ============================================
# Story Arcs
# ============================================

@router.get("/{project_id}/story-arcs", response_model=List[StoryArcSchema])
def list_story_arcs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all story arcs for a project"""
    return projects_crud.get_story_arcs(db, project_id, current_user.id)


@router.post("/story-arcs", response_model=StoryArcSchema, status_code=status.HTTP_201_CREATED)
def create_story_arc(
    story_arc: StoryArcCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new story arc"""
    db_arc = projects_crud.create_story_arc(db, story_arc, current_user.id)
    if not db_arc:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_arc


# ============================================
# Brainstorm Sessions
# ============================================

@router.get("/brainstorm-sessions", response_model=List[BrainstormSessionSchema])
def list_brainstorm_sessions(
    project_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get brainstorm sessions for the current user"""
    return projects_crud.get_brainstorm_sessions(db, current_user.id, project_id, limit)


@router.post("/brainstorm-sessions", response_model=BrainstormSessionSchema, status_code=status.HTTP_201_CREATED)
def create_brainstorm_session(
    session: BrainstormSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new brainstorm session"""
    return projects_crud.create_brainstorm_session(db, session, current_user.id)

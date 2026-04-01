"""
CRUD operations for AuthorForge projects and related entities.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, bindparam, text
from typing import List, Optional
from datetime import datetime, UTC

from app.models.authorforge_models import (
    Project, Manuscript, Character, Location, StoryArc,
    BrainstormSession, GenreEnum
)
from app.models.authorforge_schemas import (
    ProjectCreate, ProjectUpdate,
    ManuscriptCreate, ManuscriptUpdate,
    CharacterCreate, CharacterUpdate,
    LocationCreate, LocationUpdate,
    StoryArcCreate, StoryArcUpdate,
    BrainstormSessionCreate
)


def _normalize_project_status(status: Optional[object]) -> Optional[str]:
    """Convert schema enum or raw status text to the stored lowercase value."""
    if status is None:
        return None
    raw_value = getattr(status, "value", status)
    return str(raw_value).lower()


def _load_genres(db: Session, project: Optional[Project]) -> Optional[Project]:
    """Load genres from the association table onto the project object."""
    if project is None:
        return None
    rows = db.execute(
        text("SELECT genre FROM project_genres WHERE project_id = :pid"),
        {"pid": project.id}
    ).fetchall()
    project.genres = [GenreEnum(r[0]) for r in rows]
    return project


def _load_genres_list(db: Session, projects: List[Project]) -> List[Project]:
    """Load genres for a list of projects."""
    if not projects:
        return projects

    project_ids = [project.id for project in projects]
    rows = db.execute(
        text(
            "SELECT project_id, genre FROM project_genres "
            "WHERE project_id IN :project_ids"
        ).bindparams(bindparam("project_ids", expanding=True)),
        {"project_ids": project_ids},
    ).fetchall()

    genres_by_project = {project_id: [] for project_id in project_ids}
    for project_id, genre in rows:
        genres_by_project.setdefault(project_id, []).append(GenreEnum(genre))

    for project in projects:
        project.genres = genres_by_project.get(project.id, [])
    return projects


# ============================================
# Projects
# ============================================

def get_user_projects(db: Session, user_id: int, status: Optional[object] = None) -> List[Project]:
    """Get all projects for a user"""
    query = db.query(Project).filter(Project.user_id == user_id)
    if status:
        query = query.filter(Project.status == _normalize_project_status(status))
    return _load_genres_list(db, query.order_by(Project.last_edited_at.desc().nullsfirst(), Project.updated_at.desc()).all())


def get_project(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """Get a specific project by ID"""
    project = db.query(Project).filter(
        and_(Project.id == project_id, Project.user_id == user_id)
    ).first()
    return _load_genres(db, project)


def create_project(db: Session, project: ProjectCreate, user_id: int) -> Project:
    """Create a new project"""
    db_project = Project(
        user_id=user_id,
        name=project.name,
        description=project.description,
        status=_normalize_project_status(project.status),
        target_word_count=project.target_word_count,
        settings=project.settings,
        word_count=0
    )
    db.add(db_project)
    db.flush()  # Get the ID before adding genres

    # Add genres
    for genre in project.genres:
        db.execute(
            text("INSERT INTO project_genres (project_id, genre) VALUES (:project_id, :genre)"),
            {"project_id": db_project.id, "genre": genre.value}
        )

    db.commit()
    db.refresh(db_project)
    return _load_genres(db, db_project)


def update_project(db: Session, project_id: int, user_id: int, project_update: ProjectUpdate) -> Optional[Project]:
    """Update a project"""
    db_project = get_project(db, project_id, user_id)
    if not db_project:
        return None

    update_data = project_update.model_dump(exclude_unset=True)

    # Handle genres separately
    if "genres" in update_data:
        genres = update_data.pop("genres")
        # Remove existing genres
        db.execute(
            text("DELETE FROM project_genres WHERE project_id = :project_id"),
            {"project_id": project_id}
        )
        # Add new genres
        for genre in genres:
            db.execute(
                text("INSERT INTO project_genres (project_id, genre) VALUES (:project_id, :genre)"),
                {"project_id": project_id, "genre": genre.value}
            )

    # Update other fields
    for field, value in update_data.items():
        if field == "status":
            value = _normalize_project_status(value)
        setattr(db_project, field, value)

    db_project.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_project)
    return _load_genres(db, db_project)


def delete_project(db: Session, project_id: int, user_id: int) -> bool:
    """Delete a project"""
    deleted_rows = db.query(Project).filter(
        and_(Project.id == project_id, Project.user_id == user_id)
    ).delete(synchronize_session=False)
    if deleted_rows == 0:
        return False

    db.commit()
    return True


def update_project_word_count(db: Session, project_id: int) -> Optional[Project]:
    """Recalculate and update project word count from manuscripts"""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        return None

    total = db.query(db.func.sum(Manuscript.word_count)).filter(
        Manuscript.project_id == project_id
    ).scalar() or 0

    db_project.word_count = total
    db_project.last_edited_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_project)
    return db_project


# ============================================
# Manuscripts
# ============================================

def get_manuscripts(db: Session, project_id: int, user_id: int) -> List[Manuscript]:
    """Get all manuscripts for a project"""
    # Verify user owns the project
    project = get_project(db, project_id, user_id)
    if not project:
        return []

    return db.query(Manuscript).filter(
        Manuscript.project_id == project_id
    ).order_by(Manuscript.order_index, Manuscript.chapter_number).all()


def get_manuscript(db: Session, manuscript_id: int, user_id: int) -> Optional[Manuscript]:
    """Get a specific manuscript"""
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        return None

    # Verify user owns the project
    project = get_project(db, manuscript.project_id, user_id)
    if not project:
        return None

    return manuscript


def create_manuscript(db: Session, manuscript: ManuscriptCreate, user_id: int) -> Optional[Manuscript]:
    """Create a new manuscript"""
    # Verify user owns the project
    project = get_project(db, manuscript.project_id, user_id)
    if not project:
        return None

    # Calculate word count
    word_count = len(manuscript.content.split()) if manuscript.content else 0

    db_manuscript = Manuscript(
        **manuscript.model_dump(),
        word_count=word_count
    )
    db.add(db_manuscript)
    db.commit()
    db.refresh(db_manuscript)

    # Update project word count
    update_project_word_count(db, manuscript.project_id)

    return db_manuscript


def update_manuscript(
    db: Session, manuscript_id: int, user_id: int, manuscript_update: ManuscriptUpdate
) -> Optional[Manuscript]:
    """Update a manuscript"""
    db_manuscript = get_manuscript(db, manuscript_id, user_id)
    if not db_manuscript:
        return None

    update_data = manuscript_update.model_dump(exclude_unset=True)

    # Recalculate word count if content changed
    if "content" in update_data:
        content = update_data["content"]
        update_data["word_count"] = len(content.split()) if content else 0

    for field, value in update_data.items():
        setattr(db_manuscript, field, value)

    db_manuscript.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_manuscript)

    # Update project word count and last_edited_at
    update_project_word_count(db, db_manuscript.project_id)

    return db_manuscript


def delete_manuscript(db: Session, manuscript_id: int, user_id: int) -> bool:
    """Delete a manuscript"""
    db_manuscript = get_manuscript(db, manuscript_id, user_id)
    if not db_manuscript:
        return False

    project_id = db_manuscript.project_id
    db.delete(db_manuscript)
    db.commit()

    # Update project word count
    update_project_word_count(db, project_id)

    return True


# ============================================
# Characters
# ============================================

def get_characters(db: Session, project_id: int, user_id: int) -> List[Character]:
    """Get all characters for a project"""
    project = get_project(db, project_id, user_id)
    if not project:
        return []

    return db.query(Character).filter(Character.project_id == project_id).all()


def create_character(db: Session, character: CharacterCreate, user_id: int) -> Optional[Character]:
    """Create a new character"""
    project = get_project(db, character.project_id, user_id)
    if not project:
        return None

    db_character = Character(**character.model_dump())
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character


def update_character(
    db: Session, character_id: int, user_id: int, character_update: CharacterUpdate
) -> Optional[Character]:
    """Update a character"""
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        return None

    # Verify user owns the project
    project = get_project(db, db_character.project_id, user_id)
    if not project:
        return None

    update_data = character_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_character, field, value)

    db_character.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_character)
    return db_character


def delete_character(db: Session, character_id: int, user_id: int) -> bool:
    """Delete a character"""
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        return False

    project = get_project(db, db_character.project_id, user_id)
    if not project:
        return False

    db.delete(db_character)
    db.commit()
    return True


# ============================================
# Locations
# ============================================

def get_locations(db: Session, project_id: int, user_id: int) -> List[Location]:
    """Get all locations for a project"""
    project = get_project(db, project_id, user_id)
    if not project:
        return []

    return db.query(Location).filter(Location.project_id == project_id).all()


def create_location(db: Session, location: LocationCreate, user_id: int) -> Optional[Location]:
    """Create a new location"""
    project = get_project(db, location.project_id, user_id)
    if not project:
        return None

    db_location = Location(**location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


# ============================================
# Story Arcs
# ============================================

def get_story_arcs(db: Session, project_id: int, user_id: int) -> List[StoryArc]:
    """Get all story arcs for a project"""
    project = get_project(db, project_id, user_id)
    if not project:
        return []

    return db.query(StoryArc).filter(StoryArc.project_id == project_id).all()


def create_story_arc(db: Session, story_arc: StoryArcCreate, user_id: int) -> Optional[StoryArc]:
    """Create a new story arc"""
    project = get_project(db, story_arc.project_id, user_id)
    if not project:
        return None

    db_arc = StoryArc(**story_arc.model_dump())
    db.add(db_arc)
    db.commit()
    db.refresh(db_arc)
    return db_arc


# ============================================
# Brainstorm Sessions
# ============================================

def get_brainstorm_sessions(
    db: Session, user_id: int, project_id: Optional[int] = None, limit: int = 20
) -> List[BrainstormSession]:
    """Get brainstorm sessions for a user"""
    query = db.query(BrainstormSession).filter(BrainstormSession.user_id == user_id)

    if project_id:
        query = query.filter(BrainstormSession.project_id == project_id)

    return query.order_by(BrainstormSession.created_at.desc()).limit(limit).all()


def create_brainstorm_session(
    db: Session, session: BrainstormSessionCreate, user_id: int
) -> BrainstormSession:
    """Create a new brainstorm session"""
    db_session = BrainstormSession(
        user_id=user_id,
        **session.model_dump()
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

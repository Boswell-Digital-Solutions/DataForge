"""
AuthorForge Database Models

Extends DataForge with project management, genres, and writing-specific data.
These models share the same database as DataForge for seamless integration.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Table, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


# ============================================
# Enums
# ============================================

class GenreEnum(str, enum.Enum):
    """Fiction genres supported by AuthorForge"""
    FANTASY = "fantasy"
    SCIFI = "scifi"
    CHRISTIAN_FICTION = "christian_fiction"
    GENERAL = "general"


class ProjectStatus(str, enum.Enum):
    """Project lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


# ============================================
# Association Tables
# ============================================

project_genres = Table(
    'project_genres',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column(
        'genre',
        SQLEnum(GenreEnum, name='genreenum', values_callable=_enum_values),
        primary_key=True,
    )
)


# ============================================
# Models
# ============================================

class Project(Base):
    """
    Writing projects in AuthorForge.

    Each project represents a story/manuscript with associated genres,
    manuscripts, characters, and world-building elements.
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        SQLEnum(ProjectStatus, name='projectstatus', values_callable=_enum_values),
        default=ProjectStatus.ACTIVE,
        index=True,
    )

    # Word Count Tracking
    word_count = Column(Integer, default=0)
    target_word_count = Column(Integer)

    # Metadata
    settings = Column(JSON)  # Project-specific settings (AI preferences, export settings, etc.)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_edited_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="projects")
    # Note: genres are stored in the project_genres association table
    # Access via: project.genres (list of GenreEnum values)
    manuscripts = relationship("Manuscript", back_populates="project", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="project", cascade="all, delete-orphan")
    story_arcs = relationship("StoryArc", back_populates="project", cascade="all, delete-orphan")


class Manuscript(Base):
    """
    Manuscript chapters/scenes within a project.

    Represents the actual writing content organized by chapters.
    """
    __tablename__ = "manuscripts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Content
    title = Column(String(500), nullable=False)
    content = Column(Text)  # The actual writing
    chapter_number = Column(Integer)
    scene_number = Column(Integer)

    # Metadata
    word_count = Column(Integer, default=0)
    notes = Column(Text)  # Author notes for this chapter/scene
    status = Column(String(50), default="draft")  # draft, revision, final

    # Ordering
    order_index = Column(Integer, default=0)  # For custom ordering

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="manuscripts")


class Character(Base):
    """
    Characters in a project (for Anvil workspace).

    Stores character profiles, arcs, and development tracking.
    """
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    role = Column(String(100))  # protagonist, antagonist, supporting, etc.
    description = Column(Text)

    # Character Details (JSON for flexibility)
    profile = Column(JSON)  # age, appearance, background, etc.
    personality = Column(JSON)  # traits, values, fears, desires
    relationships = Column(JSON)  # relationships with other characters

    # Arc Tracking
    arc_data = Column(JSON)  # internal/external/spiritual arc beats

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="characters")


class Location(Base):
    """
    Locations/places in a project (for Lore workspace).

    World-building locations with descriptions and connections.
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    location_type = Column(String(100))  # city, region, building, etc.
    description = Column(Text)

    # World-building Details
    details = Column(JSON)  # geography, climate, culture, history, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="locations")


class StoryArc(Base):
    """
    Story arc tracking for plot beats (for Anvil workspace).

    Tracks plot structure, tension, and narrative flow.
    """
    __tablename__ = "story_arcs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Arc Info
    name = Column(String(255), nullable=False)
    arc_type = Column(String(50))  # main_plot, subplot, character_arc
    description = Column(Text)

    # Plot Beats (JSON array of beat objects)
    beats = Column(JSON)  # [{chapter, title, description, tension_level, ...}, ...]

    # Graph Data for visualization
    graph_data = Column(JSON)  # Tension curve, chapter markers, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="story_arcs")


class BrainstormSession(Base):
    """
    AI brainstorming sessions and generated ideas.

    Stores brainstorming history for future reference.
    """
    __tablename__ = "brainstorm_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True)

    # Session Info
    prompt = Column(Text, nullable=False)
    genre = Column(
        SQLEnum(GenreEnum, name='genreenum', values_callable=_enum_values),
        nullable=False,
    )

    # Generated Ideas (JSON array)
    ideas = Column(JSON, nullable=False)  # Array of story idea objects

    # Optional: Link to expanded ideas
    expanded_data = Column(JSON)  # Store expansions if user requests them

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="brainstorm_sessions")

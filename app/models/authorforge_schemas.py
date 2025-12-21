"""
AuthorForge Pydantic Schemas

API request/response models for AuthorForge endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# Enums (match SQLAlchemy enums)
# ============================================

class Genre(str, Enum):
    """Fiction genres"""
    FANTASY = "fantasy"
    SCIFI = "scifi"
    CHRISTIAN_FICTION = "christian_fiction"
    GENERAL = "general"


class ProjectStatusEnum(str, Enum):
    """Project status"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ============================================
# Project Schemas
# ============================================

class ProjectBase(BaseModel):
    """Base project fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: ProjectStatusEnum = ProjectStatusEnum.ACTIVE
    target_word_count: Optional[int] = Field(None, ge=0)
    settings: Optional[Dict[str, Any]] = None


class ProjectCreate(ProjectBase):
    """Create a new project"""
    genres: List[Genre] = Field(default_factory=list, min_length=1)


class ProjectUpdate(BaseModel):
    """Update project fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatusEnum] = None
    word_count: Optional[int] = Field(None, ge=0)
    target_word_count: Optional[int] = Field(None, ge=0)
    genres: Optional[List[Genre]] = None
    settings: Optional[Dict[str, Any]] = None


class Project(ProjectBase):
    """Project response"""
    id: int
    user_id: int
    genres: List[Genre]
    word_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_edited_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectSummary(BaseModel):
    """Lightweight project info for lists"""
    id: int
    name: str
    genres: List[Genre]
    status: ProjectStatusEnum
    word_count: int
    target_word_count: Optional[int]
    last_edited_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Manuscript Schemas
# ============================================

class ManuscriptBase(BaseModel):
    """Base manuscript fields"""
    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    chapter_number: Optional[int] = Field(None, ge=0)
    scene_number: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    status: str = "draft"
    order_index: int = 0


class ManuscriptCreate(ManuscriptBase):
    """Create a new manuscript"""
    project_id: int


class ManuscriptUpdate(BaseModel):
    """Update manuscript fields"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    chapter_number: Optional[int] = Field(None, ge=0)
    scene_number: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[str] = None
    order_index: Optional[int] = None


class Manuscript(ManuscriptBase):
    """Manuscript response"""
    id: int
    project_id: int
    word_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Character Schemas
# ============================================

class CharacterBase(BaseModel):
    """Base character fields"""
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = None
    description: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    personality: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None
    arc_data: Optional[Dict[str, Any]] = None


class CharacterCreate(CharacterBase):
    """Create a new character"""
    project_id: int


class CharacterUpdate(BaseModel):
    """Update character fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = None
    description: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    personality: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None
    arc_data: Optional[Dict[str, Any]] = None


class Character(CharacterBase):
    """Character response"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Location Schemas
# ============================================

class LocationBase(BaseModel):
    """Base location fields"""
    name: str = Field(..., min_length=1, max_length=255)
    location_type: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class LocationCreate(LocationBase):
    """Create a new location"""
    project_id: int


class LocationUpdate(BaseModel):
    """Update location fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_type: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class Location(LocationBase):
    """Location response"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Story Arc Schemas
# ============================================

class StoryArcBase(BaseModel):
    """Base story arc fields"""
    name: str = Field(..., min_length=1, max_length=255)
    arc_type: Optional[str] = None
    description: Optional[str] = None
    beats: Optional[List[Dict[str, Any]]] = None
    graph_data: Optional[Dict[str, Any]] = None


class StoryArcCreate(StoryArcBase):
    """Create a new story arc"""
    project_id: int


class StoryArcUpdate(BaseModel):
    """Update story arc fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    arc_type: Optional[str] = None
    description: Optional[str] = None
    beats: Optional[List[Dict[str, Any]]] = None
    graph_data: Optional[Dict[str, Any]] = None


class StoryArc(StoryArcBase):
    """Story arc response"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Brainstorm Session Schemas
# ============================================

class BrainstormSessionCreate(BaseModel):
    """Create a brainstorm session"""
    prompt: str = Field(..., min_length=1)
    genre: Genre
    project_id: Optional[int] = None
    ideas: List[Dict[str, Any]]


class BrainstormSession(BaseModel):
    """Brainstorm session response"""
    id: int
    user_id: int
    project_id: Optional[int]
    prompt: str
    genre: Genre
    ideas: List[Dict[str, Any]]
    expanded_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

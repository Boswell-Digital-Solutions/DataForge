# Models package

from .models import User, Domain, Tag, Document, Chunk, document_tags
from .authorforge_models import (
    GenreEnum, ProjectStatus,
    Project, Manuscript, Character, Location, StoryArc, BrainstormSession,
    project_genres
)
from .schemas import (
    UserBase, UserCreate, User as UserSchema,
    DomainBase, DomainCreate, Domain as DomainSchema,
    TagBase, TagCreate, Tag as TagSchema,
    DocumentBase, DocumentCreate, DocumentUpdate, Document as DocumentSchema,
    ChunkBase, Chunk as ChunkSchema,
    SearchRequest, SearchResult, SearchResponse,
    Token, TokenData,
    Stats
)
from .authorforge_schemas import (
    Genre, ProjectStatusEnum,
    ProjectBase, ProjectCreate, ProjectUpdate, Project as ProjectSchema, ProjectSummary,
    ManuscriptBase, ManuscriptCreate, ManuscriptUpdate, Manuscript as ManuscriptSchema,
    CharacterBase, CharacterCreate, CharacterUpdate, Character as CharacterSchema,
    LocationBase, LocationCreate, LocationUpdate, Location as LocationSchema,
    StoryArcBase, StoryArcCreate, StoryArcUpdate, StoryArc as StoryArcSchema,
    BrainstormSessionCreate, BrainstormSession as BrainstormSessionSchema
)

__all__ = [
    # DataForge Models
    "User", "Domain", "Tag", "Document", "Chunk", "document_tags",
    # AuthorForge Models
    "GenreEnum", "ProjectStatus",
    "Project", "Manuscript", "Character", "Location", "StoryArc", "BrainstormSession",
    "project_genres",
    # DataForge Schemas
    "UserBase", "UserCreate", "UserSchema",
    "DomainBase", "DomainCreate", "DomainSchema",
    "TagBase", "TagCreate", "TagSchema",
    "DocumentBase", "DocumentCreate", "DocumentUpdate", "DocumentSchema",
    "ChunkBase", "ChunkSchema",
    "SearchRequest", "SearchResult", "SearchResponse",
    "Token", "TokenData",
    "Stats",
    # AuthorForge Schemas
    "Genre", "ProjectStatusEnum",
    "ProjectBase", "ProjectCreate", "ProjectUpdate", "ProjectSchema", "ProjectSummary",
    "ManuscriptBase", "ManuscriptCreate", "ManuscriptUpdate", "ManuscriptSchema",
    "CharacterBase", "CharacterCreate", "CharacterUpdate", "CharacterSchema",
    "LocationBase", "LocationCreate", "LocationUpdate", "LocationSchema",
    "StoryArcBase", "StoryArcCreate", "StoryArcUpdate", "StoryArcSchema",
    "BrainstormSessionCreate", "BrainstormSessionSchema"
]

from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List
from datetime import datetime
from app.config import (
    MAX_DOCUMENT_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_QUERY_LENGTH
)

# ============================================
# User Schemas
# ============================================

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================
# Domain Schemas
# ============================================

class DomainBase(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

class DomainCreate(DomainBase):
    pass

class Domain(DomainBase):
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ============================================
# Tag Schemas
# ============================================

class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================
# Document Schemas
# ============================================

class DocumentBase(BaseModel):
    domain_id: str
    title: str = Field(..., max_length=MAX_TITLE_LENGTH)
    doc_type: str
    content: str = Field(..., max_length=MAX_DOCUMENT_LENGTH)
    doc_metadata: Optional[str] = None
    is_published: bool = True

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        if len(v) > MAX_DOCUMENT_LENGTH:
            raise ValueError(f'Content exceeds maximum length of {MAX_DOCUMENT_LENGTH} characters')
        return v

class DocumentCreate(DocumentBase):
    tags: Optional[List[str]] = []

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    doc_type: Optional[str] = None
    doc_metadata: Optional[str] = None
    is_published: Optional[bool] = None
    tags: Optional[List[str]] = None

class Document(DocumentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[Tag] = []

    model_config = ConfigDict(from_attributes=True)

# ============================================
# Chunk Schemas
# ============================================

class ChunkBase(BaseModel):
    content: str
    chunk_index: int

class Chunk(ChunkBase):
    id: int
    document_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================
# Search Schemas
# ============================================

class SearchRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_LENGTH)
    domain_id: Optional[str] = None
    tags: Optional[List[str]] = []
    limit: int = Field(default=5, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > MAX_QUERY_LENGTH:
            raise ValueError(f'Query exceeds maximum length of {MAX_QUERY_LENGTH} characters')
        return v.strip()

class SearchResult(BaseModel):
    id: int
    content: str
    similarity_score: float
    document_id: int
    document_title: str
    document_domain_id: str
    document_tags: List[str] = []

class SearchResponse(BaseModel):
    query: str
    total_results: int
    chunks: List[SearchResult]

# ============================================
# Authentication Schemas
# ============================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ============================================
# Stats Schemas
# ============================================

class Stats(BaseModel):
    total_documents: int
    total_chunks: int
    total_domains: int
    total_tags: int

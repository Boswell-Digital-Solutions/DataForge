"""
Pydantic schemas for private_source_profiles table.

Covers: CRUD operations for PrivateSourceProfile.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Enums (mirrored as string constraints in DB) ────────────────────

class PSPSourceType:
    WEB = "web"
    API = "api"
    RSS = "rss"


class PSPAuthType:
    COOKIE = "cookie"
    BEARER = "bearer"
    BASIC = "basic"
    HEADER = "header"


# ── Create ───────────────────────────────────────────────────────────

class PSPCreate(BaseModel):
    workspace_id: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: str | None = None
    source_type: str = Field("web", max_length=50)
    base_url: str = Field(..., max_length=2048)
    allowed_paths: list[str] = Field(default_factory=lambda: ["/"])
    auth_type: str = Field("cookie", max_length=50)
    config: dict[str, Any] = Field(default_factory=dict)
    quality_gates: dict[str, Any] | None = None
    is_active: bool = True


# ── Update (partial) ─────────────────────────────────────────────────

class PSPUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_type: str | None = None
    base_url: str | None = None
    allowed_paths: list[str] | None = None
    auth_type: str | None = None
    config: dict[str, Any] | None = None
    quality_gates: dict[str, Any] | None = None
    is_active: bool | None = None


# ── Response ─────────────────────────────────────────────────────────

class PSPResponse(BaseModel):
    id: int
    workspace_id: str
    name: str
    description: str | None
    source_type: str
    base_url: str
    allowed_paths: list[str]
    auth_type: str
    config: dict[str, Any]
    quality_gates: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# ── List Response ────────────────────────────────────────────────────

class PSPListResponse(BaseModel):
    items: list[PSPResponse]
    total: int

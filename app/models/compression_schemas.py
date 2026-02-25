"""Pydantic schemas for compression dictionary API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Request schemas ---

class DictionaryCreate(BaseModel):
    """Request body for registering a new compression dictionary."""
    name: str = Field(..., max_length=255)
    service_pair: str = Field(..., max_length=100, examples=["forgeagents-dataforge"])
    payload_class: str = Field(..., max_length=100, examples=["experience_search_response"])
    schema_version_min: str | None = None
    schema_version_max: str | None = None
    algorithm: str = "zstd"
    dictionary_blob_b64: str = Field(..., description="Base64-encoded dictionary binary")
    sha256_hash: str = Field(..., min_length=64, max_length=64)
    training_sample_n: int = Field(..., gt=0)
    training_params: dict[str, Any] | None = None
    compression_ratio: float | None = Field(None, ge=0.0, le=1.0)
    program: Literal["transport", "archive"]
    status: Literal["TRAINING", "CANDIDATE"] = "CANDIDATE"


class DictionaryStatusUpdate(BaseModel):
    """Request body for lifecycle status transition."""
    status: Literal["TRAINING", "CANDIDATE", "ACTIVE", "RETIRED"]


class DictionaryListParams(BaseModel):
    """Query parameters for listing dictionaries."""
    service_pair: str | None = None
    status: Literal["TRAINING", "CANDIDATE", "ACTIVE", "RETIRED"] | None = None
    program: Literal["transport", "archive"] | None = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


# --- Response schemas ---

class DictionaryResponse(BaseModel):
    """Dictionary metadata returned by the API (excludes binary blob)."""
    dictionary_id: UUID
    name: str
    version: int
    service_pair: str
    payload_class: str
    schema_version_min: str | None
    schema_version_max: str | None
    algorithm: str
    dictionary_size_bytes: int
    sha256_hash: str
    training_sample_n: int
    training_params: dict[str, Any] | None
    compression_ratio: float | None
    program: str
    status: str
    created_at: datetime
    retired_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DictionaryListResponse(BaseModel):
    """Paginated list of dictionaries."""
    items: list[DictionaryResponse]
    total: int
    limit: int
    offset: int


class ActiveDictionaryInfo(BaseModel):
    """Lightweight info for a service requesting active dictionaries."""
    dictionary_id: UUID
    service_pair: str
    payload_class: str
    sha256_hash: str
    dictionary_size_bytes: int
    version: int
    program: str

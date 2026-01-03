"""
Pydantic schemas for Tarcie ingest API.

Matches the TarcieEvent model from the Tarcie Rust codebase.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TarcieEventIn(BaseModel):
    """Single event from Tarcie."""

    id: UUID
    device_id: UUID

    timestamp_utc: datetime
    timestamp_mono_ms: int = Field(ge=0)

    event_type: Literal["Note", "Marker"]
    content: str = Field(default="", max_length=10240)  # 10KB max
    app_context: str = Field(default="General", max_length=64)
    source_version: str = Field(max_length=32)

    @field_validator("content", mode="before")
    @classmethod
    def truncate_content(cls, v: str) -> str:
        """Ensure content doesn't exceed max length."""
        if len(v) > 10240:
            return v[:10240]
        return v

    @field_validator("app_context", mode="before")
    @classmethod
    def truncate_context(cls, v: str) -> str:
        """Ensure context doesn't exceed max length."""
        if len(v) > 64:
            return v[:64]
        return v


class TarcieIngestRequest(BaseModel):
    """Batch ingest request from Tarcie flush."""

    source: Literal["tarcie"] = "tarcie"
    events: list[TarcieEventIn] = Field(default_factory=list, max_length=500)


class TarcieEventOut(BaseModel):
    """Response representation of a stored event."""

    id: UUID
    device_id: UUID
    timestamp_utc: datetime
    event_type: str
    content: str
    app_context: str
    ingested_at: datetime

    model_config = {"from_attributes": True}


class TarcieIngestResponse(BaseModel):
    """Response after successful ingest."""

    status: Literal["success", "partial", "error"] = "success"
    events_ingested: int = 0
    events_skipped: int = 0  # Duplicates
    errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

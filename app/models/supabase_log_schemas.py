"""
Supabase log events — Pydantic schemas for the read API.

Read-only surface consumed by ForgeAgents' Sentinel for anomaly sweeps. Rows are
already redacted at ingest (app/utils/supabase_log_ingest.py).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SupabaseLogEventResponse(BaseModel):
    id: str
    event_time: datetime
    log_type: str | None
    level: str | None
    status: str | None
    method: str | None
    pathname: str | None
    latency_ms: float | None
    category: str | None
    message: str | None
    event_metadata: dict[str, Any]
    source: str
    redacted: bool
    ingested_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupabaseLogEventListResponse(BaseModel):
    items: list[SupabaseLogEventResponse]
    total: int

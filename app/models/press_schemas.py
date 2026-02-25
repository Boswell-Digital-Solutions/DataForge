"""
PressForge — Pydantic schemas for API request/response.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────

class JournalistStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DO_NOT_CONTACT = "do_not_contact"

class ConsentStatus(str, Enum):
    UNKNOWN = "unknown"
    LEGITIMATE_INTEREST = "legitimate_interest"
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"

class CampaignStatus(str, Enum):
    DISCOVER = "DISCOVER"
    MATCH = "MATCH"
    GENERATE = "GENERATE"
    LABEL = "LABEL"
    REVIEW = "REVIEW"
    EXECUTE = "EXECUTE"
    MONITOR = "MONITOR"
    COMPLETE = "COMPLETE"

class PitchStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SENT = "sent"
    REJECTED = "rejected"

class OutreachEventType(str, Enum):
    SEND = "send"
    REPLY = "reply"
    BOUNCE = "bounce"
    OPEN = "open"

class DnsStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NONE = "none"
    UNKNOWN = "unknown"

class WarmupState(str, Enum):
    COLD = "cold"
    WARMING = "warming"
    WARM = "warm"


# ── Journalist schemas ───────────────────────────────────────

class JournalistCreate(BaseModel):
    name: str = Field(..., max_length=200)
    email: str | None = None
    beat: str | None = None
    publication: str | None = None
    bio: str | None = None
    social_links: dict[str, Any] = Field(default_factory=dict)
    status: JournalistStatus = JournalistStatus.ACTIVE
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    notes: str | None = None

class JournalistUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    beat: str | None = None
    publication: str | None = None
    bio: str | None = None
    social_links: dict[str, Any] | None = None
    status: JournalistStatus | None = None
    consent_status: ConsentStatus | None = None
    notes: str | None = None

class JournalistResponse(BaseModel):
    id: UUID
    name: str
    email: str | None
    beat: str | None
    publication: str | None
    bio: str | None
    social_links: dict[str, Any]
    status: str
    consent_status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JournalistListResponse(BaseModel):
    items: list[JournalistResponse]
    total: int


# ── Campaign schemas ─────────────────────────────────────────

class CampaignCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., max_length=300)
    news_angle: str | None = None

class CampaignUpdate(BaseModel):
    title: str | None = None
    news_angle: str | None = None
    status: CampaignStatus | None = None

class CampaignResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    news_angle: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


# ── Pitch schemas ────────────────────────────────────────────

class PitchCreate(BaseModel):
    campaign_id: UUID
    journalist_id: UUID
    subject: str | None = None
    body: str | None = None
    ai_generated: bool = False
    ai_rationale: str | None = None

class PitchUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    ai_rationale: str | None = None
    humanity_score: float | None = None
    human_verification_checksum: str | None = None
    status: PitchStatus | None = None

class PitchResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    journalist_id: UUID
    subject: str | None
    body: str | None
    ai_generated: bool
    ai_rationale: str | None
    humanity_score: float | None
    human_verification_checksum: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PitchListResponse(BaseModel):
    items: list[PitchResponse]
    total: int


# ── Outreach event schemas ───────────────────────────────────

class OutreachEventCreate(BaseModel):
    pitch_id: UUID
    event_type: OutreachEventType
    metadata: dict[str, Any] = Field(default_factory=dict)

class OutreachEventResponse(BaseModel):
    id: UUID
    pitch_id: UUID
    event_type: str
    metadata: dict[str, Any]
    occurred_at: datetime

    class Config:
        from_attributes = True


# ── Coverage schemas ─────────────────────────────────────────

class CoverageCreate(BaseModel):
    journalist_id: UUID | None = None
    campaign_id: UUID | None = None
    article_url: str
    title: str | None = None
    ai_sentiment_score: float | None = None

class CoverageResponse(BaseModel):
    id: UUID
    journalist_id: UUID | None
    campaign_id: UUID | None
    article_url: str
    title: str | None
    ai_sentiment_score: float | None
    discovered_at: datetime

    class Config:
        from_attributes = True


# ── Domain reputation schemas ────────────────────────────────

class DomainReputationResponse(BaseModel):
    id: UUID
    domain: str
    dmarc_status: str
    spf_status: str
    dkim_status: str
    warmup_state: str
    bounce_rate: float
    last_checked_at: datetime | None

    class Config:
        from_attributes = True


# ── AI audit log schemas ────────────────────────────────────

class AiAuditLogCreate(BaseModel):
    run_type: str
    model_version: str
    input_hash: str | None = None
    rationale: str | None = None
    personalization_notes: str | None = None
    campaign_id: UUID | None = None
    journalist_id: UUID | None = None

class AiAuditLogResponse(BaseModel):
    id: UUID
    run_type: str
    model_version: str
    input_hash: str | None
    rationale: str | None
    personalization_notes: str | None
    campaign_id: UUID | None
    journalist_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True

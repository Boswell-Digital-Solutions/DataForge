"""
PressForge — Pydantic schemas for API request/response.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


class JournalistListResponse(BaseModel):
    items: list[JournalistResponse]
    total: int


# ── Campaign schemas ─────────────────────────────────────────

class CampaignType(str, Enum):
    BOOK_LAUNCH = "book_launch"
    SERIES_CONTINUATION = "series_continuation"
    AUTHOR_PLATFORM = "author_platform"
    BACKLIST_REVIVAL = "backlist_revival"

class CampaignCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., max_length=300)
    news_angle: str | None = None
    campaign_type: CampaignType = CampaignType.BOOK_LAUNCH

class CampaignUpdate(BaseModel):
    title: str | None = None
    news_angle: str | None = None
    status: CampaignStatus | None = None
    campaign_type: CampaignType | None = None
    geo_share_pre: float | None = None
    geo_share_post: float | None = None

class CampaignResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    news_angle: str | None
    status: str
    campaign_type: str
    geo_share_pre: float | None = None
    geo_share_post: float | None = None
    cost_per_cycle: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


# ── Match result schemas ─────────────────────────────────────

class MatchStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class MatchResultCreate(BaseModel):
    campaign_id: UUID
    journalist_id: UUID
    match_score: float = Field(..., ge=0.0, le=1.0)
    beat_relevance: float | None = None
    recency_score: float | None = None
    audience_overlap: float | None = None
    evidence_bundle_id: UUID | None = None
    ai_rationale: str | None = None
    status: MatchStatus = MatchStatus.SUGGESTED

class MatchResultBulkCreate(BaseModel):
    matches: list[MatchResultCreate]

class MatchResultUpdate(BaseModel):
    status: MatchStatus | None = None
    ai_rationale: str | None = None

class MatchResultResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    journalist_id: UUID
    match_score: float
    beat_relevance: float | None
    recency_score: float | None
    audience_overlap: float | None
    evidence_bundle_id: UUID | None
    ai_rationale: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchResultListResponse(BaseModel):
    items: list[MatchResultResponse]
    total: int


# ── Pitch schemas ────────────────────────────────────────────

class PitchCreate(BaseModel):
    campaign_id: UUID
    journalist_id: UUID
    subject: str | None = None
    body: str | None = None
    ai_generated: bool = False
    ai_rationale: str | None = None
    evidence_bundle_id: UUID | None = None
    subject_variants: list[dict[str, Any]] | None = None

class PitchUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    ai_rationale: str | None = None
    humanity_score: float | None = None
    human_verification_checksum: str | None = None
    evidence_bundle_id: UUID | None = None
    subject_variants: list[dict[str, Any]] | None = None
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
    evidence_bundle_id: UUID | None = None
    subject_variants: list[dict[str, Any]] | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    metadata: dict[str, Any] = Field(validation_alias="event_metadata")
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)



class OutreachEventListResponse(BaseModel):
    items: list[OutreachEventResponse]
    total: int


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

    model_config = ConfigDict(from_attributes=True)



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

    model_config = ConfigDict(from_attributes=True)



# ── AI audit log schemas ────────────────────────────────────

class AiAuditLogCreate(BaseModel):
    run_type: str
    model_version: str
    input_hash: str | None = None
    rationale: str | None = None
    personalization_notes: str | None = None
    campaign_id: UUID | None = None
    journalist_id: UUID | None = None
    # EAE fields
    evidence_bundle_id: UUID | None = None
    bundle_hash: str | None = None
    model_route: str | None = None
    output_payload: dict[str, Any] | None = None
    cited_evidence_ids: list[str] | None = None
    uncited_evidence_ids: list[str] | None = None
    missing_evidence_warnings: list[str] | None = None

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
    # EAE fields
    evidence_bundle_id: UUID | None = None
    bundle_hash: str | None = None
    model_route: str | None = None
    output_payload: dict[str, Any] | None = None
    cited_evidence_ids: list[str] | None = None
    uncited_evidence_ids: list[str] | None = None
    missing_evidence_warnings: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)



# ── Evidence Item schemas (EAE) ────────────────────────────

class EvidenceKindEnum(str, Enum):
    JOURNALIST_ARTICLE = "journalist_article"
    JOURNALIST_PROFILE = "journalist_profile"
    BOOK_METADATA = "book_metadata"
    AUTHOR_BIO = "author_bio"
    PRESS_RELEASE = "press_release"
    INDUSTRY_SIGNAL = "industry_signal"
    PRIOR_COVERAGE = "prior_coverage"
    SOCIAL_SIGNAL = "social_signal"
    AUTHORITATIVE_REF = "authoritative_ref"

class AiStance(str, Enum):
    RECEPTIVE = "receptive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    HOSTILE = "hostile"
    UNKNOWN = "unknown"

class EvidenceItemCreate(BaseModel):
    kind: EvidenceKindEnum
    title: str = Field(..., max_length=500)
    source: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    content: str
    content_hash: str = Field(..., max_length=71)
    excerpt: str | None = None
    trust_tier: int = Field(default=1, ge=1, le=5)
    entity_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_chunk_id: int | None = None
    ingested_by: str | None = None
    stale_at: datetime | None = None
    ai_stance: AiStance | None = None
    disclosure_policy: str | None = None

class EvidenceItemUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    content: str | None = None
    content_hash: str | None = None
    excerpt: str | None = None
    trust_tier: int | None = Field(default=None, ge=1, le=5)
    entity_tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None
    stale_at: datetime | None = None
    ai_stance: AiStance | None = None
    disclosure_policy: str | None = None

class EvidenceItemResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    kind: str
    title: str
    source: str | None
    url: str | None
    published_at: datetime | None
    content_hash: str
    excerpt: str | None
    trust_tier: int
    entity_tags: list[str]
    metadata: dict[str, Any] = Field(validation_alias="extra_metadata")
    source_chunk_id: int | None
    ingested_by: str | None
    is_active: bool
    stale_at: datetime | None
    ai_stance: str | None = None
    disclosure_policy: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemListResponse(BaseModel):
    items: list[EvidenceItemResponse]
    total: int


# ── Evidence search schemas (EAE) ──────────────────────────

class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=200)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

class EvidenceSearchResult(BaseModel):
    id: UUID
    kind: str
    title: str
    content: str
    excerpt: str | None
    url: str | None
    source: str | None
    published_at: datetime | None
    trust_tier: int
    entity_tags: list[str]
    content_hash: str
    score: float
    retrieval_method: str = "hybrid"

class EvidenceSearchResponse(BaseModel):
    results: list[EvidenceSearchResult]
    total: int
    query: str


# ── Retrieval Run schemas (EAE) ────────────────────────────

class RetrievalRunCreate(BaseModel):
    task: str
    campaign_id: UUID | None = None
    query_spec: dict[str, Any]
    query_hash: str
    filters_applied: dict[str, Any]
    sub_query_count: int = 1
    candidate_count: int
    candidate_ids: list[str]
    topk_ids: list[str]
    topk_hashes: list[str]
    rerank_scores: dict[str, Any]
    bundle_id: str
    bundle_hash: str
    item_count: int
    total_tokens: int
    cache_hit: bool = False
    latency_ms: int
    coverage_score: float
    missing_kinds: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class RetrievalRunResponse(BaseModel):
    id: UUID
    created_at: datetime
    task: str
    campaign_id: UUID | None
    query_hash: str
    sub_query_count: int
    candidate_count: int
    item_count: int
    total_tokens: int
    cache_hit: bool
    latency_ms: int
    coverage_score: float
    missing_kinds: list[str]
    warnings: list[str]
    bundle_id: UUID
    bundle_hash: str

    model_config = ConfigDict(from_attributes=True)


class RetrievalRunListResponse(BaseModel):
    items: list[RetrievalRunResponse]
    total: int


# ══════════════════════════════════════════════════════════════
# v1.2: Automation, Governance, GEO, DraftSet, PromptPack
# ══════════════════════════════════════════════════════════════

# ── Automation enums ─────────────────────────────────────────

class AutomationRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    HIGH = "high"

class AgentActionType(str, Enum):
    ROUTE_PRIORITY = "route_priority"
    SUGGEST_CONFIG = "suggest_config"
    WIDEN_QUERY = "widen_query"
    ESCALATE_HUMAN = "escalate_human"
    AUTO_PAUSE = "auto_pause"
    REACTIVE_TRIGGER = "reactive_trigger"
    SELF_HEAL = "self_heal"

class CircuitBreakerStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class GeoSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class DraftSetStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"

class OutcomeType(str, Enum):
    COVERAGE_SECURED = "coverage_secured"
    FOLLOWUP_REQUESTED = "followup_requested"
    REPLY_RECEIVED = "reply_received"
    OPEN_CONFIRMED = "open_confirmed"
    BOUNCE = "bounce"
    ANTI_AI_FLAGGED = "anti_ai_flagged"


# ── Automation Job schemas ──────────────────────────────────

class AutomationJobCreate(BaseModel):
    job_key: str = Field(..., max_length=100)
    description: str | None = None
    cron_schedule: str = Field(..., max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    tier: int = Field(..., ge=1, le=4)
    cost_class: str = Field(default="low")

class AutomationJobUpdate(BaseModel):
    description: str | None = None
    cron_schedule: str | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None

class AutomationJobResponse(BaseModel):
    id: UUID
    job_key: str
    description: str | None
    cron_schedule: str
    config: dict[str, Any]
    enabled: bool
    tier: int
    cost_class: str
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationJobListResponse(BaseModel):
    items: list[AutomationJobResponse]
    total: int


# ── Automation Run schemas ──────────────────────────────────

class AutomationRunCreate(BaseModel):
    job_id: UUID
    job_key: str = Field(..., max_length=100)
    status: AutomationRunStatus = AutomationRunStatus.QUEUED
    attempt: int = 1
    inputs_hash: str | None = None

class AutomationRunUpdate(BaseModel):
    status: AutomationRunStatus | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None
    cost_tokens: int | None = None
    batch_id: str | None = None
    provider_used: str | None = None
    provider_latency_ms: int | None = None

class AutomationRunResponse(BaseModel):
    id: UUID
    job_id: UUID
    job_key: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    attempt: int
    summary: dict[str, Any] | None
    error: str | None
    cost_tokens: int | None
    batch_id: str | None
    provider_used: str | None
    provider_latency_ms: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationRunListResponse(BaseModel):
    items: list[AutomationRunResponse]
    total: int


# ── Automation Alert schemas ────────────────────────────────

class AutomationAlertCreate(BaseModel):
    run_id: UUID | None = None
    job_key: str = Field(..., max_length=100)
    severity: AlertSeverity
    title: str = Field(..., max_length=300)
    detail: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

class AutomationAlertResponse(BaseModel):
    id: UUID
    run_id: UUID | None
    job_key: str
    severity: str
    title: str
    detail: str | None
    context: dict[str, Any]
    dismissed: bool
    dismissed_by: str | None
    dismissed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationAlertListResponse(BaseModel):
    items: list[AutomationAlertResponse]
    total: int


# ── Automation Override schemas ─────────────────────────────

class AutomationOverrideCreate(BaseModel):
    job_key: str = Field(..., max_length=100)
    override_config: dict[str, Any]
    reason: str
    expires_at: datetime
    created_by: str = Field(..., max_length=100)

class AutomationOverrideResponse(BaseModel):
    id: UUID
    job_key: str
    override_config: dict[str, Any]
    reason: str
    expires_at: datetime
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationOverrideListResponse(BaseModel):
    items: list[AutomationOverrideResponse]
    total: int


# ── Agent Log schemas ───────────────────────────────────────

class AgentLogCreate(BaseModel):
    run_id: UUID | None = None
    job_key: str = Field(..., max_length=100)
    action_type: AgentActionType
    input_state: dict[str, Any] = Field(default_factory=dict)
    decision_rationale: str
    output_action: dict[str, Any] = Field(default_factory=dict)
    risk_flags: dict[str, Any] = Field(default_factory=dict)

class AgentLogResponse(BaseModel):
    id: UUID
    run_id: UUID | None
    job_key: str
    action_type: str
    input_state: dict[str, Any]
    decision_rationale: str
    output_action: dict[str, Any]
    risk_flags: dict[str, Any]
    accepted: bool | None
    accepted_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentLogUpdateDecision(BaseModel):
    accepted: bool
    accepted_by: str = Field(..., max_length=100)

class AgentLogListResponse(BaseModel):
    items: list[AgentLogResponse]
    total: int


# ── Provider Config schemas ─────────────────────────────────

class ProviderConfigCreate(BaseModel):
    provider_key: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    api_base_url: str | None = None
    supports_batch: bool = False
    batch_endpoint: str | None = None
    cost_per_1m_input: float | None = None
    cost_per_1m_output: float | None = None
    max_context_window: int | None = None
    supports_structured_output: bool = False
    rate_limit_rpm: int | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

class ProviderConfigUpdate(BaseModel):
    display_name: str | None = None
    api_base_url: str | None = None
    supports_batch: bool | None = None
    batch_endpoint: str | None = None
    cost_per_1m_input: float | None = None
    cost_per_1m_output: float | None = None
    max_context_window: int | None = None
    supports_structured_output: bool | None = None
    circuit_breaker_status: CircuitBreakerStatus | None = None
    rate_limit_rpm: int | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None

class ProviderConfigResponse(BaseModel):
    id: UUID
    provider_key: str
    display_name: str
    api_base_url: str | None
    supports_batch: bool
    batch_endpoint: str | None
    cost_per_1m_input: float | None
    cost_per_1m_output: float | None
    max_context_window: int | None
    supports_structured_output: bool
    circuit_breaker_status: str
    last_health_check_at: datetime | None
    rate_limit_rpm: int | None
    config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProviderConfigListResponse(BaseModel):
    items: list[ProviderConfigResponse]
    total: int


# ── GEO Probe schemas ──────────────────────────────────────

class GeoProbeCreate(BaseModel):
    campaign_id: UUID
    provider: str = Field(..., max_length=50)
    template_id: UUID | None = None
    prompt_text: str
    prompt_category: str | None = None
    response_excerpt: str | None = None
    brand_mentioned: bool = False
    citation_found: bool = False
    sentiment: GeoSentiment | None = None
    competitor_mentions: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int | None = None
    model_version: str | None = None

class GeoProbeResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    provider: str
    template_id: UUID | None
    prompt_text: str
    prompt_category: str | None
    response_excerpt: str | None
    brand_mentioned: bool
    citation_found: bool
    sentiment: str | None
    competitor_mentions: list[dict[str, Any]]
    latency_ms: int | None
    model_version: str | None
    probed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeoProbeListResponse(BaseModel):
    items: list[GeoProbeResponse]
    total: int


# ── GEO Probe Template schemas ─────────────────────────────

class GeoProbeTemplateCreate(BaseModel):
    campaign_id: UUID
    prompt_text: str
    intent_category: str | None = None
    funnel_stage: str | None = None
    auto_generated: bool = False

class GeoProbeTemplateUpdate(BaseModel):
    prompt_text: str | None = None
    intent_category: str | None = None
    funnel_stage: str | None = None

class GeoProbeTemplateResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    prompt_text: str
    intent_category: str | None
    funnel_stage: str | None
    auto_generated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeoProbeTemplateListResponse(BaseModel):
    items: list[GeoProbeTemplateResponse]
    total: int


# ── Social DraftSet schemas ─────────────────────────────────

class SocialDraftsetCreate(BaseModel):
    campaign_id: UUID
    bundle_hash: str | None = None
    intent: str | None = None
    platforms: list[str] = Field(default_factory=list)
    drafts: list[dict[str, Any]] = Field(default_factory=list)
    schema_json_ld: dict[str, Any] | None = None
    coverage_warnings: list[str] = Field(default_factory=list)

class SocialDraftsetUpdate(BaseModel):
    drafts: list[dict[str, Any]] | None = None
    schema_json_ld: dict[str, Any] | None = None
    status: DraftSetStatus | None = None

class SocialDraftsetResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    bundle_hash: str | None
    intent: str | None
    platforms: list[str]
    drafts: list[dict[str, Any]]
    schema_json_ld: dict[str, Any] | None
    coverage_warnings: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialDraftsetListResponse(BaseModel):
    items: list[SocialDraftsetResponse]
    total: int


# ── Prompt Pack schemas ─────────────────────────────────────

class PromptPackCreate(BaseModel):
    campaign_id: UUID
    pack_name: str | None = None
    sora_prompt: str | None = None
    chatgpt_image_prompt: str | None = None
    gemini_prompt: str | None = None
    negative_constraints: str | None = None
    aspect_ratios: dict[str, Any] = Field(default_factory=dict)
    alt_text: str | None = None

class PromptPackUpdate(BaseModel):
    pack_name: str | None = None
    sora_prompt: str | None = None
    chatgpt_image_prompt: str | None = None
    gemini_prompt: str | None = None
    negative_constraints: str | None = None
    aspect_ratios: dict[str, Any] | None = None
    alt_text: str | None = None
    status: DraftSetStatus | None = None

class PromptPackResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    pack_name: str | None
    sora_prompt: str | None
    chatgpt_image_prompt: str | None
    gemini_prompt: str | None
    negative_constraints: str | None
    aspect_ratios: dict[str, Any]
    alt_text: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptPackListResponse(BaseModel):
    items: list[PromptPackResponse]
    total: int


# ── Campaign Outcome schemas ────────────────────────────────

class CampaignOutcomeCreate(BaseModel):
    campaign_id: UUID
    bundle_hash: str | None = None
    outcome_type: OutcomeType
    outcome_weight: int
    journalist_id: UUID | None = None
    notes: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

class CampaignOutcomeResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    bundle_hash: str | None
    outcome_type: str
    outcome_weight: int
    journalist_id: UUID | None
    notes: str | None
    context: dict[str, Any]
    discovered_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignOutcomeListResponse(BaseModel):
    items: list[CampaignOutcomeResponse]
    total: int

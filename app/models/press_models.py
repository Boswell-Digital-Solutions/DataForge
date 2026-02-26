"""
PressForge — DataForge models.

Tables:
  - pf_journalists: Media contacts with coverage embeddings
  - pf_campaigns: Outreach campaigns linked to AuthorForge projects
  - pf_pitches: Per-journalist pitches with AI transparency metadata
  - pf_outreach_events: Send/reply/bounce event log
  - pf_coverage: Media mention tracking
  - pf_domain_reputation: Sender domain health (DMARC/SPF/DKIM)
  - pf_ai_audit_log: Immutable AI transparency audit trail
  - pf_evidence_items: EAE evidence registry with trust tiers, embeddings, entity tags
  - pf_retrieval_runs: EAE retrieval run audit trail (append-only)
  - pf_automation_jobs: Automation job definitions with cron schedules
  - pf_automation_runs: Automation execution log with cost tracking
  - pf_automation_alerts: Severity-based automation alerts
  - pf_automation_overrides: Runtime config overrides (7-day max TTL)
  - pf_agent_logs: Agentic governance audit trail (append-only)
  - pf_provider_configs: Multi-provider routing metadata
  - pf_geo_probes: GEO visibility probe results
  - pf_geo_probe_templates: Per-campaign GEO probe templates
  - pf_social_draftsets: Social media draft sets per campaign
  - pf_prompt_packs: AI image prompt packs per campaign
  - pf_campaign_outcomes: Outcome tracking with signal taxonomy
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class PfJournalist(Base):
    """Media contact with coverage embedding for semantic search."""
    __tablename__ = "pf_journalists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False)
    email = Column(Text, nullable=True, comment="Encrypted at app layer in later phases")
    beat = Column(String(100), nullable=True)
    publication = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    social_links = Column(JSONB, nullable=False, default=dict)
    coverage_embedding = Column(Vector(1536), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    consent_status = Column(String(20), nullable=False, default="unknown")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pitches = relationship("PfPitch", back_populates="journalist", cascade="all, delete-orphan")
    match_results = relationship("PfMatchResult", back_populates="journalist", cascade="all, delete-orphan")
    coverage = relationship("PfCoverage", back_populates="journalist")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'do_not_contact')", name="ck_pf_journalist_status"),
        CheckConstraint("consent_status IN ('unknown', 'legitimate_interest', 'opted_in', 'opted_out')", name="ck_pf_journalist_consent"),
    )


class PfCampaign(Base):
    """Outreach campaign linked to an AuthorForge project."""
    __tablename__ = "pf_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, comment="FK concept to AuthorForge project")
    title = Column(String(300), nullable=False)
    news_angle = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="DISCOVER")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # v1.2: Campaign type, GEO share tracking, cost tracking
    campaign_type = Column(String(30), nullable=False, default="book_launch")
    geo_share_pre = Column(Float, nullable=True, comment="Pre-campaign AI citation rate")
    geo_share_post = Column(Float, nullable=True, comment="Post-campaign AI citation rate")
    cost_per_cycle = Column(Float, nullable=True, comment="Computed from automation run token costs")

    # Relationships
    pitches = relationship("PfPitch", back_populates="campaign", cascade="all, delete-orphan")
    match_results = relationship("PfMatchResult", back_populates="campaign", cascade="all, delete-orphan")
    coverage = relationship("PfCoverage", back_populates="campaign")
    outcomes = relationship("PfCampaignOutcome", back_populates="campaign", cascade="all, delete-orphan")
    geo_probes = relationship("PfGeoProbe", back_populates="campaign", cascade="all, delete-orphan")
    geo_probe_templates = relationship("PfGeoProbeTemplate", back_populates="campaign", cascade="all, delete-orphan")
    social_draftsets = relationship("PfSocialDraftset", back_populates="campaign", cascade="all, delete-orphan")
    prompt_packs = relationship("PfPromptPack", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DISCOVER', 'MATCH', 'GENERATE', 'LABEL', 'REVIEW', 'EXECUTE', 'MONITOR', 'COMPLETE')",
            name="ck_pf_campaign_status",
        ),
        CheckConstraint(
            "campaign_type IN ('book_launch', 'series_continuation', 'author_platform', 'backlist_revival')",
            name="ck_pf_campaign_type",
        ),
    )


class PfMatchResult(Base):
    """AI journalist match result — ranked recommendation from MATCH stage."""
    __tablename__ = "pf_match_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Float, nullable=False, comment="0.0–1.0 composite match score")
    beat_relevance = Column(Float, nullable=True)
    recency_score = Column(Float, nullable=True)
    audience_overlap = Column(Float, nullable=True)
    evidence_bundle_id = Column(UUID(as_uuid=True), nullable=True, comment="EAE bundle used for match")
    ai_rationale = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="suggested")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="match_results")
    journalist = relationship("PfJournalist", back_populates="match_results")

    __table_args__ = (
        CheckConstraint("status IN ('suggested', 'accepted', 'rejected')", name="ck_pf_match_status"),
    )


class PfPitch(Base):
    """Per-journalist pitch with AI transparency metadata."""
    __tablename__ = "pf_pitches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    ai_generated = Column(Boolean, nullable=False, default=False)
    ai_rationale = Column(Text, nullable=True)
    humanity_score = Column(Float, nullable=True, comment="0.0=pure AI, 1.0=fully human-edited")
    human_verification_checksum = Column(String(128), nullable=True)
    evidence_bundle_id = Column(UUID(as_uuid=True), nullable=True, comment="EAE bundle used for generation")
    subject_variants = Column(JSONB, nullable=True, comment="AI-generated subject line variants")
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="pitches")
    journalist = relationship("PfJournalist", back_populates="pitches")
    outreach_events = relationship("PfOutreachEvent", back_populates="pitch", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'reviewed', 'approved', 'sent', 'rejected')", name="ck_pf_pitch_status"),
    )


class PfOutreachEvent(Base):
    """Send/reply/bounce/open event log."""
    __tablename__ = "pf_outreach_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pitch_id = Column(UUID(as_uuid=True), ForeignKey("pf_pitches.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)
    event_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    pitch = relationship("PfPitch", back_populates="outreach_events")

    __table_args__ = (
        CheckConstraint("event_type IN ('send', 'reply', 'bounce', 'open')", name="ck_pf_outreach_event_type"),
    )


class PfCoverage(Base):
    """Media mention / coverage tracking."""
    __tablename__ = "pf_coverage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    article_url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    ai_sentiment_score = Column(Float, nullable=True)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    journalist = relationship("PfJournalist", back_populates="coverage")
    campaign = relationship("PfCampaign", back_populates="coverage")


class PfDomainReputation(Base):
    """Sender domain health — DMARC/SPF/DKIM status and warm-up state."""
    __tablename__ = "pf_domain_reputation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain = Column(String(255), nullable=False, unique=True)
    dmarc_status = Column(String(10), nullable=False, default="unknown")
    spf_status = Column(String(10), nullable=False, default="unknown")
    dkim_status = Column(String(10), nullable=False, default="unknown")
    warmup_state = Column(String(10), nullable=False, default="cold")
    bounce_rate = Column(Float, nullable=False, default=0.0)
    last_checked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("dmarc_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_dmarc"),
        CheckConstraint("spf_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_spf"),
        CheckConstraint("dkim_status IN ('pass', 'fail', 'none', 'unknown')", name="ck_pf_domain_dkim"),
        CheckConstraint("warmup_state IN ('cold', 'warming', 'warm')", name="ck_pf_domain_warmup"),
    )


class PfAiAuditLog(Base):
    """Immutable append-only AI transparency audit trail."""
    __tablename__ = "pf_ai_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type = Column(String(50), nullable=False, comment="e.g. match, pitch_generation, subject_variants")
    model_version = Column(String(100), nullable=False)
    input_hash = Column(String(128), nullable=True)
    rationale = Column(Text, nullable=True)
    personalization_notes = Column(Text, nullable=True)
    campaign_id = Column(UUID(as_uuid=True), nullable=True)
    journalist_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # EAE evidence bundle columns (added by eae_001 migration)
    evidence_bundle_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    bundle_hash = Column(String(71), nullable=True, index=True)
    model_route = Column(String(100), nullable=True)
    output_payload = Column(JSONB, nullable=True)
    cited_evidence_ids = Column(JSONB, nullable=True)
    uncited_evidence_ids = Column(JSONB, nullable=True)
    missing_evidence_warnings = Column(JSONB, nullable=True)


class PfEvidenceItem(Base):
    """EAE evidence registry — PressForge-specific evidence items with trust tiers."""
    __tablename__ = "pf_evidence_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Classification
    kind = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    source = Column(String(500), nullable=True)
    url = Column(String(2000), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(71), nullable=False)
    excerpt = Column(Text, nullable=True)

    # Trust & classification
    trust_tier = Column(Integer, nullable=False, default=1)
    entity_tags = Column(JSONB, nullable=False, default=list)
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    # Search
    embedding = Column(Vector(1536), nullable=True)
    search_vector = Column(TSVECTOR)

    # Provenance
    source_chunk_id = Column(Integer, nullable=True)
    ingested_by = Column(String(50), nullable=True)

    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)
    stale_at = Column(DateTime, nullable=True)

    # v1.2: AI stance tracking for journalist kinds + disclosure policy
    ai_stance = Column(String(20), nullable=True, comment="For journalist kinds: receptive/neutral/cautious/hostile/unknown")
    disclosure_policy = Column(Text, nullable=True, comment="Outlet-level AI content policy text")

    __table_args__ = (
        CheckConstraint("trust_tier BETWEEN 1 AND 5", name="ck_pf_evidence_trust_tier"),
        CheckConstraint(
            "ai_stance IS NULL OR ai_stance IN ('receptive', 'neutral', 'cautious', 'hostile', 'unknown')",
            name="ck_pf_evidence_ai_stance",
        ),
    )


class PfRetrievalRun(Base):
    """EAE retrieval run audit trail — every pipeline execution writes one row."""
    __tablename__ = "pf_retrieval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # What was asked
    task = Column(String(50), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), nullable=True)
    query_spec = Column(JSONB, nullable=False)
    query_hash = Column(String(71), nullable=False)

    # What was searched
    filters_applied = Column(JSONB, nullable=False)
    sub_query_count = Column(Integer, nullable=False, default=1)

    # What was found
    candidate_count = Column(Integer, nullable=False)
    candidate_ids = Column(JSONB, nullable=False)
    topk_ids = Column(JSONB, nullable=False)
    topk_hashes = Column(JSONB, nullable=False)
    rerank_scores = Column(JSONB, nullable=False)

    # Bundle output
    bundle_id = Column(UUID(as_uuid=True), nullable=False)
    bundle_hash = Column(String(71), nullable=False)
    item_count = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    # Performance
    cache_hit = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=False)

    # Coverage quality
    coverage_score = Column(Float, nullable=False)
    missing_kinds = Column(JSONB, default=list)
    warnings = Column(JSONB, default=list)


# ══════════════════════════════════════════════════════════════
# v1.2: Automation, Governance, GEO, DraftSet, PromptPack
# ══════════════════════════════════════════════════════════════


class PfAutomationJob(Base):
    """Automation job definition with cron schedule and config."""
    __tablename__ = "pf_automation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_key = Column(String(100), nullable=False, unique=True, comment="e.g. journalist_refresh, geo_visibility_probe")
    description = Column(Text, nullable=True)
    cron_schedule = Column(String(100), nullable=False, comment="Cron expression, e.g. '0 3 * * *'")
    config = Column(JSONB, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    tier = Column(Integer, nullable=False)
    cost_class = Column(String(20), nullable=False, default="low")
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    runs = relationship("PfAutomationRun", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("tier BETWEEN 1 AND 4", name="ck_pf_auto_job_tier"),
        CheckConstraint("cost_class IN ('low', 'medium', 'high')", name="ck_pf_auto_job_cost_class"),
    )


class PfAutomationRun(Base):
    """Automation execution log — one row per job execution."""
    __tablename__ = "pf_automation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("pf_automation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    job_key = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    attempt = Column(Integer, nullable=False, default=1)
    inputs_hash = Column(String(128), nullable=True)
    summary = Column(JSONB, nullable=True, comment="Job-specific result summary")
    error = Column(Text, nullable=True)
    cost_tokens = Column(Integer, nullable=True, comment="Total tokens consumed for cost tracking")
    batch_id = Column(String(200), nullable=True, comment="Provider batch job ID when using batch mode")
    provider_used = Column(String(50), nullable=True, comment="Which provider handled this run")
    provider_latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    job = relationship("PfAutomationJob", back_populates="runs")
    alerts = relationship("PfAutomationAlert", back_populates="run")
    agent_logs = relationship("PfAgentLog", back_populates="run")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'skipped')",
            name="ck_pf_auto_run_status",
        ),
    )


class PfAutomationAlert(Base):
    """Automation alert — surfaced to operator in dashboard."""
    __tablename__ = "pf_automation_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pf_automation_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    job_key = Column(String(100), nullable=False, index=True)
    severity = Column(String(10), nullable=False)
    title = Column(String(300), nullable=False)
    detail = Column(Text, nullable=True)
    context = Column(JSONB, nullable=False, default=dict)
    dismissed = Column(Boolean, nullable=False, default=False)
    dismissed_by = Column(String(100), nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("PfAutomationRun", back_populates="alerts")

    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warn', 'high')", name="ck_pf_auto_alert_severity"),
    )


class PfAutomationOverride(Base):
    """Runtime config override — max 7-day TTL, reverts to YAML baseline after expiry."""
    __tablename__ = "pf_automation_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_key = Column(String(100), nullable=False, index=True)
    override_config = Column(JSONB, nullable=False, comment="Merged over YAML baseline config for this job")
    reason = Column(Text, nullable=False, comment="Why this override was created")
    expires_at = Column(DateTime, nullable=False, comment="Max 7 days from created_at")
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PfAgentLog(Base):
    """Agentic governance audit trail — append-only.

    Every rules-based decision in the automation runner writes one row.
    No UPDATE or DELETE allowed at API level.
    """
    __tablename__ = "pf_agent_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pf_automation_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    job_key = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, comment="e.g. route_priority, suggest_config, widen_query, escalate_human, auto_pause")
    input_state = Column(JSONB, nullable=False, default=dict)
    decision_rationale = Column(Text, nullable=False)
    output_action = Column(JSONB, nullable=False, default=dict)
    risk_flags = Column(JSONB, nullable=False, default=dict, comment="e.g. {high_risk: false, bias_detected: null, escalation_required: false}")
    accepted = Column(Boolean, nullable=True, comment="null until human responds")
    accepted_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("PfAutomationRun", back_populates="agent_logs")

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('route_priority', 'suggest_config', 'widen_query', 'escalate_human', 'auto_pause', 'reactive_trigger', 'self_heal')",
            name="ck_pf_agent_log_action_type",
        ),
    )


class PfProviderConfig(Base):
    """Multi-provider routing metadata — operational config only, no API keys."""
    __tablename__ = "pf_provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_key = Column(String(50), nullable=False, unique=True, comment="e.g. anthropic, openai, xai, google, ollama_local")
    display_name = Column(String(100), nullable=False)
    api_base_url = Column(String(500), nullable=True)
    supports_batch = Column(Boolean, nullable=False, default=False)
    batch_endpoint = Column(String(500), nullable=True)
    cost_per_1m_input = Column(Float, nullable=True)
    cost_per_1m_output = Column(Float, nullable=True)
    max_context_window = Column(Integer, nullable=True)
    supports_structured_output = Column(Boolean, nullable=False, default=False)
    circuit_breaker_status = Column(String(20), nullable=False, default="closed")
    last_health_check_at = Column(DateTime, nullable=True)
    rate_limit_rpm = Column(Integer, nullable=True)
    config = Column(JSONB, nullable=False, default=dict, comment="Provider-specific settings")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "circuit_breaker_status IN ('closed', 'open', 'half_open')",
            name="ck_pf_provider_circuit_breaker",
        ),
    )


class PfGeoProbe(Base):
    """GEO visibility probe result — one row per probe per provider."""
    __tablename__ = "pf_geo_probes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, comment="chatgpt, claude, gemini, perplexity")
    template_id = Column(UUID(as_uuid=True), ForeignKey("pf_geo_probe_templates.id", ondelete="SET NULL"), nullable=True)
    prompt_text = Column(Text, nullable=False)
    prompt_category = Column(String(100), nullable=True)
    response_excerpt = Column(Text, nullable=True)
    brand_mentioned = Column(Boolean, nullable=False, default=False)
    citation_found = Column(Boolean, nullable=False, default=False)
    sentiment = Column(String(20), nullable=True)
    competitor_mentions = Column(JSONB, nullable=False, default=list)
    latency_ms = Column(Integer, nullable=True)
    model_version = Column(String(100), nullable=True)
    probed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="geo_probes")
    template = relationship("PfGeoProbeTemplate")

    __table_args__ = (
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name="ck_pf_geo_probe_sentiment",
        ),
    )


class PfGeoProbeTemplate(Base):
    """Per-campaign GEO probe template — prompts sent to AI providers for visibility tracking."""
    __tablename__ = "pf_geo_probe_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    intent_category = Column(String(100), nullable=True, comment="e.g. discovery, comparison, recommendation")
    funnel_stage = Column(String(50), nullable=True, comment="e.g. awareness, consideration, decision")
    auto_generated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="geo_probe_templates")


class PfSocialDraftset(Base):
    """Social media draft set — per-platform content generated from evidence bundles."""
    __tablename__ = "pf_social_draftsets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_hash = Column(String(71), nullable=True, comment="EAE evidence bundle hash used for generation")
    intent = Column(String(50), nullable=True, comment="announce, insight, proof, bts")
    platforms = Column(JSONB, nullable=False, default=list, comment="Platform list, e.g. ['facebook', 'x', 'linkedin']")
    drafts = Column(JSONB, nullable=False, default=list, comment="Per-platform drafts: [{platform, content, char_count, hashtags, cta}]")
    schema_json_ld = Column(JSONB, nullable=True, comment="JSON-LD structured data for press release variants")
    coverage_warnings = Column(JSONB, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="social_draftsets")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'reviewed', 'approved')", name="ck_pf_draftset_status"),
    )


class PfPromptPack(Base):
    """AI image prompt pack — prompts for Sora, ChatGPT Image, Gemini per campaign."""
    __tablename__ = "pf_prompt_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    pack_name = Column(String(200), nullable=True)
    sora_prompt = Column(Text, nullable=True)
    chatgpt_image_prompt = Column(Text, nullable=True)
    gemini_prompt = Column(Text, nullable=True)
    negative_constraints = Column(Text, nullable=True)
    aspect_ratios = Column(JSONB, nullable=False, default=dict, comment="Per-platform aspect ratios + sizes")
    alt_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="prompt_packs")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'reviewed', 'approved')", name="ck_pf_promptpack_status"),
    )


class PfCampaignOutcome(Base):
    """Campaign outcome signal — weighted outcome for learning loops."""
    __tablename__ = "pf_campaign_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("pf_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_hash = Column(String(71), nullable=True, comment="EAE bundle associated with this outcome")
    outcome_type = Column(String(50), nullable=False)
    outcome_weight = Column(Integer, nullable=False)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("pf_journalists.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    context = Column(JSONB, nullable=False, default=dict)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    campaign = relationship("PfCampaign", back_populates="outcomes")

    __table_args__ = (
        CheckConstraint(
            "outcome_type IN ('coverage_secured', 'followup_requested', 'reply_received', 'open_confirmed', 'bounce', 'anti_ai_flagged')",
            name="ck_pf_outcome_type",
        ),
    )

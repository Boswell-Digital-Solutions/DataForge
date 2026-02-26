"""
PressForge — FastAPI router.

CRUD for journalists, campaigns, pitches, coverage, domain reputation, AI audit log.
EAE: evidence items CRUD, hybrid search, retrieval run logging.
Prefix: /api/v1/press
"""

import hashlib
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.press_models import (
    PfJournalist, PfCampaign, PfMatchResult, PfPitch, PfOutreachEvent,
    PfCoverage, PfDomainReputation, PfAiAuditLog,
    PfEvidenceItem, PfRetrievalRun,
    # v1.2
    PfAutomationJob, PfAutomationRun, PfAutomationAlert, PfAutomationOverride,
    PfAgentLog, PfProviderConfig, PfGeoProbe, PfGeoProbeTemplate,
    PfSocialDraftset, PfPromptPack, PfCampaignOutcome,
)
from app.models.press_schemas import (
    JournalistCreate, JournalistUpdate, JournalistResponse, JournalistListResponse,
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignListResponse,
    MatchResultCreate, MatchResultBulkCreate, MatchResultUpdate,
    MatchResultResponse, MatchResultListResponse,
    PitchCreate, PitchUpdate, PitchResponse, PitchListResponse,
    OutreachEventCreate, OutreachEventResponse, OutreachEventListResponse,
    CoverageCreate, CoverageResponse,
    DomainReputationResponse,
    AiAuditLogCreate, AiAuditLogResponse,
    EvidenceItemCreate, EvidenceItemUpdate, EvidenceItemResponse, EvidenceItemListResponse,
    EvidenceSearchRequest, EvidenceSearchResponse, EvidenceSearchResult,
    RetrievalRunCreate, RetrievalRunResponse, RetrievalRunListResponse,
    # v1.2
    AutomationJobCreate, AutomationJobUpdate, AutomationJobResponse, AutomationJobListResponse,
    AutomationRunCreate, AutomationRunUpdate, AutomationRunResponse, AutomationRunListResponse,
    AutomationAlertCreate, AutomationAlertResponse, AutomationAlertListResponse,
    AutomationOverrideCreate, AutomationOverrideResponse, AutomationOverrideListResponse,
    AgentLogCreate, AgentLogResponse, AgentLogUpdateDecision, AgentLogListResponse,
    ProviderConfigCreate, ProviderConfigUpdate, ProviderConfigResponse, ProviderConfigListResponse,
    GeoProbeCreate, GeoProbeResponse, GeoProbeListResponse,
    GeoProbeTemplateCreate, GeoProbeTemplateUpdate, GeoProbeTemplateResponse, GeoProbeTemplateListResponse,
    SocialDraftsetCreate, SocialDraftsetUpdate, SocialDraftsetResponse, SocialDraftsetListResponse,
    PromptPackCreate, PromptPackUpdate, PromptPackResponse, PromptPackListResponse,
    CampaignOutcomeCreate, CampaignOutcomeResponse, CampaignOutcomeListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/press", tags=["press"])


# ── Journalists ──────────────────────────────────────────────

@router.post("/journalists", response_model=JournalistResponse, status_code=201)
def create_journalist(body: JournalistCreate, db: Session = Depends(get_db)):
    journalist = PfJournalist(
        name=body.name,
        email=body.email,
        beat=body.beat,
        publication=body.publication,
        bio=body.bio,
        social_links=body.social_links,
        status=body.status.value,
        consent_status=body.consent_status.value,
        notes=body.notes,
    )
    db.add(journalist)
    db.commit()
    db.refresh(journalist)
    return journalist


@router.get("/journalists", response_model=JournalistListResponse)
def list_journalists(
    beat: str | None = None,
    publication: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfJournalist)
    if beat:
        q = q.filter(PfJournalist.beat.ilike(f"%{beat}%"))
    if publication:
        q = q.filter(PfJournalist.publication.ilike(f"%{publication}%"))
    if status:
        q = q.filter(PfJournalist.status == status)
    if search:
        q = q.filter(
            PfJournalist.name.ilike(f"%{search}%")
            | PfJournalist.beat.ilike(f"%{search}%")
            | PfJournalist.publication.ilike(f"%{search}%")
        )
    total = q.count()
    items = q.order_by(PfJournalist.name).offset(offset).limit(limit).all()
    return JournalistListResponse(items=items, total=total)


@router.get("/journalists/{journalist_id}", response_model=JournalistResponse)
def get_journalist(journalist_id: UUID, db: Session = Depends(get_db)):
    journalist = db.query(PfJournalist).filter(PfJournalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")
    return journalist


@router.patch("/journalists/{journalist_id}", response_model=JournalistResponse)
def update_journalist(journalist_id: UUID, body: JournalistUpdate, db: Session = Depends(get_db)):
    journalist = db.query(PfJournalist).filter(PfJournalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(journalist, key, value.value if hasattr(value, 'value') else value)
    journalist.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(journalist)
    return journalist


@router.delete("/journalists/{journalist_id}", status_code=204)
def delete_journalist(journalist_id: UUID, db: Session = Depends(get_db)):
    journalist = db.query(PfJournalist).filter(PfJournalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")
    db.delete(journalist)
    db.commit()


# ── Campaigns ────────────────────────────────────────────────

@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db)):
    campaign = PfCampaign(
        project_id=body.project_id,
        title=body.title,
        news_angle=body.news_angle,
        campaign_type=body.campaign_type.value,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns", response_model=CampaignListResponse)
def list_campaigns(
    project_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfCampaign)
    if project_id:
        q = q.filter(PfCampaign.project_id == project_id)
    if status:
        q = q.filter(PfCampaign.status == status)
    total = q.count()
    items = q.order_by(PfCampaign.created_at.desc()).offset(offset).limit(limit).all()
    return CampaignListResponse(items=items, total=total)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    campaign = db.query(PfCampaign).filter(PfCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: UUID, body: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = db.query(PfCampaign).filter(PfCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(campaign, key, value.value if hasattr(value, 'value') else value)
    campaign.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(campaign)
    return campaign


# ── Match Results ────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/matches", response_model=MatchResultListResponse)
def list_match_results(
    campaign_id: UUID,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if not db.query(PfCampaign).filter(PfCampaign.id == campaign_id).first():
        raise HTTPException(status_code=404, detail="Campaign not found")
    q = db.query(PfMatchResult).filter(PfMatchResult.campaign_id == campaign_id)
    if status:
        q = q.filter(PfMatchResult.status == status)
    total = q.count()
    items = q.order_by(PfMatchResult.match_score.desc()).offset(offset).limit(limit).all()
    return MatchResultListResponse(items=items, total=total)


@router.post("/campaigns/{campaign_id}/matches", response_model=list[MatchResultResponse], status_code=201)
def create_match_results(
    campaign_id: UUID,
    body: MatchResultBulkCreate,
    db: Session = Depends(get_db),
):
    if not db.query(PfCampaign).filter(PfCampaign.id == campaign_id).first():
        raise HTTPException(status_code=404, detail="Campaign not found")

    created = []
    for m in body.matches:
        if not db.query(PfJournalist).filter(PfJournalist.id == m.journalist_id).first():
            raise HTTPException(status_code=404, detail=f"Journalist {m.journalist_id} not found")
        result = PfMatchResult(
            campaign_id=campaign_id,
            journalist_id=m.journalist_id,
            match_score=m.match_score,
            beat_relevance=m.beat_relevance,
            recency_score=m.recency_score,
            audience_overlap=m.audience_overlap,
            evidence_bundle_id=m.evidence_bundle_id,
            ai_rationale=m.ai_rationale,
            status=m.status.value,
        )
        db.add(result)
        created.append(result)

    db.commit()
    for r in created:
        db.refresh(r)
    return created


@router.patch("/matches/{match_id}", response_model=MatchResultResponse)
def update_match_result(match_id: UUID, body: MatchResultUpdate, db: Session = Depends(get_db)):
    match = db.query(PfMatchResult).filter(PfMatchResult.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(match, key, value.value if hasattr(value, 'value') else value)
    match.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(match)
    return match


@router.delete("/matches/{match_id}", status_code=204)
def delete_match_result(match_id: UUID, db: Session = Depends(get_db)):
    match = db.query(PfMatchResult).filter(PfMatchResult.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")
    db.delete(match)
    db.commit()


# ── Pitches ──────────────────────────────────────────────────

@router.post("/pitches", response_model=PitchResponse, status_code=201)
def create_pitch(body: PitchCreate, db: Session = Depends(get_db)):
    # Verify campaign and journalist exist
    if not db.query(PfCampaign).filter(PfCampaign.id == body.campaign_id).first():
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not db.query(PfJournalist).filter(PfJournalist.id == body.journalist_id).first():
        raise HTTPException(status_code=404, detail="Journalist not found")

    pitch = PfPitch(
        campaign_id=body.campaign_id,
        journalist_id=body.journalist_id,
        subject=body.subject,
        body=body.body,
        ai_generated=body.ai_generated,
        ai_rationale=body.ai_rationale,
        evidence_bundle_id=body.evidence_bundle_id,
        subject_variants=body.subject_variants,
    )
    db.add(pitch)
    db.commit()
    db.refresh(pitch)
    return pitch


@router.get("/pitches", response_model=PitchListResponse)
def list_pitches(
    campaign_id: UUID | None = None,
    journalist_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfPitch)
    if campaign_id:
        q = q.filter(PfPitch.campaign_id == campaign_id)
    if journalist_id:
        q = q.filter(PfPitch.journalist_id == journalist_id)
    if status:
        q = q.filter(PfPitch.status == status)
    total = q.count()
    items = q.order_by(PfPitch.created_at.desc()).offset(offset).limit(limit).all()
    return PitchListResponse(items=items, total=total)


@router.get("/pitches/{pitch_id}", response_model=PitchResponse)
def get_pitch(pitch_id: UUID, db: Session = Depends(get_db)):
    pitch = db.query(PfPitch).filter(PfPitch.id == pitch_id).first()
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")
    return pitch


@router.patch("/pitches/{pitch_id}", response_model=PitchResponse)
def update_pitch(pitch_id: UUID, body: PitchUpdate, db: Session = Depends(get_db)):
    pitch = db.query(PfPitch).filter(PfPitch.id == pitch_id).first()
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(pitch, key, value.value if hasattr(value, 'value') else value)

    db.commit()
    db.refresh(pitch)
    return pitch


# ── Outreach Events ──────────────────────────────────────────

@router.post("/outreach-events", response_model=OutreachEventResponse, status_code=201)
def create_outreach_event(body: OutreachEventCreate, db: Session = Depends(get_db)):
    if not db.query(PfPitch).filter(PfPitch.id == body.pitch_id).first():
        raise HTTPException(status_code=404, detail="Pitch not found")

    event = PfOutreachEvent(
        pitch_id=body.pitch_id,
        event_type=body.event_type.value,
        event_metadata=body.metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/outreach-events", response_model=OutreachEventListResponse)
def list_outreach_events(
    pitch_id: UUID | None = None,
    event_type: str | None = None,
    campaign_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfOutreachEvent)
    if pitch_id:
        q = q.filter(PfOutreachEvent.pitch_id == pitch_id)
    if event_type:
        q = q.filter(PfOutreachEvent.event_type == event_type)
    if campaign_id:
        q = q.join(PfPitch, PfOutreachEvent.pitch_id == PfPitch.id).filter(
            PfPitch.campaign_id == campaign_id
        )
    total = q.count()
    items = q.order_by(PfOutreachEvent.occurred_at.desc()).offset(offset).limit(limit).all()
    return OutreachEventListResponse(items=items, total=total)


# ── Coverage ─────────────────────────────────────────────────

@router.post("/coverage", response_model=CoverageResponse, status_code=201)
def create_coverage(body: CoverageCreate, db: Session = Depends(get_db)):
    coverage = PfCoverage(
        journalist_id=body.journalist_id,
        campaign_id=body.campaign_id,
        article_url=body.article_url,
        title=body.title,
        ai_sentiment_score=body.ai_sentiment_score,
    )
    db.add(coverage)
    db.commit()
    db.refresh(coverage)
    return coverage


@router.get("/coverage", response_model=list[CoverageResponse])
def list_coverage(
    campaign_id: UUID | None = None,
    journalist_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfCoverage)
    if campaign_id:
        q = q.filter(PfCoverage.campaign_id == campaign_id)
    if journalist_id:
        q = q.filter(PfCoverage.journalist_id == journalist_id)
    return q.order_by(PfCoverage.discovered_at.desc()).offset(offset).limit(limit).all()


# ── Domain Reputation ────────────────────────────────────────

@router.get("/domain-reputation", response_model=list[DomainReputationResponse])
def list_domain_reputation(db: Session = Depends(get_db)):
    return db.query(PfDomainReputation).order_by(PfDomainReputation.domain).all()


@router.get("/domain-reputation/{domain}", response_model=DomainReputationResponse)
def get_domain_reputation(domain: str, db: Session = Depends(get_db)):
    rep = db.query(PfDomainReputation).filter(PfDomainReputation.domain == domain).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Domain not found")
    return rep


# ── AI Audit Log ─────────────────────────────────────────────

@router.post("/ai-audit-log", response_model=AiAuditLogResponse, status_code=201)
def create_ai_audit_entry(body: AiAuditLogCreate, db: Session = Depends(get_db)):
    entry = PfAiAuditLog(
        run_type=body.run_type,
        model_version=body.model_version,
        input_hash=body.input_hash,
        rationale=body.rationale,
        personalization_notes=body.personalization_notes,
        campaign_id=body.campaign_id,
        journalist_id=body.journalist_id,
        evidence_bundle_id=body.evidence_bundle_id,
        bundle_hash=body.bundle_hash,
        model_route=body.model_route,
        output_payload=body.output_payload,
        cited_evidence_ids=body.cited_evidence_ids,
        uncited_evidence_ids=body.uncited_evidence_ids,
        missing_evidence_warnings=body.missing_evidence_warnings,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/ai-audit-log", response_model=list[AiAuditLogResponse])
def list_ai_audit_log(
    campaign_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAiAuditLog)
    if campaign_id:
        q = q.filter(PfAiAuditLog.campaign_id == campaign_id)
    return q.order_by(PfAiAuditLog.created_at.desc()).offset(offset).limit(limit).all()


# ── Evidence Items (EAE) ───────────────────────────────────

@router.post("/evidence", response_model=EvidenceItemResponse, status_code=201)
def create_evidence_item(body: EvidenceItemCreate, db: Session = Depends(get_db)):
    item = PfEvidenceItem(
        kind=body.kind.value,
        title=body.title,
        source=body.source,
        url=body.url,
        published_at=body.published_at,
        content=body.content,
        content_hash=body.content_hash,
        excerpt=body.excerpt,
        trust_tier=body.trust_tier,
        entity_tags=body.entity_tags,
        extra_metadata=body.metadata,
        source_chunk_id=body.source_chunk_id,
        ingested_by=body.ingested_by,
        stale_at=body.stale_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/evidence", response_model=EvidenceItemListResponse)
def list_evidence_items(
    kind: str | None = None,
    trust_tier_min: int | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfEvidenceItem)
    if kind:
        q = q.filter(PfEvidenceItem.kind == kind)
    if trust_tier_min is not None:
        q = q.filter(PfEvidenceItem.trust_tier >= trust_tier_min)
    if is_active is not None:
        q = q.filter(PfEvidenceItem.is_active == is_active)
    total = q.count()
    items = q.order_by(PfEvidenceItem.created_at.desc()).offset(offset).limit(limit).all()
    return EvidenceItemListResponse(items=items, total=total)


@router.get("/evidence/{evidence_id}", response_model=EvidenceItemResponse)
def get_evidence_item(evidence_id: UUID, db: Session = Depends(get_db)):
    item = db.query(PfEvidenceItem).filter(PfEvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    return item


@router.patch("/evidence/{evidence_id}", response_model=EvidenceItemResponse)
def update_evidence_item(evidence_id: UUID, body: EvidenceItemUpdate, db: Session = Depends(get_db)):
    item = db.query(PfEvidenceItem).filter(PfEvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    # Map schema field names to ORM attribute names where they differ
    field_map = {"metadata": "extra_metadata"}
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            attr_name = field_map.get(key, key)
            setattr(item, attr_name, value.value if hasattr(value, 'value') else value)
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return item


@router.delete("/evidence/{evidence_id}", status_code=204)
def delete_evidence_item(evidence_id: UUID, db: Session = Depends(get_db)):
    item = db.query(PfEvidenceItem).filter(PfEvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    db.delete(item)
    db.commit()


# ── Evidence Search (EAE — Hybrid) ─────────────────────────

@router.post("/evidence/search", response_model=EvidenceSearchResponse)
def search_evidence(body: EvidenceSearchRequest, db: Session = Depends(get_db)):
    """Hybrid search against pf_evidence_items (keyword + metadata filters).

    Full semantic+RRF search requires embedding generation — for now this uses
    keyword search + metadata filters. Semantic search will be added when the
    embedding pipeline integration is wired up.
    """
    q = db.query(PfEvidenceItem).filter(PfEvidenceItem.is_active == True)

    filters = body.filters

    # Apply metadata filters
    if "kind__in" in filters:
        q = q.filter(PfEvidenceItem.kind.in_(filters["kind__in"]))
    if "trust_tier__gte" in filters:
        q = q.filter(PfEvidenceItem.trust_tier >= filters["trust_tier__gte"])
    if "published_at__gte" in filters:
        q = q.filter(PfEvidenceItem.published_at >= filters["published_at__gte"])
    if "published_at__lte" in filters:
        q = q.filter(PfEvidenceItem.published_at <= filters["published_at__lte"])
    if "entity_tags__overlap" in filters:
        # GIN index overlap: check if any of the filter tags are in entity_tags
        overlap_tags = filters["entity_tags__overlap"]
        if overlap_tags:
            from sqlalchemy.dialects.postgresql import array
            q = q.filter(PfEvidenceItem.entity_tags.op("?|")(overlap_tags))

    # Keyword search using tsvector if query is non-trivial
    if body.query.strip():
        ts_query = func.websearch_to_tsquery("english", body.query)
        rank = func.ts_rank_cd(PfEvidenceItem.search_vector, ts_query)
        q = q.filter(PfEvidenceItem.search_vector.op("@@")(ts_query))
        q = q.add_columns(rank.label("rank_score"))
        q = q.order_by(rank.desc())
    else:
        q = q.add_columns(func.literal(0.5).label("rank_score"))
        q = q.order_by(PfEvidenceItem.published_at.desc().nullslast())

    raw_results = q.limit(body.limit).all()

    results = []
    for row in raw_results:
        if hasattr(row, "PfEvidenceItem"):
            item = row.PfEvidenceItem
            score = float(row.rank_score)
        else:
            item = row[0]
            score = float(row[1])

        results.append(EvidenceSearchResult(
            id=item.id,
            kind=item.kind,
            title=item.title,
            content=item.content,
            excerpt=item.excerpt,
            url=item.url,
            source=item.source,
            published_at=item.published_at,
            trust_tier=item.trust_tier,
            entity_tags=item.entity_tags or [],
            content_hash=item.content_hash,
            score=min(score, 1.0),
            retrieval_method="hybrid",
        ))

    return EvidenceSearchResponse(
        results=results,
        total=len(results),
        query=body.query,
    )


# ── Retrieval Runs (EAE) ───────────────────────────────────

@router.post("/retrieval-runs", response_model=RetrievalRunResponse, status_code=201)
def create_retrieval_run(body: RetrievalRunCreate, db: Session = Depends(get_db)):
    run = PfRetrievalRun(
        task=body.task,
        campaign_id=body.campaign_id,
        query_spec=body.query_spec,
        query_hash=body.query_hash,
        filters_applied=body.filters_applied,
        sub_query_count=body.sub_query_count,
        candidate_count=body.candidate_count,
        candidate_ids=body.candidate_ids,
        topk_ids=body.topk_ids,
        topk_hashes=body.topk_hashes,
        rerank_scores=body.rerank_scores,
        bundle_id=body.bundle_id,
        bundle_hash=body.bundle_hash,
        item_count=body.item_count,
        total_tokens=body.total_tokens,
        cache_hit=body.cache_hit,
        latency_ms=body.latency_ms,
        coverage_score=body.coverage_score,
        missing_kinds=body.missing_kinds,
        warnings=body.warnings,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/retrieval-runs", response_model=RetrievalRunListResponse)
def list_retrieval_runs(
    task: str | None = None,
    campaign_id: UUID | None = None,
    cache_hit: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfRetrievalRun)
    if task:
        q = q.filter(PfRetrievalRun.task == task)
    if campaign_id:
        q = q.filter(PfRetrievalRun.campaign_id == campaign_id)
    if cache_hit is not None:
        q = q.filter(PfRetrievalRun.cache_hit == cache_hit)
    total = q.count()
    items = q.order_by(PfRetrievalRun.created_at.desc()).offset(offset).limit(limit).all()
    return RetrievalRunListResponse(items=items, total=total)


# ══════════════════════════════════════════════════════════════
# v1.2: Automation, Governance, GEO, DraftSet, PromptPack
# ══════════════════════════════════════════════════════════════


# ── Automation Jobs ──────────────────────────────────────────

@router.post("/automation/jobs", response_model=AutomationJobResponse, status_code=201)
def create_automation_job(body: AutomationJobCreate, db: Session = Depends(get_db)):
    job = PfAutomationJob(
        job_key=body.job_key,
        description=body.description,
        cron_schedule=body.cron_schedule,
        config=body.config,
        enabled=body.enabled,
        tier=body.tier,
        cost_class=body.cost_class,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/automation/jobs", response_model=AutomationJobListResponse)
def list_automation_jobs(
    enabled: bool | None = None,
    tier: int | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAutomationJob)
    if enabled is not None:
        q = q.filter(PfAutomationJob.enabled == enabled)
    if tier is not None:
        q = q.filter(PfAutomationJob.tier == tier)
    total = q.count()
    items = q.order_by(PfAutomationJob.tier, PfAutomationJob.job_key).offset(offset).limit(limit).all()
    return AutomationJobListResponse(items=items, total=total)


@router.get("/automation/jobs/{job_id}", response_model=AutomationJobResponse)
def get_automation_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(PfAutomationJob).filter(PfAutomationJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Automation job not found")
    return job


@router.patch("/automation/jobs/{job_id}", response_model=AutomationJobResponse)
def update_automation_job(job_id: UUID, body: AutomationJobUpdate, db: Session = Depends(get_db)):
    job = db.query(PfAutomationJob).filter(PfAutomationJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Automation job not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


# ── Automation Runs ──────────────────────────────────────────

@router.post("/automation/runs", response_model=AutomationRunResponse, status_code=201)
def create_automation_run(body: AutomationRunCreate, db: Session = Depends(get_db)):
    run = PfAutomationRun(
        job_id=body.job_id,
        job_key=body.job_key,
        status=body.status.value,
        attempt=body.attempt,
        inputs_hash=body.inputs_hash,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/automation/runs", response_model=AutomationRunListResponse)
def list_automation_runs(
    job_key: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAutomationRun)
    if job_key:
        q = q.filter(PfAutomationRun.job_key == job_key)
    if status:
        q = q.filter(PfAutomationRun.status == status)
    total = q.count()
    items = q.order_by(PfAutomationRun.created_at.desc()).offset(offset).limit(limit).all()
    return AutomationRunListResponse(items=items, total=total)


@router.get("/automation/runs/{run_id}", response_model=AutomationRunResponse)
def get_automation_run(run_id: UUID, db: Session = Depends(get_db)):
    run = db.query(PfAutomationRun).filter(PfAutomationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Automation run not found")
    return run


@router.patch("/automation/runs/{run_id}", response_model=AutomationRunResponse)
def update_automation_run(run_id: UUID, body: AutomationRunUpdate, db: Session = Depends(get_db)):
    run = db.query(PfAutomationRun).filter(PfAutomationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Automation run not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if isinstance(value, datetime):
            setattr(run, field, value)
        elif hasattr(value, 'value'):
            setattr(run, field, value.value)
        else:
            setattr(run, field, value)
    db.commit()
    db.refresh(run)
    # Update the job's last_run_at
    if run.status in ("success", "failed"):
        job = db.query(PfAutomationJob).filter(PfAutomationJob.id == run.job_id).first()
        if job:
            job.last_run_at = datetime.utcnow()
            db.commit()
    return run


# ── Automation Alerts ────────────────────────────────────────

@router.post("/automation/alerts", response_model=AutomationAlertResponse, status_code=201)
def create_automation_alert(body: AutomationAlertCreate, db: Session = Depends(get_db)):
    alert = PfAutomationAlert(
        run_id=body.run_id,
        job_key=body.job_key,
        severity=body.severity.value,
        title=body.title,
        detail=body.detail,
        context=body.context,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/automation/alerts", response_model=AutomationAlertListResponse)
def list_automation_alerts(
    job_key: str | None = None,
    severity: str | None = None,
    dismissed: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAutomationAlert)
    if job_key:
        q = q.filter(PfAutomationAlert.job_key == job_key)
    if severity:
        q = q.filter(PfAutomationAlert.severity == severity)
    if dismissed is not None:
        q = q.filter(PfAutomationAlert.dismissed == dismissed)
    total = q.count()
    items = q.order_by(PfAutomationAlert.created_at.desc()).offset(offset).limit(limit).all()
    return AutomationAlertListResponse(items=items, total=total)


@router.patch("/automation/alerts/{alert_id}/dismiss", response_model=AutomationAlertResponse)
def dismiss_automation_alert(alert_id: UUID, dismissed_by: str = Query(...), db: Session = Depends(get_db)):
    alert = db.query(PfAutomationAlert).filter(PfAutomationAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.dismissed = True
    alert.dismissed_by = dismissed_by
    alert.dismissed_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


# ── Automation Overrides ─────────────────────────────────────

@router.post("/automation/overrides", response_model=AutomationOverrideResponse, status_code=201)
def create_automation_override(body: AutomationOverrideCreate, db: Session = Depends(get_db)):
    from datetime import timedelta
    max_expires = datetime.utcnow() + timedelta(days=7)
    if body.expires_at > max_expires:
        raise HTTPException(400, "Override TTL cannot exceed 7 days")
    override = PfAutomationOverride(
        job_key=body.job_key,
        override_config=body.override_config,
        reason=body.reason,
        expires_at=body.expires_at,
        created_by=body.created_by,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


@router.get("/automation/overrides", response_model=AutomationOverrideListResponse)
def list_automation_overrides(
    job_key: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAutomationOverride)
    if job_key:
        q = q.filter(PfAutomationOverride.job_key == job_key)
    if active_only:
        q = q.filter(PfAutomationOverride.expires_at > datetime.utcnow())
    total = q.count()
    items = q.order_by(PfAutomationOverride.created_at.desc()).offset(offset).limit(limit).all()
    return AutomationOverrideListResponse(items=items, total=total)


@router.delete("/automation/overrides/{override_id}", status_code=204)
def delete_automation_override(override_id: UUID, db: Session = Depends(get_db)):
    override = db.query(PfAutomationOverride).filter(PfAutomationOverride.id == override_id).first()
    if not override:
        raise HTTPException(404, "Override not found")
    db.delete(override)
    db.commit()


# ── Agent Logs (append-only) ────────────────────────────────

@router.post("/agent-logs", response_model=AgentLogResponse, status_code=201)
def create_agent_log(body: AgentLogCreate, db: Session = Depends(get_db)):
    log = PfAgentLog(
        run_id=body.run_id,
        job_key=body.job_key,
        action_type=body.action_type.value,
        input_state=body.input_state,
        decision_rationale=body.decision_rationale,
        output_action=body.output_action,
        risk_flags=body.risk_flags,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/agent-logs", response_model=AgentLogListResponse)
def list_agent_logs(
    run_id: UUID | None = None,
    job_key: str | None = None,
    action_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfAgentLog)
    if run_id:
        q = q.filter(PfAgentLog.run_id == run_id)
    if job_key:
        q = q.filter(PfAgentLog.job_key == job_key)
    if action_type:
        q = q.filter(PfAgentLog.action_type == action_type)
    total = q.count()
    items = q.order_by(PfAgentLog.created_at.desc()).offset(offset).limit(limit).all()
    return AgentLogListResponse(items=items, total=total)


@router.patch("/agent-logs/{log_id}/decision", response_model=AgentLogResponse)
def update_agent_log_decision(log_id: UUID, body: AgentLogUpdateDecision, db: Session = Depends(get_db)):
    """Record human accept/veto decision on an agent proposal. This is the only mutable op on agent logs."""
    log = db.query(PfAgentLog).filter(PfAgentLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "Agent log not found")
    if log.accepted is not None:
        raise HTTPException(409, "Decision already recorded")
    log.accepted = body.accepted
    log.accepted_by = body.accepted_by
    db.commit()
    db.refresh(log)
    return log


# ── Provider Configs ─────────────────────────────────────────

@router.post("/provider-configs", response_model=ProviderConfigResponse, status_code=201)
def create_provider_config(body: ProviderConfigCreate, db: Session = Depends(get_db)):
    config = PfProviderConfig(
        provider_key=body.provider_key,
        display_name=body.display_name,
        api_base_url=body.api_base_url,
        supports_batch=body.supports_batch,
        batch_endpoint=body.batch_endpoint,
        cost_per_1m_input=body.cost_per_1m_input,
        cost_per_1m_output=body.cost_per_1m_output,
        max_context_window=body.max_context_window,
        supports_structured_output=body.supports_structured_output,
        rate_limit_rpm=body.rate_limit_rpm,
        config=body.config,
        enabled=body.enabled,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/provider-configs", response_model=ProviderConfigListResponse)
def list_provider_configs(
    enabled: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfProviderConfig)
    if enabled is not None:
        q = q.filter(PfProviderConfig.enabled == enabled)
    total = q.count()
    items = q.order_by(PfProviderConfig.provider_key).offset(offset).limit(limit).all()
    return ProviderConfigListResponse(items=items, total=total)


@router.get("/provider-configs/{config_id}", response_model=ProviderConfigResponse)
def get_provider_config(config_id: UUID, db: Session = Depends(get_db)):
    config = db.query(PfProviderConfig).filter(PfProviderConfig.id == config_id).first()
    if not config:
        raise HTTPException(404, "Provider config not found")
    return config


@router.patch("/provider-configs/{config_id}", response_model=ProviderConfigResponse)
def update_provider_config(config_id: UUID, body: ProviderConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(PfProviderConfig).filter(PfProviderConfig.id == config_id).first()
    if not config:
        raise HTTPException(404, "Provider config not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if hasattr(value, 'value'):
            setattr(config, field, value.value)
        else:
            setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return config


# ── GEO Probes ──────────────────────────────────────────────

@router.post("/geo/probes", response_model=GeoProbeResponse, status_code=201)
def create_geo_probe(body: GeoProbeCreate, db: Session = Depends(get_db)):
    probe = PfGeoProbe(
        campaign_id=body.campaign_id,
        provider=body.provider,
        template_id=body.template_id,
        prompt_text=body.prompt_text,
        prompt_category=body.prompt_category,
        response_excerpt=body.response_excerpt,
        brand_mentioned=body.brand_mentioned,
        citation_found=body.citation_found,
        sentiment=body.sentiment.value if body.sentiment else None,
        competitor_mentions=body.competitor_mentions,
        latency_ms=body.latency_ms,
        model_version=body.model_version,
    )
    db.add(probe)
    db.commit()
    db.refresh(probe)
    return probe


@router.get("/geo/probes", response_model=GeoProbeListResponse)
def list_geo_probes(
    campaign_id: UUID | None = None,
    provider: str | None = None,
    brand_mentioned: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfGeoProbe)
    if campaign_id:
        q = q.filter(PfGeoProbe.campaign_id == campaign_id)
    if provider:
        q = q.filter(PfGeoProbe.provider == provider)
    if brand_mentioned is not None:
        q = q.filter(PfGeoProbe.brand_mentioned == brand_mentioned)
    total = q.count()
    items = q.order_by(PfGeoProbe.probed_at.desc()).offset(offset).limit(limit).all()
    return GeoProbeListResponse(items=items, total=total)


# ── GEO Probe Templates ─────────────────────────────────────

@router.post("/geo/templates", response_model=GeoProbeTemplateResponse, status_code=201)
def create_geo_template(body: GeoProbeTemplateCreate, db: Session = Depends(get_db)):
    template = PfGeoProbeTemplate(
        campaign_id=body.campaign_id,
        prompt_text=body.prompt_text,
        intent_category=body.intent_category,
        funnel_stage=body.funnel_stage,
        auto_generated=body.auto_generated,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/geo/templates", response_model=GeoProbeTemplateListResponse)
def list_geo_templates(
    campaign_id: UUID | None = None,
    auto_generated: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfGeoProbeTemplate)
    if campaign_id:
        q = q.filter(PfGeoProbeTemplate.campaign_id == campaign_id)
    if auto_generated is not None:
        q = q.filter(PfGeoProbeTemplate.auto_generated == auto_generated)
    total = q.count()
    items = q.order_by(PfGeoProbeTemplate.created_at.desc()).offset(offset).limit(limit).all()
    return GeoProbeTemplateListResponse(items=items, total=total)


@router.get("/geo/templates/{template_id}", response_model=GeoProbeTemplateResponse)
def get_geo_template(template_id: UUID, db: Session = Depends(get_db)):
    template = db.query(PfGeoProbeTemplate).filter(PfGeoProbeTemplate.id == template_id).first()
    if not template:
        raise HTTPException(404, "GEO probe template not found")
    return template


@router.patch("/geo/templates/{template_id}", response_model=GeoProbeTemplateResponse)
def update_geo_template(template_id: UUID, body: GeoProbeTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(PfGeoProbeTemplate).filter(PfGeoProbeTemplate.id == template_id).first()
    if not template:
        raise HTTPException(404, "GEO probe template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/geo/templates/{template_id}", status_code=204)
def delete_geo_template(template_id: UUID, db: Session = Depends(get_db)):
    template = db.query(PfGeoProbeTemplate).filter(PfGeoProbeTemplate.id == template_id).first()
    if not template:
        raise HTTPException(404, "GEO probe template not found")
    db.delete(template)
    db.commit()


# ── Social DraftSets ─────────────────────────────────────────

@router.post("/social/draftsets", response_model=SocialDraftsetResponse, status_code=201)
def create_social_draftset(body: SocialDraftsetCreate, db: Session = Depends(get_db)):
    draftset = PfSocialDraftset(
        campaign_id=body.campaign_id,
        bundle_hash=body.bundle_hash,
        intent=body.intent,
        platforms=body.platforms,
        drafts=body.drafts,
        schema_json_ld=body.schema_json_ld,
        coverage_warnings=body.coverage_warnings,
    )
    db.add(draftset)
    db.commit()
    db.refresh(draftset)
    return draftset


@router.get("/social/draftsets", response_model=SocialDraftsetListResponse)
def list_social_draftsets(
    campaign_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfSocialDraftset)
    if campaign_id:
        q = q.filter(PfSocialDraftset.campaign_id == campaign_id)
    if status:
        q = q.filter(PfSocialDraftset.status == status)
    total = q.count()
    items = q.order_by(PfSocialDraftset.created_at.desc()).offset(offset).limit(limit).all()
    return SocialDraftsetListResponse(items=items, total=total)


@router.get("/social/draftsets/{draftset_id}", response_model=SocialDraftsetResponse)
def get_social_draftset(draftset_id: UUID, db: Session = Depends(get_db)):
    draftset = db.query(PfSocialDraftset).filter(PfSocialDraftset.id == draftset_id).first()
    if not draftset:
        raise HTTPException(404, "DraftSet not found")
    return draftset


@router.patch("/social/draftsets/{draftset_id}", response_model=SocialDraftsetResponse)
def update_social_draftset(draftset_id: UUID, body: SocialDraftsetUpdate, db: Session = Depends(get_db)):
    draftset = db.query(PfSocialDraftset).filter(PfSocialDraftset.id == draftset_id).first()
    if not draftset:
        raise HTTPException(404, "DraftSet not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if hasattr(value, 'value'):
            setattr(draftset, field, value.value)
        else:
            setattr(draftset, field, value)
    db.commit()
    db.refresh(draftset)
    return draftset


# ── Prompt Packs ─────────────────────────────────────────────

@router.post("/media/promptpacks", response_model=PromptPackResponse, status_code=201)
def create_prompt_pack(body: PromptPackCreate, db: Session = Depends(get_db)):
    pack = PfPromptPack(
        campaign_id=body.campaign_id,
        pack_name=body.pack_name,
        sora_prompt=body.sora_prompt,
        chatgpt_image_prompt=body.chatgpt_image_prompt,
        gemini_prompt=body.gemini_prompt,
        negative_constraints=body.negative_constraints,
        aspect_ratios=body.aspect_ratios,
        alt_text=body.alt_text,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


@router.get("/media/promptpacks", response_model=PromptPackListResponse)
def list_prompt_packs(
    campaign_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfPromptPack)
    if campaign_id:
        q = q.filter(PfPromptPack.campaign_id == campaign_id)
    if status:
        q = q.filter(PfPromptPack.status == status)
    total = q.count()
    items = q.order_by(PfPromptPack.created_at.desc()).offset(offset).limit(limit).all()
    return PromptPackListResponse(items=items, total=total)


@router.get("/media/promptpacks/{pack_id}", response_model=PromptPackResponse)
def get_prompt_pack(pack_id: UUID, db: Session = Depends(get_db)):
    pack = db.query(PfPromptPack).filter(PfPromptPack.id == pack_id).first()
    if not pack:
        raise HTTPException(404, "Prompt pack not found")
    return pack


@router.patch("/media/promptpacks/{pack_id}", response_model=PromptPackResponse)
def update_prompt_pack(pack_id: UUID, body: PromptPackUpdate, db: Session = Depends(get_db)):
    pack = db.query(PfPromptPack).filter(PfPromptPack.id == pack_id).first()
    if not pack:
        raise HTTPException(404, "Prompt pack not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if hasattr(value, 'value'):
            setattr(pack, field, value.value)
        else:
            setattr(pack, field, value)
    db.commit()
    db.refresh(pack)
    return pack


# ── Campaign Outcomes ────────────────────────────────────────

@router.post("/campaign-outcomes", response_model=CampaignOutcomeResponse, status_code=201)
def create_campaign_outcome(body: CampaignOutcomeCreate, db: Session = Depends(get_db)):
    outcome = PfCampaignOutcome(
        campaign_id=body.campaign_id,
        bundle_hash=body.bundle_hash,
        outcome_type=body.outcome_type.value,
        outcome_weight=body.outcome_weight,
        journalist_id=body.journalist_id,
        notes=body.notes,
        context=body.context,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


@router.get("/campaign-outcomes", response_model=CampaignOutcomeListResponse)
def list_campaign_outcomes(
    campaign_id: UUID | None = None,
    outcome_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PfCampaignOutcome)
    if campaign_id:
        q = q.filter(PfCampaignOutcome.campaign_id == campaign_id)
    if outcome_type:
        q = q.filter(PfCampaignOutcome.outcome_type == outcome_type)
    total = q.count()
    items = q.order_by(PfCampaignOutcome.created_at.desc()).offset(offset).limit(limit).all()
    return CampaignOutcomeListResponse(items=items, total=total)

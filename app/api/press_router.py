"""
PressForge — FastAPI router.

CRUD for journalists, campaigns, pitches, coverage, domain reputation, AI audit log.
Prefix: /api/v1/press
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.press_models import (
    PfJournalist, PfCampaign, PfPitch, PfOutreachEvent,
    PfCoverage, PfDomainReputation, PfAiAuditLog,
)
from app.models.press_schemas import (
    JournalistCreate, JournalistUpdate, JournalistResponse, JournalistListResponse,
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignListResponse,
    PitchCreate, PitchUpdate, PitchResponse, PitchListResponse,
    OutreachEventCreate, OutreachEventResponse,
    CoverageCreate, CoverageResponse,
    DomainReputationResponse,
    AiAuditLogCreate, AiAuditLogResponse,
)

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
        metadata=body.metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


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

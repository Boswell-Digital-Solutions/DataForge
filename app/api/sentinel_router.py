"""
Sentinel Agent — FastAPI router.

CRUD for sweeps and healing events.
Prefix: /api/v1/sentinel
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sentinel_models import SentinelSweep, SentinelHealingEvent
from app.models.sentinel_schemas import (
    SweepCreate, SweepUpdate, SweepResponse, SweepListResponse,
    HealingEventCreate, HealingEventUpdate, HealingEventResponse, HealingEventListResponse,
)

router = APIRouter(prefix="/api/v1/sentinel", tags=["sentinel"])


# ── Sweeps ───────────────────────────────────────────────────

@router.post("/sweeps", response_model=SweepResponse, status_code=201)
def create_sweep(body: SweepCreate, db: Session = Depends(get_db)):
    sweep = SentinelSweep(
        sweep_type=body.sweep_type.value,
        trigger=body.trigger.value,
    )
    db.add(sweep)
    db.commit()
    db.refresh(sweep)
    return sweep


@router.get("/sweeps", response_model=SweepListResponse)
def list_sweeps(
    status: str | None = None,
    sweep_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(SentinelSweep)
    if status:
        q = q.filter(SentinelSweep.status == status)
    if sweep_type:
        q = q.filter(SentinelSweep.sweep_type == sweep_type)
    total = q.count()
    items = q.order_by(SentinelSweep.started_at.desc()).offset(offset).limit(limit).all()
    return SweepListResponse(items=items, total=total)


@router.get("/sweeps/{sweep_id}", response_model=SweepResponse)
def get_sweep(sweep_id: UUID, db: Session = Depends(get_db)):
    sweep = db.query(SentinelSweep).filter(SentinelSweep.id == sweep_id).first()
    if not sweep:
        raise HTTPException(status_code=404, detail="Sweep not found")
    return sweep


@router.patch("/sweeps/{sweep_id}", response_model=SweepResponse)
def update_sweep(sweep_id: UUID, body: SweepUpdate, db: Session = Depends(get_db)):
    sweep = db.query(SentinelSweep).filter(SentinelSweep.id == sweep_id).first()
    if not sweep:
        raise HTTPException(status_code=404, detail="Sweep not found")

    update_data = body.model_dump(exclude_unset=True)

    # Convert DimensionResult objects to dicts for JSONB storage
    if "findings" in update_data and update_data["findings"] is not None:
        update_data["findings"] = [f.model_dump() if hasattr(f, 'model_dump') else f for f in update_data["findings"]]
        update_data["dimensions_checked"] = [f.get("dimension", f.dimension) if hasattr(f, 'dimension') else f.get("dimension", "") for f in update_data["findings"]]

    for key, value in update_data.items():
        if value is not None:
            setattr(sweep, key, value.value if hasattr(value, 'value') else value)

    db.commit()
    db.refresh(sweep)
    return sweep


@router.get("/sweeps/latest/status", response_model=SweepResponse | None)
def get_latest_sweep(db: Session = Depends(get_db)):
    sweep = db.query(SentinelSweep).order_by(SentinelSweep.started_at.desc()).first()
    return sweep


# ── Healing Events ───────────────────────────────────────────

@router.post("/healing", response_model=HealingEventResponse, status_code=201)
def create_healing_event(body: HealingEventCreate, db: Session = Depends(get_db)):
    # Verify sweep exists
    sweep = db.query(SentinelSweep).filter(SentinelSweep.id == body.sweep_id).first()
    if not sweep:
        raise HTTPException(status_code=404, detail="Sweep not found")

    event = SentinelHealingEvent(
        sweep_id=body.sweep_id,
        playbook=body.playbook,
        tier=body.tier.value,
        action=body.action,
        target_service=body.target_service,
        governed=body.governed,
        details=body.details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/healing", response_model=HealingEventListResponse)
def list_healing_events(
    sweep_id: UUID | None = None,
    outcome: str | None = None,
    tier: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(SentinelHealingEvent)
    if sweep_id:
        q = q.filter(SentinelHealingEvent.sweep_id == sweep_id)
    if outcome:
        q = q.filter(SentinelHealingEvent.outcome == outcome)
    if tier:
        q = q.filter(SentinelHealingEvent.tier == tier)
    total = q.count()
    items = q.order_by(SentinelHealingEvent.created_at.desc()).offset(offset).limit(limit).all()
    return HealingEventListResponse(items=items, total=total)


@router.patch("/healing/{event_id}", response_model=HealingEventResponse)
def update_healing_event(event_id: UUID, body: HealingEventUpdate, db: Session = Depends(get_db)):
    event = db.query(SentinelHealingEvent).filter(SentinelHealingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Healing event not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(event, key, value.value if hasattr(value, 'value') else value)

    db.commit()
    db.refresh(event)
    return event

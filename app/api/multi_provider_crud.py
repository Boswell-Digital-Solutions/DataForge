"""
CRUD operations for multi-provider pipeline tables.

Covers: model_catalog, pricing_monitor_runs, pricing_snapshots,
        pricing_alerts, cost_ledger, batch_queue.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func as sql_func, and_
from sqlalchemy.orm import Session

from app.models.multi_provider_models import (
    ModelCatalog, PricingMonitorRun, PricingSnapshot,
    PricingAlert, CostLedger, BatchQueue
)
from app.models.multi_provider_schemas import (
    ModelCatalogCreate, ModelCatalogUpdate,
    PricingMonitorRunCreate, PricingMonitorRunUpdate,
    PricingSnapshotCreate,
    PricingAlertCreate, PricingAlertUpdate,
    CostLedgerCreate, CostLedgerAggregation,
    BatchQueueCreate, BatchQueueUpdate,
)


# ── ModelCatalog CRUD ─────────────────────────────────────────────────

def create_model_entry(db: Session, data: ModelCatalogCreate) -> ModelCatalog:
    row = ModelCatalog(
        model_key=data.model_key,
        provider=data.provider.value,
        model_id=data.model_id,
        input_cost_per_mtok=data.input_cost_per_mtok,
        output_cost_per_mtok=data.output_cost_per_mtok,
        batch_input_cost=data.batch_input_cost,
        batch_output_cost=data.batch_output_cost,
        max_context=data.max_context,
        cache_read_discount=data.cache_read_discount,
        supports_batch=data.supports_batch,
        supports_structured_output=data.supports_structured_output,
        tier=data.tier.value,
        is_active=data.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_model_entry(db: Session, model_key: str) -> Optional[ModelCatalog]:
    return db.query(ModelCatalog).filter(ModelCatalog.model_key == model_key).first()


def list_model_entries(
    db: Session,
    *,
    provider: str | None = None,
    tier: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ModelCatalog], int]:
    query = db.query(ModelCatalog)
    if active_only:
        query = query.filter(ModelCatalog.is_active.is_(True))
    if provider:
        query = query.filter(ModelCatalog.provider == provider)
    if tier:
        query = query.filter(ModelCatalog.tier == tier)
    total = query.count()
    items = query.order_by(ModelCatalog.tier, ModelCatalog.input_cost_per_mtok).offset(offset).limit(limit).all()
    return items, total


def update_model_entry(db: Session, model_key: str, data: ModelCatalogUpdate) -> Optional[ModelCatalog]:
    row = db.query(ModelCatalog).filter(ModelCatalog.model_key == model_key).first()
    if not row:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "tier" in updates and updates["tier"] is not None:
        updates["tier"] = updates["tier"].value if hasattr(updates["tier"], "value") else updates["tier"]
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_model_entry(db: Session, model_key: str) -> bool:
    row = db.query(ModelCatalog).filter(ModelCatalog.model_key == model_key).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── PricingMonitorRun CRUD ────────────────────────────────────────────

def create_pricing_run(db: Session, data: PricingMonitorRunCreate) -> PricingMonitorRun:
    row = PricingMonitorRun(
        trigger_type=data.trigger_type.value,
        status="running",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pricing_run(db: Session, run_id: UUID) -> Optional[PricingMonitorRun]:
    return db.query(PricingMonitorRun).filter(PricingMonitorRun.id == run_id).first()


def list_pricing_runs(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PricingMonitorRun], int]:
    query = db.query(PricingMonitorRun)
    if status:
        query = query.filter(PricingMonitorRun.status == status)
    total = query.count()
    items = query.order_by(PricingMonitorRun.started_at.desc()).offset(offset).limit(limit).all()
    return items, total


def update_pricing_run(db: Session, run_id: UUID, data: PricingMonitorRunUpdate) -> Optional[PricingMonitorRun]:
    row = db.query(PricingMonitorRun).filter(PricingMonitorRun.id == run_id).first()
    if not row:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── PricingSnapshot CRUD ─────────────────────────────────────────────

def create_pricing_snapshot(db: Session, data: PricingSnapshotCreate) -> PricingSnapshot:
    row = PricingSnapshot(
        provider=data.provider.value,
        run_id=data.run_id,
        models=data.models,
        raw_content_hash=data.raw_content_hash,
        extraction_model=data.extraction_model,
        validation_errors=data.validation_errors,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_pricing_snapshots(
    db: Session,
    *,
    provider: str | None = None,
    run_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PricingSnapshot], int]:
    query = db.query(PricingSnapshot)
    if provider:
        query = query.filter(PricingSnapshot.provider == provider)
    if run_id:
        query = query.filter(PricingSnapshot.run_id == run_id)
    total = query.count()
    items = query.order_by(PricingSnapshot.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


# ── PricingAlert CRUD ─────────────────────────────────────────────────

def create_pricing_alert(db: Session, data: PricingAlertCreate) -> PricingAlert:
    row = PricingAlert(
        run_id=data.run_id,
        provider=data.provider.value,
        model_id=data.model_id,
        change_type=data.change_type.value,
        field_changed=data.field_changed,
        old_value=data.old_value,
        new_value=data.new_value,
        change_percent=data.change_percent,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_pricing_alerts(
    db: Session,
    *,
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PricingAlert], int]:
    query = db.query(PricingAlert)
    if status:
        query = query.filter(PricingAlert.status == status)
    if provider:
        query = query.filter(PricingAlert.provider == provider)
    total = query.count()
    items = query.order_by(PricingAlert.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def update_pricing_alert(db: Session, alert_id: UUID, data: PricingAlertUpdate) -> Optional[PricingAlert]:
    row = db.query(PricingAlert).filter(PricingAlert.id == alert_id).first()
    if not row:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    if "status" in updates and updates["status"] in ("applied", "dismissed", "investigating"):
        row.resolved_at = datetime.now(timezone.utc)
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── CostLedger CRUD ──────────────────────────────────────────────────

def create_cost_entry(db: Session, data: CostLedgerCreate) -> CostLedger:
    row = CostLedger(
        user_id=data.user_id,
        provider=data.provider.value,
        model_id=data.model_id,
        task_type=data.task_type[:64],
        input_tokens=data.input_tokens,
        output_tokens=data.output_tokens,
        input_cost_usd=data.input_cost_usd,
        output_cost_usd=data.output_cost_usd,
        total_cost_usd=data.total_cost_usd,
        is_batch=data.is_batch,
        is_cached=data.is_cached,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cost_entries(
    db: Session,
    *,
    provider: str | None = None,
    task_type: str | None = None,
    user_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CostLedger], int]:
    query = db.query(CostLedger)
    if provider:
        query = query.filter(CostLedger.provider == provider)
    if task_type:
        query = query.filter(CostLedger.task_type == task_type)
    if user_id:
        query = query.filter(CostLedger.user_id == user_id)
    if since:
        query = query.filter(CostLedger.created_at >= since)
    if until:
        query = query.filter(CostLedger.created_at <= until)
    total = query.count()
    items = query.order_by(CostLedger.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def get_cost_aggregation(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    user_id: str | None = None,
) -> CostLedgerAggregation:
    query = db.query(CostLedger)
    if since:
        query = query.filter(CostLedger.created_at >= since)
    if until:
        query = query.filter(CostLedger.created_at <= until)
    if user_id:
        query = query.filter(CostLedger.user_id == user_id)

    total_cost = query.with_entities(sql_func.coalesce(sql_func.sum(CostLedger.total_cost_usd), 0)).scalar()
    total_input = query.with_entities(sql_func.coalesce(sql_func.sum(CostLedger.input_tokens), 0)).scalar()
    total_output = query.with_entities(sql_func.coalesce(sql_func.sum(CostLedger.output_tokens), 0)).scalar()
    count = query.count()
    batch_count = query.filter(CostLedger.is_batch.is_(True)).count()
    cached_count = query.filter(CostLedger.is_cached.is_(True)).count()

    # By provider
    provider_rows = (
        db.query(CostLedger.provider, sql_func.sum(CostLedger.total_cost_usd))
        .group_by(CostLedger.provider)
    )
    if since:
        provider_rows = provider_rows.filter(CostLedger.created_at >= since)
    if until:
        provider_rows = provider_rows.filter(CostLedger.created_at <= until)
    if user_id:
        provider_rows = provider_rows.filter(CostLedger.user_id == user_id)
    by_provider = {row[0]: Decimal(str(row[1])) for row in provider_rows.all()}

    # By task type
    task_rows = (
        db.query(CostLedger.task_type, sql_func.sum(CostLedger.total_cost_usd))
        .group_by(CostLedger.task_type)
    )
    if since:
        task_rows = task_rows.filter(CostLedger.created_at >= since)
    if until:
        task_rows = task_rows.filter(CostLedger.created_at <= until)
    if user_id:
        task_rows = task_rows.filter(CostLedger.user_id == user_id)
    by_task = {row[0]: Decimal(str(row[1])) for row in task_rows.all()}

    return CostLedgerAggregation(
        total_cost_usd=Decimal(str(total_cost)),
        total_input_tokens=int(total_input),
        total_output_tokens=int(total_output),
        inference_count=count,
        batch_count=batch_count,
        cached_count=cached_count,
        by_provider=by_provider,
        by_task_type=by_task,
    )


# ── BatchQueue CRUD ──────────────────────────────────────────────────

def create_batch_item(db: Session, data: BatchQueueCreate) -> BatchQueue:
    row = BatchQueue(
        batch_group_id=data.batch_group_id,
        app_id=data.app_id[:50],
        task_type=data.task_type[:50],
        model_key=data.model_key[:50],
        provider=data.provider.value,
        messages_json=data.messages_json,
        max_tokens=data.max_tokens,
        temperature=data.temperature,
        structured_output_json=data.structured_output_json,
        callback_url=data.callback_url,
        callback_meta=data.callback_meta,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_batch_items(
    db: Session,
    *,
    status: str | None = None,
    batch_group_id: UUID | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[BatchQueue], int]:
    query = db.query(BatchQueue)
    if status:
        query = query.filter(BatchQueue.status == status)
    if batch_group_id:
        query = query.filter(BatchQueue.batch_group_id == batch_group_id)
    if provider:
        query = query.filter(BatchQueue.provider == provider)
    total = query.count()
    items = query.order_by(BatchQueue.queued_at.desc()).offset(offset).limit(limit).all()
    return items, total


def update_batch_item(db: Session, item_id: int, data: BatchQueueUpdate) -> Optional[BatchQueue]:
    row = db.query(BatchQueue).filter(BatchQueue.id == item_id).first()
    if not row:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def get_batch_group_status(db: Session, batch_group_id: UUID) -> dict:
    """Get aggregate status for a batch group."""
    query = db.query(BatchQueue).filter(BatchQueue.batch_group_id == batch_group_id)
    total = query.count()
    completed = query.filter(BatchQueue.status == "completed").count()
    failed = query.filter(BatchQueue.status == "failed").count()
    pending = query.filter(BatchQueue.status.in_(["queued", "submitted"])).count()
    total_cost = query.with_entities(sql_func.coalesce(sql_func.sum(BatchQueue.cost_usd), 0)).scalar()
    return {
        "batch_group_id": str(batch_group_id),
        "total": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "total_cost_usd": float(total_cost),
    }

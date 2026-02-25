"""
Multi-Provider Pipeline API — model catalog, pricing monitor, cost ledger, batch queue.

API Endpoints:
  Model Catalog:
    - GET  /api/v1/models            — List all models (filterable by provider, tier)
    - GET  /api/v1/models/{key}      — Get single model by key
    - POST /api/v1/models            — Create model entry
    - PUT  /api/v1/models/{key}      — Update model entry
    - DELETE /api/v1/models/{key}    — Delete model entry

  Pricing Monitor:
    - GET  /api/v1/pricing/runs      — List pricing monitor runs
    - POST /api/v1/pricing/runs      — Create a new run
    - PATCH /api/v1/pricing/runs/{id} — Update run status
    - POST /api/v1/pricing/snapshots — Record a pricing snapshot
    - GET  /api/v1/pricing/snapshots — List snapshots
    - GET  /api/v1/pricing/alerts    — List alerts
    - POST /api/v1/pricing/alerts    — Create an alert
    - PATCH /api/v1/pricing/alerts/{id} — Update alert status

  Cost Ledger:
    - POST /api/v1/costs/record      — Record a cost entry
    - GET  /api/v1/costs/entries      — List cost entries
    - GET  /api/v1/costs/aggregation  — Get aggregated cost stats

  Batch Queue:
    - POST /api/v1/batch/enqueue     — Enqueue a batch item
    - GET  /api/v1/batch/items       — List batch items
    - PATCH /api/v1/batch/items/{id} — Update batch item
    - GET  /api/v1/batch/groups/{id} — Get batch group status
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.api import multi_provider_crud as crud
from app.models.multi_provider_schemas import (
    ModelCatalogCreate, ModelCatalogUpdate, ModelCatalogResponse, ModelCatalogListResponse,
    PricingMonitorRunCreate, PricingMonitorRunUpdate, PricingMonitorRunResponse, PricingMonitorRunListResponse,
    PricingSnapshotCreate, PricingSnapshotResponse,
    PricingAlertCreate, PricingAlertUpdate, PricingAlertResponse, PricingAlertListResponse,
    CostLedgerCreate, CostLedgerResponse, CostLedgerListResponse, CostLedgerAggregation,
    BatchQueueCreate, BatchQueueUpdate, BatchQueueResponse, BatchQueueListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Multi-Provider"],
)


# ══════════════════════════════════════════════════════════════════════
# Model Catalog
# ══════════════════════════════════════════════════════════════════════

@router.get("/models", response_model=ModelCatalogListResponse, summary="List model catalog")
async def list_models(
    provider: str | None = Query(None),
    tier: str | None = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all models in the catalog, optionally filtered by provider and tier."""
    items, total = crud.list_model_entries(db, provider=provider, tier=tier, active_only=active_only, limit=limit, offset=offset)
    return ModelCatalogListResponse(items=[ModelCatalogResponse.model_validate(m) for m in items], total=total)


@router.get("/models/{model_key}", response_model=ModelCatalogResponse, summary="Get model by key")
async def get_model(model_key: str, db: Session = Depends(get_db)):
    """Get a single model catalog entry by its key."""
    row = crud.get_model_entry(db, model_key)
    if not row:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    return ModelCatalogResponse.model_validate(row)


@router.post("/models", status_code=201, response_model=ModelCatalogResponse, summary="Create model entry")
async def create_model(data: ModelCatalogCreate, db: Session = Depends(get_db)):
    """Add a new model to the catalog."""
    existing = crud.get_model_entry(db, data.model_key)
    if existing:
        raise HTTPException(status_code=409, detail=f"Model '{data.model_key}' already exists")
    row = crud.create_model_entry(db, data)
    logger.info("model_catalog_created", extra={"model_key": data.model_key, "provider": data.provider.value})
    return ModelCatalogResponse.model_validate(row)


@router.put("/models/{model_key}", response_model=ModelCatalogResponse, summary="Update model entry")
async def update_model(model_key: str, data: ModelCatalogUpdate, db: Session = Depends(get_db)):
    """Update an existing model catalog entry."""
    row = crud.update_model_entry(db, model_key, data)
    if not row:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    logger.info("model_catalog_updated", extra={"model_key": model_key})
    return ModelCatalogResponse.model_validate(row)


@router.delete("/models/{model_key}", status_code=204, summary="Delete model entry")
async def delete_model(model_key: str, db: Session = Depends(get_db)):
    """Remove a model from the catalog."""
    deleted = crud.delete_model_entry(db, model_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found")
    logger.info("model_catalog_deleted", extra={"model_key": model_key})


# ══════════════════════════════════════════════════════════════════════
# Pricing Monitor Runs
# ══════════════════════════════════════════════════════════════════════

@router.post("/pricing/runs", status_code=201, response_model=PricingMonitorRunResponse, summary="Start pricing run")
async def create_pricing_run(data: PricingMonitorRunCreate, db: Session = Depends(get_db)):
    """Create a new pricing monitor run record."""
    row = crud.create_pricing_run(db, data)
    logger.info("pricing_run_created", extra={"run_id": str(row.id), "trigger": data.trigger_type.value})
    return PricingMonitorRunResponse.model_validate(row)


@router.get("/pricing/runs", response_model=PricingMonitorRunListResponse, summary="List pricing runs")
async def list_pricing_runs(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List pricing monitor runs with optional status filter."""
    items, total = crud.list_pricing_runs(db, status=status, limit=limit, offset=offset)
    return PricingMonitorRunListResponse(items=[PricingMonitorRunResponse.model_validate(r) for r in items], total=total)


@router.patch("/pricing/runs/{run_id}", response_model=PricingMonitorRunResponse, summary="Update pricing run")
async def update_pricing_run(run_id: UUID, data: PricingMonitorRunUpdate, db: Session = Depends(get_db)):
    """Update a pricing monitor run (status, counts, completion)."""
    row = crud.update_pricing_run(db, run_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Pricing run not found")
    return PricingMonitorRunResponse.model_validate(row)


# ══════════════════════════════════════════════════════════════════════
# Pricing Snapshots
# ══════════════════════════════════════════════════════════════════════

@router.post("/pricing/snapshots", status_code=201, response_model=PricingSnapshotResponse, summary="Record snapshot")
async def create_snapshot(data: PricingSnapshotCreate, db: Session = Depends(get_db)):
    """Record a pricing snapshot from a provider scrape."""
    row = crud.create_pricing_snapshot(db, data)
    logger.info("pricing_snapshot_created", extra={"provider": data.provider.value, "run_id": str(data.run_id)})
    return PricingSnapshotResponse.model_validate(row)


@router.get("/pricing/snapshots", summary="List snapshots")
async def list_snapshots(
    provider: str | None = Query(None),
    run_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List pricing snapshots with optional provider/run filter."""
    items, total = crud.list_pricing_snapshots(db, provider=provider, run_id=run_id, limit=limit, offset=offset)
    return {"items": [PricingSnapshotResponse.model_validate(s) for s in items], "total": total}


# ══════════════════════════════════════════════════════════════════════
# Pricing Alerts
# ══════════════════════════════════════════════════════════════════════

@router.post("/pricing/alerts", status_code=201, response_model=PricingAlertResponse, summary="Create alert")
async def create_alert(data: PricingAlertCreate, db: Session = Depends(get_db)):
    """Create a pricing alert for a detected change."""
    row = crud.create_pricing_alert(db, data)
    logger.info("pricing_alert_created", extra={"provider": data.provider.value, "model_id": data.model_id, "change": data.change_type.value})
    return PricingAlertResponse.model_validate(row)


@router.get("/pricing/alerts", response_model=PricingAlertListResponse, summary="List alerts")
async def list_alerts(
    status: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List pricing alerts with optional status/provider filter."""
    items, total = crud.list_pricing_alerts(db, status=status, provider=provider, limit=limit, offset=offset)
    return PricingAlertListResponse(items=[PricingAlertResponse.model_validate(a) for a in items], total=total)


@router.patch("/pricing/alerts/{alert_id}", response_model=PricingAlertResponse, summary="Update alert")
async def update_alert(alert_id: UUID, data: PricingAlertUpdate, db: Session = Depends(get_db)):
    """Update alert status (apply, dismiss, investigate)."""
    row = crud.update_pricing_alert(db, alert_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return PricingAlertResponse.model_validate(row)


# ══════════════════════════════════════════════════════════════════════
# Cost Ledger
# ══════════════════════════════════════════════════════════════════════

@router.post("/costs/record", status_code=201, response_model=CostLedgerResponse, summary="Record cost entry")
async def record_cost(data: CostLedgerCreate, db: Session = Depends(get_db)):
    """Record a single inference cost entry to the ledger."""
    row = crud.create_cost_entry(db, data)
    return CostLedgerResponse.model_validate(row)


@router.get("/costs/entries", response_model=CostLedgerListResponse, summary="List cost entries")
async def list_costs(
    provider: str | None = Query(None),
    task_type: str | None = Query(None),
    user_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List cost ledger entries with optional filters."""
    items, total = crud.list_cost_entries(
        db, provider=provider, task_type=task_type, user_id=user_id,
        since=since, until=until, limit=limit, offset=offset,
    )
    return CostLedgerListResponse(items=[CostLedgerResponse.model_validate(c) for c in items], total=total)


@router.get("/costs/aggregation", response_model=CostLedgerAggregation, summary="Get cost aggregation")
async def get_cost_aggregation(
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    user_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregated cost statistics for a time period."""
    return crud.get_cost_aggregation(db, since=since, until=until, user_id=user_id)


# ══════════════════════════════════════════════════════════════════════
# Batch Queue
# ══════════════════════════════════════════════════════════════════════

@router.post("/batch/enqueue", status_code=201, response_model=BatchQueueResponse, summary="Enqueue batch item")
async def enqueue_batch(data: BatchQueueCreate, db: Session = Depends(get_db)):
    """Add a request to the batch queue."""
    row = crud.create_batch_item(db, data)
    logger.info("batch_enqueued", extra={"group": str(data.batch_group_id), "model": data.model_key})
    return BatchQueueResponse.model_validate(row)


@router.get("/batch/items", response_model=BatchQueueListResponse, summary="List batch items")
async def list_batch(
    status: str | None = Query(None),
    batch_group_id: UUID | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List batch queue items with optional filters."""
    items, total = crud.list_batch_items(db, status=status, batch_group_id=batch_group_id, provider=provider, limit=limit, offset=offset)
    return BatchQueueListResponse(items=[BatchQueueResponse.model_validate(b) for b in items], total=total)


@router.patch("/batch/items/{item_id}", response_model=BatchQueueResponse, summary="Update batch item")
async def update_batch(item_id: int, data: BatchQueueUpdate, db: Session = Depends(get_db)):
    """Update batch item status, results, or error."""
    row = crud.update_batch_item(db, item_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Batch item not found")
    return BatchQueueResponse.model_validate(row)


@router.get("/batch/groups/{group_id}", summary="Get batch group status")
async def get_batch_group(group_id: UUID, db: Session = Depends(get_db)):
    """Get aggregate status for a batch group."""
    return crud.get_batch_group_status(db, group_id)

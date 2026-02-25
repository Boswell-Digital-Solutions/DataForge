"""
Pydantic schemas for multi-provider pipeline tables.

Covers: model_catalog, pricing_snapshots, pricing_alerts,
        pricing_monitor_runs, cost_ledger, batch_queue.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────

class ModelTier(str, Enum):
    BUDGET = "budget"
    WORKHORSE = "workhorse"
    FLAGSHIP = "flagship"


class ProviderName(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"


class PricingAlertChangeType(str, Enum):
    PRICE_INCREASE = "price_increase"
    PRICE_DECREASE = "price_decrease"
    NEW_MODEL = "new_model"
    MODEL_DEPRECATED = "model_deprecated"
    CAPABILITY_CHANGE = "capability_change"


class PricingAlertStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"
    INVESTIGATING = "investigating"


class PricingRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PricingRunTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class BatchStatus(str, Enum):
    QUEUED = "queued"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"


# ── ModelCatalog ──────────────────────────────────────────────────────

class ModelCatalogCreate(BaseModel):
    model_key: str = Field(..., max_length=128)
    provider: ProviderName
    model_id: str = Field(..., max_length=128)
    input_cost_per_mtok: Decimal = Field(..., ge=0)
    output_cost_per_mtok: Decimal = Field(..., ge=0)
    batch_input_cost: Decimal | None = None
    batch_output_cost: Decimal | None = None
    max_context: int = Field(..., gt=0)
    cache_read_discount: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    supports_batch: bool = False
    supports_structured_output: bool = False
    tier: ModelTier
    is_active: bool = True


class ModelCatalogUpdate(BaseModel):
    input_cost_per_mtok: Decimal | None = None
    output_cost_per_mtok: Decimal | None = None
    batch_input_cost: Decimal | None = None
    batch_output_cost: Decimal | None = None
    max_context: int | None = None
    cache_read_discount: Decimal | None = None
    supports_batch: bool | None = None
    supports_structured_output: bool | None = None
    tier: ModelTier | None = None
    is_active: bool | None = None


class ModelCatalogResponse(BaseModel):
    model_key: str
    provider: str
    model_id: str
    input_cost_per_mtok: Decimal
    output_cost_per_mtok: Decimal
    batch_input_cost: Decimal | None
    batch_output_cost: Decimal | None
    max_context: int
    cache_read_discount: Decimal
    supports_batch: bool
    supports_structured_output: bool
    tier: str
    is_active: bool
    updated_at: datetime | None
    updated_by: str

    class Config:
        from_attributes = True


class ModelCatalogListResponse(BaseModel):
    items: list[ModelCatalogResponse]
    total: int


# ── PricingMonitorRun ─────────────────────────────────────────────────

class PricingMonitorRunCreate(BaseModel):
    trigger_type: PricingRunTrigger


class PricingMonitorRunUpdate(BaseModel):
    status: PricingRunStatus | None = None
    providers_scraped: int | None = None
    models_extracted: int | None = None
    changes_detected: int | None = None
    auto_applied: int | None = None
    alerts_created: int | None = None
    total_cost_usd: Decimal | None = None
    error: str | None = None
    completed_at: datetime | None = None


class PricingMonitorRunResponse(BaseModel):
    id: UUID
    trigger_type: str
    status: str
    providers_scraped: int
    models_extracted: int
    changes_detected: int
    auto_applied: int
    alerts_created: int
    total_cost_usd: Decimal | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class PricingMonitorRunListResponse(BaseModel):
    items: list[PricingMonitorRunResponse]
    total: int


# ── PricingSnapshot ───────────────────────────────────────────────────

class PricingSnapshotCreate(BaseModel):
    provider: ProviderName
    run_id: UUID
    models: list[dict[str, Any]]
    raw_content_hash: str | None = None
    extraction_model: str | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)


class PricingSnapshotResponse(BaseModel):
    id: UUID
    provider: str
    run_id: UUID
    models: list[dict[str, Any]]
    raw_content_hash: str | None
    extraction_model: str | None
    validation_errors: list[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ── PricingAlert ──────────────────────────────────────────────────────

class PricingAlertCreate(BaseModel):
    run_id: UUID
    provider: ProviderName
    model_id: str = Field(..., max_length=128)
    change_type: PricingAlertChangeType
    field_changed: str | None = None
    old_value: Decimal | None = None
    new_value: Decimal | None = None
    change_percent: Decimal | None = None


class PricingAlertUpdate(BaseModel):
    status: PricingAlertStatus | None = None
    resolved_by: str | None = None
    admin_notes: str | None = None


class PricingAlertResponse(BaseModel):
    id: UUID
    run_id: UUID
    provider: str
    model_id: str
    change_type: str
    field_changed: str | None
    old_value: Decimal | None
    new_value: Decimal | None
    change_percent: Decimal | None
    status: str
    resolved_by: str | None
    resolved_at: datetime | None
    admin_notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PricingAlertListResponse(BaseModel):
    items: list[PricingAlertResponse]
    total: int


# ── CostLedger ────────────────────────────────────────────────────────

class CostLedgerCreate(BaseModel):
    user_id: str | None = None
    provider: ProviderName
    model_id: str = Field(..., max_length=128)
    task_type: str = Field(..., max_length=64)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    input_cost_usd: Decimal = Field(..., ge=0)
    output_cost_usd: Decimal = Field(..., ge=0)
    total_cost_usd: Decimal = Field(..., ge=0)
    is_batch: bool = False
    is_cached: bool = False


class CostLedgerResponse(BaseModel):
    id: UUID
    user_id: str | None
    provider: str
    model_id: str
    task_type: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    total_cost_usd: Decimal
    is_batch: bool
    is_cached: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CostLedgerListResponse(BaseModel):
    items: list[CostLedgerResponse]
    total: int


class CostLedgerAggregation(BaseModel):
    """Aggregated cost stats for a time period."""
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    inference_count: int
    batch_count: int
    cached_count: int
    by_provider: dict[str, Decimal]
    by_task_type: dict[str, Decimal]


# ── BatchQueue ────────────────────────────────────────────────────────

class BatchQueueCreate(BaseModel):
    batch_group_id: UUID
    app_id: str = Field(..., max_length=50)
    task_type: str = Field(..., max_length=50)
    model_key: str = Field(..., max_length=50)
    provider: ProviderName
    messages_json: list[dict[str, Any]]
    max_tokens: int = Field(..., gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    structured_output_json: dict[str, Any] | None = None
    callback_url: str | None = None
    callback_meta: dict[str, Any] | None = None


class BatchQueueUpdate(BaseModel):
    status: BatchStatus | None = None
    provider_batch_id: str | None = None
    response_content: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    retry_count: int | None = None


class BatchQueueResponse(BaseModel):
    id: int
    batch_group_id: UUID
    app_id: str
    task_type: str
    model_key: str
    provider: str
    status: str
    provider_batch_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: Decimal | None
    queued_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    retry_count: int

    class Config:
        from_attributes = True


class BatchQueueListResponse(BaseModel):
    items: list[BatchQueueResponse]
    total: int

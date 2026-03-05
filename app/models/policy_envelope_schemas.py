"""Pydantic schemas for deterministic LLM policy and Slice 2 routing."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PolicyTimeoutsV1(BaseModel):
    per_call_seconds: int = Field(..., ge=1, le=3600)
    total_run_seconds: int = Field(..., ge=1, le=86400)


class PolicyHardFailThresholdsV1(BaseModel):
    invariant_violation: bool
    safety_score_min: float | None = Field(default=None, ge=0.0, le=1.0)
    unit_test_pass_required: bool


class PolicyEnvelopeV1(BaseModel):
    policy_version: str = Field(..., min_length=1, max_length=32)
    model_whitelist: list[str] = Field(..., min_length=1)
    max_calls_per_run: int = Field(..., ge=1, le=10000)
    max_tokens_per_run: int = Field(..., ge=1, le=50_000_000)
    max_cost_usd_per_run: Decimal = Field(..., ge=0)
    timeouts: PolicyTimeoutsV1
    hard_fail_thresholds: PolicyHardFailThresholdsV1


class PolicyEnvelopeRecordResponse(PolicyEnvelopeV1):
    policy_key: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LedgerEntryV1(BaseModel):
    schema_version: Literal["LedgerEntryV1"] = "LedgerEntryV1"
    ledger_id: str = Field(..., min_length=1, max_length=36)
    run_id: str = Field(..., min_length=1, max_length=64)
    sequence_no: int = Field(..., ge=1)
    policy_key: str = Field(..., min_length=1, max_length=128)
    policy_version: str = Field(..., min_length=1, max_length=32)
    model: str = Field(..., min_length=1, max_length=128)
    provider: str | None = Field(default=None, max_length=64)
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    cost_estimated_usd: Decimal = Field(..., ge=0)
    started_at: datetime
    completed_at: datetime
    termination_reason: str | None = Field(default=None, max_length=64)
    action_id: str | None = Field(default=None, max_length=256)
    action_mode: str | None = Field(default=None, max_length=32)
    router_context: dict | None = None
    preference_vector: dict | None = None
    bandit_policy_id: str | None = Field(default=None, max_length=32)
    bandit_state_hash: str | None = Field(default=None, max_length=128)
    policy_mode_used: str | None = Field(default=None, max_length=16)
    policy_id_used: str | None = Field(default=None, max_length=128)
    baseline_policy_id: str | None = Field(default=None, max_length=128)
    is_canary: bool = False
    rollout_reason_code: str | None = Field(default=None, max_length=128)
    trace_id: str | None = Field(default=None, max_length=256)
    shadow_policy_id: str | None = Field(default=None, max_length=128)
    shadow_action_id: str | None = Field(default=None, max_length=256)
    shadow_model: str | None = Field(default=None, max_length=128)
    router_degraded: bool = False
    high_cost_action: bool = False

    @field_validator("total_tokens")
    @classmethod
    def validate_total_tokens(cls, value: int, info):
        expected = info.data.get("prompt_tokens", 0) + info.data.get("completion_tokens", 0)
        if value != expected:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        return value


class LedgerAppendResponse(BaseModel):
    status: Literal["created"]
    entry: LedgerEntryV1


class RunScoreV1(BaseModel):
    schema_version: Literal["RunScoreV1"] = "RunScoreV1"
    quality_score: float = Field(..., ge=0.0, le=1.0)
    safety_score: float = Field(..., ge=0.0, le=1.0)
    invariant_pass: bool
    unit_tests_pass: bool


class RunFinalizationV1(BaseModel):
    schema_version: Literal["RunFinalizationV1"] = "RunFinalizationV1"
    run_id: str = Field(..., min_length=1, max_length=64)
    policy_key: str = Field(..., min_length=1, max_length=128)
    policy_version: str = Field(..., min_length=1, max_length=32)
    status: Literal["success", "terminated", "error"]
    termination_reason: str | None = Field(default=None, max_length=64)
    total_calls: int = Field(..., ge=0)
    total_prompt_tokens: int = Field(..., ge=0)
    total_completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_cost_usd: Decimal = Field(..., ge=0)
    started_at: datetime
    finalized_at: datetime
    run_score: RunScoreV1

    @field_validator("total_tokens")
    @classmethod
    def validate_total_tokens(cls, value: int, info):
        expected = info.data.get("total_prompt_tokens", 0) + info.data.get(
            "total_completion_tokens", 0
        )
        if value != expected:
            raise ValueError(
                "total_tokens must equal total_prompt_tokens + total_completion_tokens"
            )
        return value


class RunFinalizationResponse(BaseModel):
    status: Literal["finalized"]
    finalization: RunFinalizationV1


class PolicyRunStateResponse(BaseModel):
    run_id: str
    exists: bool
    finalized: bool
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: Decimal
    started_at: datetime | None = None
    last_call_completed_at: datetime | None = None
    finalization: RunFinalizationV1 | None = None


class PolicyRunStateEnvelope(BaseModel):
    state: PolicyRunStateResponse


class RouterTaskType(str, Enum):
    ASSIST = "assist"
    SKILL = "skill"
    AGENT = "agent"
    GENERAL = "general"


class InputSizeBucket(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionMode(str, Enum):
    STANDARD = "standard"
    FAST = "fast"
    REASONING = "reasoning"


class PreferenceNormalizationMethod(str, Enum):
    SUM_TO_ONE = "sum_to_one"


class RouterContextV1(BaseModel):
    schema_version: Literal["RouterContextV1"] = "RouterContextV1"
    task_type: RouterTaskType
    input_size_bucket: InputSizeBucket
    risk_class: RiskClass
    requires_reasoning: bool
    domain_tag: str | None = Field(default=None, max_length=128)


class ActionV1(BaseModel):
    schema_version: Literal["ActionV1"] = "ActionV1"
    action_id: str = Field(..., min_length=1, max_length=256)
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    mode: ActionMode = ActionMode.STANDARD
    constraints: list[str] = Field(default_factory=list)
    model_key: str | None = Field(default=None, max_length=128)
    catalog_provider: str | None = Field(default=None, max_length=64)
    tier: str | None = Field(default=None, max_length=32)
    unit_cost_usd_per_mtok: Decimal = Field(default=Decimal("0"), ge=0)


class PreferenceVectorV1(BaseModel):
    schema_version: Literal["PreferenceVectorV1"] = "PreferenceVectorV1"
    w_quality: float = Field(..., ge=0.0)
    w_cost: float = Field(..., ge=0.0)
    w_latency: float = Field(..., ge=0.0)
    w_safety: float = Field(..., ge=0.0)
    normalization_method: PreferenceNormalizationMethod = PreferenceNormalizationMethod.SUM_TO_ONE

    @model_validator(mode="after")
    def normalize(self) -> "PreferenceVectorV1":
        total = self.w_quality + self.w_cost + self.w_latency + self.w_safety
        if total <= 0:
            raise ValueError("preference vector weights must sum to a positive value")
        if self.normalization_method == PreferenceNormalizationMethod.SUM_TO_ONE:
            self.w_quality = self.w_quality / total
            self.w_cost = self.w_cost / total
            self.w_latency = self.w_latency / total
            self.w_safety = self.w_safety / total
        return self


class BanditActionStatsV1(BaseModel):
    schema_version: Literal["BanditActionStatsV1"] = "BanditActionStatsV1"
    action: ActionV1
    count: int = Field(..., ge=0)
    alpha: float = Field(..., gt=0.0)
    beta: float = Field(..., gt=0.0)
    mean_reward: float = Field(..., ge=0.0, le=1.0)
    cumulative_reward: float = Field(..., ge=0.0)
    last_reward: float | None = Field(default=None, ge=0.0, le=1.0)
    last_selected_at: datetime | None = None


class BanditStateV1(BaseModel):
    schema_version: Literal["BanditStateV1"] = "BanditStateV1"
    tenant_id: str = Field(..., min_length=1, max_length=128)
    policy_key: str = Field(..., min_length=1, max_length=128)
    policy_version: str = Field(..., min_length=1, max_length=32)
    partition_key: str = Field(..., min_length=1, max_length=256)
    router_context: RouterContextV1
    preference_vector: PreferenceVectorV1
    bandit_policy_id: Literal["ts_v1"]
    state_version: int = Field(..., ge=0)
    action_stats: list[BanditActionStatsV1] = Field(..., min_length=1)
    high_cost_action_fraction_limit: float = Field(..., ge=0.0, le=1.0)
    last_updated: datetime | None = None


class RewardRecordV1(BaseModel):
    schema_version: Literal["RewardRecordV1"] = "RewardRecordV1"
    run_id: str = Field(..., min_length=1, max_length=64)
    call_id: str = Field(..., min_length=1, max_length=64)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    policy_key: str = Field(..., min_length=1, max_length=128)
    policy_version: str = Field(..., min_length=1, max_length=32)
    partition_key: str = Field(..., min_length=1, max_length=256)
    action_id: str = Field(..., min_length=1, max_length=256)
    bandit_policy_id: Literal["ts_v1"]
    reward_version: Literal["RewardV1"] = "RewardV1"
    reward_value: float = Field(..., ge=0.0, le=1.0)
    observed_cost_usd: Decimal = Field(..., ge=0)
    latency_ms: int = Field(..., ge=0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    safety_score: float = Field(..., ge=0.0, le=1.0)
    invariant_pass: bool
    unit_tests_pass: bool
    router_context: RouterContextV1
    preference_vector: PreferenceVectorV1
    policy_mode_used: Literal["ACTIVE", "CANARY", "SHADOW", "OFF"]
    policy_id_used: str = Field(..., min_length=1, max_length=128)
    baseline_policy_id: str | None = Field(default=None, max_length=128)
    is_canary: bool
    rollout_reason_code: str | None = Field(default=None, max_length=128)
    router_degraded: bool = False
    created_at: datetime


class BanditStateEnvelope(BaseModel):
    state: BanditStateV1


class BanditStateUpsertResponse(BaseModel):
    status: Literal["created", "updated"]
    state: BanditStateV1


class RewardRecordResponse(BaseModel):
    status: Literal["created"]
    reward: RewardRecordV1


class BanditOutcomeV1(BaseModel):
    state: BanditStateV1
    reward: RewardRecordV1


class BanditOutcomeResponse(BaseModel):
    status: Literal["recorded"]
    state: BanditStateV1
    reward: RewardRecordV1

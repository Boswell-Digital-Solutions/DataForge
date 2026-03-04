"""Tests for deterministic policy envelope persistence endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.api.policy_envelope_router import (
    append_reward_record,
    append_policy_run_ledger_entry,
    finalize_policy_run,
    get_bandit_state,
    get_policy_envelope,
    get_policy_run_state,
    record_bandit_outcome,
    upsert_bandit_state,
    upsert_policy_envelope,
)
from app.models.policy_envelope_models import (
    LLMPolicyBanditStateModel,
    LLMPolicyRewardRecordModel,
)
from app.models.policy_envelope_schemas import LedgerEntryV1, PolicyEnvelopeV1, RunFinalizationV1
from app.models.policy_envelope_schemas import (
    ActionMode,
    ActionV1,
    BanditOutcomeV1,
    BanditStateV1,
    InputSizeBucket,
    PreferenceVectorV1,
    RewardRecordV1,
    RiskClass,
    RouterContextV1,
    RouterTaskType,
)


def make_policy() -> PolicyEnvelopeV1:
    return PolicyEnvelopeV1.model_validate(
        {
            "policy_version": "v1",
            "model_whitelist": ["allowed-model"],
            "max_calls_per_run": 3,
            "max_tokens_per_run": 1000,
            "max_cost_usd_per_run": Decimal("1.0"),
            "timeouts": {
                "per_call_seconds": 30,
                "total_run_seconds": 300,
            },
            "hard_fail_thresholds": {
                "invariant_violation": True,
                "safety_score_min": 0.5,
                "unit_test_pass_required": True,
            },
        }
    )


def make_ledger_entry(
    run_id: str,
    sequence_no: int,
    *,
    termination_reason: str | None = None,
) -> LedgerEntryV1:
    prompt_tokens = 10 * sequence_no
    completion_tokens = 5 * sequence_no
    return LedgerEntryV1.model_validate(
        {
            "schema_version": "LedgerEntryV1",
            "ledger_id": f"00000000-0000-0000-0000-{sequence_no:012d}",
            "run_id": run_id,
            "sequence_no": sequence_no,
            "policy_key": "forgeagents.test.v1",
            "policy_version": "v1",
            "model": "allowed-model",
            "provider": "neuroforge",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_estimated_usd": Decimal("0.001") * sequence_no,
            "started_at": f"2026-03-03T12:00:0{sequence_no}Z",
            "completed_at": f"2026-03-03T12:00:1{sequence_no}Z",
            "termination_reason": termination_reason,
        }
    )


def make_finalization(run_id: str, *, termination_reason: str | None = None) -> RunFinalizationV1:
    return RunFinalizationV1.model_validate(
        {
            "schema_version": "RunFinalizationV1",
            "run_id": run_id,
            "policy_key": "forgeagents.test.v1",
            "policy_version": "v1",
            "status": "terminated" if termination_reason else "success",
            "termination_reason": termination_reason,
            "total_calls": 2,
            "total_prompt_tokens": 30,
            "total_completion_tokens": 15,
            "total_tokens": 45,
            "total_cost_usd": "0.003",
            "started_at": "2026-03-03T12:00:01Z",
            "finalized_at": "2026-03-03T12:01:00Z",
            "run_score": {
                "schema_version": "RunScoreV1",
                "quality_score": 0.0,
                "safety_score": 1.0,
                "invariant_pass": True,
                "unit_tests_pass": True,
            },
        }
    )


def make_router_context() -> RouterContextV1:
    return RouterContextV1.model_validate(
        {
            "schema_version": "RouterContextV1",
            "task_type": RouterTaskType.ASSIST,
            "input_size_bucket": InputSizeBucket.SMALL,
            "risk_class": RiskClass.LOW,
            "requires_reasoning": False,
            "domain_tag": "governance",
        }
    )


def make_preference_vector(*, quality: float, cost: float, latency: float, safety: float) -> PreferenceVectorV1:
    return PreferenceVectorV1.model_validate(
        {
            "schema_version": "PreferenceVectorV1",
            "w_quality": quality,
            "w_cost": cost,
            "w_latency": latency,
            "w_safety": safety,
            "normalization_method": "sum_to_one",
        }
    )


def make_action(action_id: str, *, model: str, unit_cost: str) -> ActionV1:
    return ActionV1.model_validate(
        {
            "schema_version": "ActionV1",
            "action_id": action_id,
            "provider": "neuroforge",
            "model": model,
            "mode": ActionMode.STANDARD,
            "constraints": [],
            "model_key": model,
            "catalog_provider": "openai" if model.startswith("gpt") else "anthropic",
            "tier": "workhorse",
            "unit_cost_usd_per_mtok": Decimal(unit_cost),
        }
    )


def make_bandit_state(
    *,
    state_version: int,
    reward_mean: float = 0.5,
) -> BanditStateV1:
    preference_vector = make_preference_vector(quality=1.0, cost=1.0, latency=1.0, safety=1.0)
    action = make_action(
        "neuroforge:gpt-5-mini:standard",
        model="gpt-5-mini",
        unit_cost="2.25",
    )
    return BanditStateV1.model_validate(
        {
            "schema_version": "BanditStateV1",
            "tenant_id": "tenant-1",
            "policy_key": "forgeagents.assist.v1",
            "policy_version": "v1",
            "partition_key": "assist|small|low|reasoning:0|pref:balanced",
            "router_context": make_router_context().model_dump(mode="json"),
            "preference_vector": preference_vector.model_dump(mode="json"),
            "bandit_policy_id": "ts_v1",
            "state_version": state_version,
            "action_stats": [
                {
                    "schema_version": "BanditActionStatsV1",
                    "action": action.model_dump(mode="json"),
                    "count": max(state_version, 1),
                    "alpha": 1.0 + reward_mean,
                    "beta": 2.0 - reward_mean,
                    "mean_reward": reward_mean,
                    "cumulative_reward": reward_mean * max(state_version, 1),
                    "last_reward": reward_mean,
                    "last_selected_at": "2026-03-04T12:00:00Z",
                }
            ],
            "high_cost_action_fraction_limit": 0.5,
            "last_updated": "2026-03-04T12:00:00Z",
        }
    )


def make_reward_record(*, call_id: str) -> RewardRecordV1:
    return RewardRecordV1.model_validate(
        {
            "schema_version": "RewardRecordV1",
            "run_id": "assist:run-1",
            "call_id": call_id,
            "tenant_id": "tenant-1",
            "policy_key": "forgeagents.assist.v1",
            "policy_version": "v1",
            "partition_key": "assist|small|low|reasoning:0|pref:balanced",
            "action_id": "neuroforge:gpt-5-mini:standard",
            "bandit_policy_id": "ts_v1",
            "reward_version": "RewardV1",
            "reward_value": 0.75,
            "observed_cost_usd": "0.001250",
            "latency_ms": 425,
            "quality_score": 0.8,
            "safety_score": 0.95,
            "invariant_pass": True,
            "unit_tests_pass": True,
            "router_context": make_router_context().model_dump(mode="json"),
            "preference_vector": make_preference_vector(
                quality=1.0,
                cost=1.0,
                latency=1.0,
                safety=1.0,
            ).model_dump(mode="json"),
            "router_degraded": False,
            "created_at": datetime(2026, 3, 4, 12, 0, 1, tzinfo=timezone.utc).isoformat(),
        }
    )


def test_policy_envelope_can_be_upserted_and_fetched(db):
    upserted = upsert_policy_envelope("forgeagents.test.v1", make_policy(), db)
    assert upserted.policy_key == "forgeagents.test.v1"

    fetched = get_policy_envelope("forgeagents.test.v1", db)
    assert fetched.policy_version == "v1"
    assert fetched.model_whitelist == ["allowed-model"]


def test_policy_run_state_aggregates_ledger_and_finalization(db):
    upsert_policy_envelope("forgeagents.test.v1", make_policy(), db)
    append_policy_run_ledger_entry(make_ledger_entry("run-state", 1), db)
    append_policy_run_ledger_entry(make_ledger_entry("run-state", 2), db)
    finalize_policy_run(
        make_finalization("run-state", termination_reason="max_calls_per_run_reached"),
        db,
    )

    state = get_policy_run_state("run-state", db)
    assert state.state.exists is True
    assert state.state.finalized is True
    assert state.state.total_calls == 2
    assert state.state.total_prompt_tokens == 30
    assert state.state.total_completion_tokens == 15
    assert state.state.total_tokens == 45
    assert state.state.finalization is not None
    assert state.state.finalization.termination_reason == "max_calls_per_run_reached"


def test_finalized_run_rejects_additional_ledger_writes(db):
    upsert_policy_envelope("forgeagents.test.v1", make_policy(), db)
    append_policy_run_ledger_entry(make_ledger_entry("run-finalized", 1), db)
    finalize_policy_run(make_finalization("run-finalized"), db)

    with pytest.raises(HTTPException) as exc_info:
        append_policy_run_ledger_entry(make_ledger_entry("run-finalized", 2), db)

    assert exc_info.value.status_code == 409
    assert "rejects additional ledger writes" in exc_info.value.detail


def test_bandit_state_can_be_upserted_and_fetched(db):
    state = make_bandit_state(state_version=0)

    created = upsert_bandit_state("tenant-1", "forgeagents.assist.v1", state, db)
    assert created.status == "created"

    fetched = get_bandit_state(
        "tenant-1",
        "forgeagents.assist.v1",
        partition_key=state.partition_key,
        db=db,
    )
    assert fetched.state.partition_key == state.partition_key
    assert fetched.state.bandit_policy_id == "ts_v1"


def test_reward_record_can_be_appended(db):
    reward = make_reward_record(call_id="call-1")

    response = append_reward_record(reward, db)

    assert response.status == "created"
    assert response.reward.call_id == "call-1"


def test_bandit_outcome_records_state_and_reward_atomically(db):
    initial_state = make_bandit_state(state_version=1, reward_mean=0.60)
    reward = make_reward_record(call_id="call-atomic-1")
    outcome = BanditOutcomeV1.model_validate(
        {
            "state": initial_state.model_dump(mode="json"),
            "reward": reward.model_dump(mode="json"),
        }
    )

    recorded = record_bandit_outcome(outcome, db)

    assert recorded.status == "recorded"
    assert recorded.state.state_version == 1
    assert (
        db.query(LLMPolicyBanditStateModel)
        .filter(LLMPolicyBanditStateModel.tenant_id == "tenant-1")
        .count()
        == 1
    )
    assert (
        db.query(LLMPolicyRewardRecordModel)
        .filter(LLMPolicyRewardRecordModel.call_id == "call-atomic-1")
        .count()
        == 1
    )


def test_bandit_outcome_conflict_rolls_back_reward_write(db):
    initial_state = make_bandit_state(state_version=1, reward_mean=0.55)
    reward = make_reward_record(call_id="call-atomic-2")
    record_bandit_outcome(
        BanditOutcomeV1.model_validate(
            {
                "state": initial_state.model_dump(mode="json"),
                "reward": reward.model_dump(mode="json"),
            }
        ),
        db,
    )

    conflicting_state = make_bandit_state(state_version=1, reward_mean=0.90)
    conflicting_reward = make_reward_record(call_id="call-atomic-3")

    with pytest.raises(HTTPException) as exc_info:
        record_bandit_outcome(
            BanditOutcomeV1.model_validate(
                {
                    "state": conflicting_state.model_dump(mode="json"),
                    "reward": conflicting_reward.model_dump(mode="json"),
                }
            ),
            db,
        )

    assert exc_info.value.status_code == 409
    stored_state = get_bandit_state(
        "tenant-1",
        "forgeagents.assist.v1",
        partition_key=initial_state.partition_key,
        db=db,
    )
    assert stored_state.state.state_version == 1
    assert (
        db.query(LLMPolicyRewardRecordModel)
        .filter(LLMPolicyRewardRecordModel.call_id == "call-atomic-3")
        .count()
        == 0
    )

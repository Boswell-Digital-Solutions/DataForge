"""DataForge router for deterministic LLM policy envelopes and run ledgers."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.policy_envelope_models import (
    LLMPolicyBanditStateModel,
    LLMPolicyEnvelopeModel,
    LLMPolicyLedgerEntryModel,
    LLMPolicyRewardRecordModel,
    LLMPolicyRunFinalizationModel,
)
from app.models.policy_envelope_schemas import (
    BanditOutcomeResponse,
    BanditOutcomeV1,
    BanditStateEnvelope,
    BanditStateUpsertResponse,
    BanditStateV1,
    LedgerAppendResponse,
    LedgerEntryV1,
    PolicyEnvelopeRecordResponse,
    PolicyEnvelopeV1,
    PolicyRunStateEnvelope,
    PolicyRunStateResponse,
    RewardRecordResponse,
    RewardRecordV1,
    RunFinalizationResponse,
    RunFinalizationV1,
)

router = APIRouter(prefix="/api/v1", tags=["llm-policy"])


@router.put(
    "/policy-envelopes/{policy_key}",
    response_model=PolicyEnvelopeRecordResponse,
    summary="Create or update a deterministic policy envelope",
)
def upsert_policy_envelope(
    policy_key: str,
    envelope: PolicyEnvelopeV1,
    db: Session = Depends(get_db),
) -> PolicyEnvelopeRecordResponse:
    row = db.query(LLMPolicyEnvelopeModel).filter(
        LLMPolicyEnvelopeModel.policy_key == policy_key
    ).first()

    if row is None:
        row = LLMPolicyEnvelopeModel(
            policy_key=policy_key,
            policy_version=envelope.policy_version,
            envelope=envelope.model_dump(mode="json"),
            is_active=True,
        )
        db.add(row)
    else:
        row.policy_version = envelope.policy_version
        row.envelope = envelope.model_dump(mode="json")
        row.is_active = True

    db.commit()
    db.refresh(row)
    return PolicyEnvelopeRecordResponse(
        policy_key=row.policy_key,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        **row.envelope,
    )


@router.get(
    "/policy-envelopes/{policy_key}",
    response_model=PolicyEnvelopeRecordResponse,
    summary="Fetch a deterministic policy envelope",
)
def get_policy_envelope(
    policy_key: str,
    db: Session = Depends(get_db),
) -> PolicyEnvelopeRecordResponse:
    row = db.query(LLMPolicyEnvelopeModel).filter(
        LLMPolicyEnvelopeModel.policy_key == policy_key,
        LLMPolicyEnvelopeModel.is_active.is_(True),
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Policy envelope '{policy_key}' not found")

    return PolicyEnvelopeRecordResponse(
        policy_key=row.policy_key,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        **row.envelope,
    )


@router.get(
    "/policy-runs/{run_id}/state",
    response_model=PolicyRunStateEnvelope,
    summary="Fetch ledger aggregate and finalization state for a run",
)
def get_policy_run_state(
    run_id: str,
    db: Session = Depends(get_db),
) -> PolicyRunStateEnvelope:
    ledger_rows = db.query(LLMPolicyLedgerEntryModel).filter(
        LLMPolicyLedgerEntryModel.run_id == run_id
    )
    finalization_row = db.query(LLMPolicyRunFinalizationModel).filter(
        LLMPolicyRunFinalizationModel.run_id == run_id
    ).first()

    aggregate = ledger_rows.with_entities(
        func.count(LLMPolicyLedgerEntryModel.ledger_id),
        func.coalesce(func.sum(LLMPolicyLedgerEntryModel.prompt_tokens), 0),
        func.coalesce(func.sum(LLMPolicyLedgerEntryModel.completion_tokens), 0),
        func.coalesce(func.sum(LLMPolicyLedgerEntryModel.total_tokens), 0),
        func.coalesce(func.sum(LLMPolicyLedgerEntryModel.cost_estimated_usd), Decimal("0")),
        func.min(LLMPolicyLedgerEntryModel.started_at),
        func.max(LLMPolicyLedgerEntryModel.completed_at),
    ).first()

    started_at = aggregate[5]
    if started_at is None and finalization_row is not None:
        started_at = finalization_row.started_at

    finalization = None
    if finalization_row is not None:
        finalization = RunFinalizationV1(**finalization_row.finalization_payload)

    state = PolicyRunStateResponse(
        run_id=run_id,
        exists=bool((aggregate[0] or 0) or finalization_row),
        finalized=finalization_row is not None,
        total_calls=int(aggregate[0] or 0),
        total_prompt_tokens=int(aggregate[1] or 0),
        total_completion_tokens=int(aggregate[2] or 0),
        total_tokens=int(aggregate[3] or 0),
        total_cost_usd=Decimal(str(aggregate[4] or 0)),
        started_at=started_at,
        last_call_completed_at=aggregate[6],
        finalization=finalization,
    )
    return PolicyRunStateEnvelope(state=state)


@router.post(
    "/policy-runs/ledger",
    response_model=LedgerAppendResponse,
    status_code=201,
    summary="Append an immutable per-call ledger entry",
)
def append_policy_run_ledger_entry(
    entry: LedgerEntryV1,
    db: Session = Depends(get_db),
) -> LedgerAppendResponse:
    finalized = db.query(LLMPolicyRunFinalizationModel).filter(
        LLMPolicyRunFinalizationModel.run_id == entry.run_id
    ).first()
    if finalized is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Run '{entry.run_id}' is finalized and rejects additional ledger writes",
        )

    row = LLMPolicyLedgerEntryModel(
        ledger_id=entry.ledger_id,
        run_id=entry.run_id,
        sequence_no=entry.sequence_no,
        policy_key=entry.policy_key,
        policy_version=entry.policy_version,
        model=entry.model,
        provider=entry.provider,
        prompt_tokens=entry.prompt_tokens,
        completion_tokens=entry.completion_tokens,
        total_tokens=entry.total_tokens,
        cost_estimated_usd=entry.cost_estimated_usd,
        started_at=entry.started_at,
        completed_at=entry.completed_at,
        termination_reason=entry.termination_reason,
        entry_payload=entry.model_dump(mode="json"),
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Ledger append conflict for run '{entry.run_id}' sequence {entry.sequence_no}",
        ) from exc

    return LedgerAppendResponse(status="created", entry=entry)


@router.post(
    "/policy-runs/finalize",
    response_model=RunFinalizationResponse,
    status_code=201,
    summary="Finalize a run exactly once",
)
def finalize_policy_run(
    finalization: RunFinalizationV1,
    db: Session = Depends(get_db),
) -> RunFinalizationResponse:
    existing = db.query(LLMPolicyRunFinalizationModel).filter(
        LLMPolicyRunFinalizationModel.run_id == finalization.run_id
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Run '{finalization.run_id}' is already finalized",
        )

    row = LLMPolicyRunFinalizationModel(
        run_id=finalization.run_id,
        policy_key=finalization.policy_key,
        policy_version=finalization.policy_version,
        status=finalization.status,
        termination_reason=finalization.termination_reason,
        total_calls=finalization.total_calls,
        total_prompt_tokens=finalization.total_prompt_tokens,
        total_completion_tokens=finalization.total_completion_tokens,
        total_tokens=finalization.total_tokens,
        total_cost_usd=finalization.total_cost_usd,
        started_at=finalization.started_at,
        finalized_at=finalization.finalized_at,
        finalization_payload=finalization.model_dump(mode="json"),
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Run '{finalization.run_id}' is already finalized",
        ) from exc

    return RunFinalizationResponse(status="finalized", finalization=finalization)


@router.get(
    "/policy-routing/bandit-states/{tenant_id}/{policy_key}",
    response_model=BanditStateEnvelope,
    summary="Fetch a tenant-scoped Slice 2 bandit state partition",
)
def get_bandit_state(
    tenant_id: str,
    policy_key: str,
    partition_key: str,
    db: Session = Depends(get_db),
) -> BanditStateEnvelope:
    row = db.query(LLMPolicyBanditStateModel).filter(
        LLMPolicyBanditStateModel.tenant_id == tenant_id,
        LLMPolicyBanditStateModel.policy_key == policy_key,
        LLMPolicyBanditStateModel.partition_key == partition_key,
    ).first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Bandit state not found for "
                f"tenant='{tenant_id}' policy='{policy_key}' partition='{partition_key}'"
            ),
        )
    return BanditStateEnvelope(state=BanditStateV1.model_validate(row.state_payload))


@router.put(
    "/policy-routing/bandit-states/{tenant_id}/{policy_key}",
    response_model=BanditStateUpsertResponse,
    summary="Create or replace a tenant-scoped Slice 2 bandit state partition",
)
def upsert_bandit_state(
    tenant_id: str,
    policy_key: str,
    state: BanditStateV1,
    db: Session = Depends(get_db),
) -> BanditStateUpsertResponse:
    if state.tenant_id != tenant_id or state.policy_key != policy_key:
        raise HTTPException(
            status_code=400,
            detail="Path tenant/policy must match the BanditStateV1 payload",
        )

    row = db.query(LLMPolicyBanditStateModel).filter(
        LLMPolicyBanditStateModel.tenant_id == tenant_id,
        LLMPolicyBanditStateModel.policy_key == policy_key,
        LLMPolicyBanditStateModel.partition_key == state.partition_key,
    ).first()

    status_value = "updated"
    if row is None:
        row = LLMPolicyBanditStateModel(
            tenant_id=tenant_id,
            policy_key=policy_key,
            partition_key=state.partition_key,
        )
        db.add(row)
        status_value = "created"

    row.policy_version = state.policy_version
    row.bandit_policy_id = state.bandit_policy_id
    row.state_version = state.state_version
    row.state_payload = state.model_dump(mode="json")
    row.last_updated = state.last_updated

    db.commit()
    db.refresh(row)

    return BanditStateUpsertResponse(
        status=status_value,
        state=BanditStateV1.model_validate(row.state_payload),
    )


@router.post(
    "/policy-routing/rewards",
    response_model=RewardRecordResponse,
    status_code=201,
    summary="Append an immutable Slice 2 reward record",
)
def append_reward_record(
    reward: RewardRecordV1,
    db: Session = Depends(get_db),
) -> RewardRecordResponse:
    existing = db.query(LLMPolicyRewardRecordModel).filter(
        LLMPolicyRewardRecordModel.call_id == reward.call_id
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Reward record for call '{reward.call_id}' already exists",
        )

    row = LLMPolicyRewardRecordModel(
        call_id=reward.call_id,
        run_id=reward.run_id,
        tenant_id=reward.tenant_id,
        policy_key=reward.policy_key,
        policy_version=reward.policy_version,
        partition_key=reward.partition_key,
        action_id=reward.action_id,
        bandit_policy_id=reward.bandit_policy_id,
        reward_version=reward.reward_version,
        reward_value=reward.reward_value,
        router_degraded=reward.router_degraded,
        reward_payload=reward.model_dump(mode="json"),
        created_at=reward.created_at,
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Reward record for call '{reward.call_id}' already exists",
        ) from exc

    return RewardRecordResponse(status="created", reward=reward)


@router.post(
    "/policy-routing/outcomes",
    response_model=BanditOutcomeResponse,
    status_code=201,
    summary="Atomically update Slice 2 bandit state and append reward record",
)
def record_bandit_outcome(
    outcome: BanditOutcomeV1,
    db: Session = Depends(get_db),
) -> BanditOutcomeResponse:
    state = outcome.state
    reward = outcome.reward

    if state.tenant_id != reward.tenant_id:
        raise HTTPException(status_code=400, detail="State/reward tenant_id mismatch")
    if state.policy_key != reward.policy_key:
        raise HTTPException(status_code=400, detail="State/reward policy_key mismatch")
    if state.policy_version != reward.policy_version:
        raise HTTPException(status_code=400, detail="State/reward policy_version mismatch")
    if state.partition_key != reward.partition_key:
        raise HTTPException(status_code=400, detail="State/reward partition_key mismatch")
    if state.bandit_policy_id != reward.bandit_policy_id:
        raise HTTPException(status_code=400, detail="State/reward bandit_policy_id mismatch")

    if db.query(LLMPolicyRewardRecordModel).filter(
        LLMPolicyRewardRecordModel.call_id == reward.call_id
    ).first():
        raise HTTPException(
            status_code=409,
            detail=f"Reward record for call '{reward.call_id}' already exists",
        )

    state_row = db.query(LLMPolicyBanditStateModel).filter(
        LLMPolicyBanditStateModel.tenant_id == state.tenant_id,
        LLMPolicyBanditStateModel.policy_key == state.policy_key,
        LLMPolicyBanditStateModel.partition_key == state.partition_key,
    ).with_for_update().first()

    if state_row is None:
        if state.state_version not in (0, 1):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Bandit state version conflict for new partition "
                    f"'{state.partition_key}'"
                ),
            )
        state_row = LLMPolicyBanditStateModel(
            tenant_id=state.tenant_id,
            policy_key=state.policy_key,
            partition_key=state.partition_key,
        )
        db.add(state_row)
    else:
        expected_previous_version = max(state.state_version - 1, 0)
        if state_row.state_version != expected_previous_version:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Bandit state version conflict for "
                    f"tenant='{state.tenant_id}' policy='{state.policy_key}' "
                    f"partition='{state.partition_key}'"
                ),
            )

    reward_row = LLMPolicyRewardRecordModel(
        call_id=reward.call_id,
        run_id=reward.run_id,
        tenant_id=reward.tenant_id,
        policy_key=reward.policy_key,
        policy_version=reward.policy_version,
        partition_key=reward.partition_key,
        action_id=reward.action_id,
        bandit_policy_id=reward.bandit_policy_id,
        reward_version=reward.reward_version,
        reward_value=reward.reward_value,
        router_degraded=reward.router_degraded,
        reward_payload=reward.model_dump(mode="json"),
        created_at=reward.created_at,
    )
    db.add(reward_row)

    state_row.policy_version = state.policy_version
    state_row.bandit_policy_id = state.bandit_policy_id
    state_row.state_version = state.state_version
    state_row.state_payload = state.model_dump(mode="json")
    state_row.last_updated = state.last_updated

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"Bandit outcome conflict for tenant='{state.tenant_id}' "
                f"policy='{state.policy_key}' partition='{state.partition_key}'"
            ),
        ) from exc

    return BanditOutcomeResponse(status="recorded", state=state, reward=reward)

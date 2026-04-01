from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.runtime_promotion.execution_handoff.contracts import ExecutionState
from app.runtime_promotion.execution_handoff.contracts import FailureReasonClass
from app.runtime_promotion.execution_handoff.contracts import LocalRecommendationExecutionStatusV1
from app.runtime_promotion.execution_handoff.models import RuntimePromotionExecutionRequest
from app.runtime_promotion.execution_handoff.models import RuntimePromotionExecutionStatus
from app.runtime_promotion.execution_handoff.models import RuntimePromotionVerificationResult


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class ExecutionStatusCreate:
    execution_request_id: str
    execution_state: ExecutionState
    status_summary: str | None = None
    failure_reason_class: FailureReasonClass = FailureReasonClass.NONE
    operator_visible_notes: str | None = None
    artifact_refs: list[str] | None = None
    accepted_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    timed_out_at: datetime | None = None
    trace_id: str | None = None
    parent_artifact_id: str | None = None
    emitting_subsystem: str | None = None


@dataclass(slots=True)
class ExecutionStatusSummary:
    execution_request_id: str
    latest_execution_state: str | None
    latest_status_summary: str | None
    latest_failure_reason_class: str | None
    last_status_recorded_at: datetime | None


@dataclass(slots=True)
class VerificationResultSummary:
    execution_request_id: str
    observed_outcome: str | None
    verification_summary: str | None
    regression_detected: bool
    rollback_recommended: bool
    verified_at: datetime | None


def append_execution_status(
    session: Session,
    payload: ExecutionStatusCreate,
) -> RuntimePromotionExecutionStatus:
    execution_request = session.get(
        RuntimePromotionExecutionRequest,
        payload.execution_request_id,
    )
    if execution_request is None:
        raise ValueError(
            f"Execution request not found: {payload.execution_request_id}"
        )

    recorded_at = _utcnow()

    status = RuntimePromotionExecutionStatus(
        execution_status_id=_new_id(),
        trace_id=payload.trace_id or execution_request.trace_id,
        root_decision_artifact_id=execution_request.root_decision_artifact_id,
        parent_artifact_id=payload.parent_artifact_id
        or execution_request.execution_request_id,
        lineage_step=max(execution_request.lineage_step + 1, 2),
        emitting_subsystem=payload.emitting_subsystem
        or execution_request.target_subsystem,
        execution_request_id=payload.execution_request_id,
        execution_state=payload.execution_state.value,
        status_summary=payload.status_summary,
        failure_reason_class=payload.failure_reason_class.value,
        operator_visible_notes=payload.operator_visible_notes,
        artifact_refs_json=list(payload.artifact_refs or []),
        accepted_at=payload.accepted_at,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        failed_at=payload.failed_at,
        timed_out_at=payload.timed_out_at,
        recorded_at=recorded_at,
    )

    session.add(status)

    execution_request.request_status = _map_execution_state_to_request_status(
        payload.execution_state
    )
    execution_request.updated_at = recorded_at

    session.flush()
    return status


def get_latest_execution_status(
    session: Session,
    execution_request_id: str,
) -> RuntimePromotionExecutionStatus | None:
    return session.scalar(
        select(RuntimePromotionExecutionStatus)
        .where(
            RuntimePromotionExecutionStatus.execution_request_id
            == execution_request_id
        )
        .order_by(
            desc(RuntimePromotionExecutionStatus.recorded_at),
            desc(RuntimePromotionExecutionStatus.execution_status_id),
        )
        .limit(1)
    )


def get_latest_verification_result(
    session: Session,
    execution_request_id: str,
) -> RuntimePromotionVerificationResult | None:
    return session.scalar(
        select(RuntimePromotionVerificationResult)
        .where(
            RuntimePromotionVerificationResult.execution_request_id
            == execution_request_id
        )
        .order_by(
            desc(RuntimePromotionVerificationResult.verified_at),
            desc(RuntimePromotionVerificationResult.verification_artifact_id),
        )
        .limit(1)
    )


def build_execution_status_contract(
    status: RuntimePromotionExecutionStatus,
) -> LocalRecommendationExecutionStatusV1:
    return LocalRecommendationExecutionStatusV1(
        execution_status_id=status.execution_status_id,
        trace_id=status.trace_id,
        root_decision_artifact_id=status.root_decision_artifact_id,
        parent_artifact_id=status.parent_artifact_id,
        lineage_step=status.lineage_step,
        emitting_subsystem=status.emitting_subsystem,
        execution_request_id=status.execution_request_id,
        execution_state=ExecutionState(status.execution_state),
        accepted_at=status.accepted_at,
        started_at=status.started_at,
        completed_at=status.completed_at,
        failed_at=status.failed_at,
        timed_out_at=status.timed_out_at,
        status_summary=status.status_summary,
        failure_reason_class=FailureReasonClass(status.failure_reason_class),
        operator_visible_notes=status.operator_visible_notes,
        artifact_refs=list(status.artifact_refs_json or []),
        updated_at=status.recorded_at,
    )


def build_execution_status_summary(
    status: RuntimePromotionExecutionStatus | None,
    *,
    execution_request_id: str,
) -> ExecutionStatusSummary:
    if status is None:
        return ExecutionStatusSummary(
            execution_request_id=execution_request_id,
            latest_execution_state=None,
            latest_status_summary=None,
            latest_failure_reason_class=None,
            last_status_recorded_at=None,
        )

    return ExecutionStatusSummary(
        execution_request_id=execution_request_id,
        latest_execution_state=status.execution_state,
        latest_status_summary=status.status_summary,
        latest_failure_reason_class=status.failure_reason_class,
        last_status_recorded_at=status.recorded_at,
    )


def build_verification_result_summary(
    verification: RuntimePromotionVerificationResult | None,
    *,
    execution_request_id: str,
) -> VerificationResultSummary:
    if verification is None:
        return VerificationResultSummary(
            execution_request_id=execution_request_id,
            observed_outcome=None,
            verification_summary=None,
            regression_detected=False,
            rollback_recommended=False,
            verified_at=None,
        )

    return VerificationResultSummary(
        execution_request_id=execution_request_id,
        observed_outcome=verification.observed_outcome,
        verification_summary=verification.verification_summary,
        regression_detected=verification.regression_detected,
        rollback_recommended=verification.rollback_recommended,
        verified_at=verification.verified_at,
    )


def mark_execution_request_dead_lettered(
    session: Session,
    *,
    execution_request_id: str,
    status_summary: str,
    failure_reason_class: FailureReasonClass,
    operator_visible_notes: str | None = None,
    artifact_refs: list[str] | None = None,
    trace_id: str | None = None,
    parent_artifact_id: str | None = None,
    emitting_subsystem: str | None = None,
) -> RuntimePromotionExecutionStatus:
    summary = status_summary.strip()
    if not summary:
        raise ValueError("status_summary must be non-empty for dead-lettered status")

    if failure_reason_class == FailureReasonClass.NONE:
        raise ValueError(
            "failure_reason_class must be explicit for dead-lettered status"
        )

    return append_execution_status(
        session,
        ExecutionStatusCreate(
            execution_request_id=execution_request_id,
            execution_state=ExecutionState.DEAD_LETTERED,
            status_summary=summary,
            failure_reason_class=failure_reason_class,
            operator_visible_notes=operator_visible_notes,
            artifact_refs=artifact_refs,
            trace_id=trace_id,
            parent_artifact_id=parent_artifact_id,
            emitting_subsystem=emitting_subsystem,
        ),
    )


def _map_execution_state_to_request_status(execution_state: ExecutionState) -> str:
    if execution_state == ExecutionState.QUEUED:
        return "queued"
    if execution_state == ExecutionState.ACCEPTED:
        return "accepted"
    if execution_state == ExecutionState.RUNNING:
        return "running"
    if execution_state == ExecutionState.COMPLETED:
        return "completed"
    if execution_state == ExecutionState.FAILED:
        return "failed"
    if execution_state == ExecutionState.TIMED_OUT:
        return "timed_out"
    if execution_state == ExecutionState.ROLLED_BACK:
        return "rolled_back"
    if execution_state == ExecutionState.DEAD_LETTERED:
        return "dead_lettered"
    if execution_state == ExecutionState.VERIFICATION_PENDING:
        return "completed"

    raise ValueError(f"Unsupported execution state mapping: {execution_state}")
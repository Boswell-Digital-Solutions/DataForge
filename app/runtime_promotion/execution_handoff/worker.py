from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.runtime_promotion.execution_handoff.contracts import (
    AuthorizationClass,
    ExecutionRequestStatus,
    ExecutionState,
    FailureReasonClass,
    TargetLane,
    TargetSubsystem,
)
from app.runtime_promotion.execution_handoff.models import RuntimePromotionExecutionRequest
from app.runtime_promotion.execution_handoff.status_service import (
    ExecutionStatusCreate,
    append_execution_status,
)

FIRST_LOCAL_RUNTIME_ACTION = "process_local_failure_pattern"
CLAIMABLE_REQUEST_STATUSES = {
    ExecutionRequestStatus.CREATED.value,
    ExecutionRequestStatus.QUEUED.value,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class WorkerRunResult:
    execution_request_id: str
    terminal_state: str
    status_summary: str


class WorkerValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        failure_reason_class: FailureReasonClass,
    ) -> None:
        super().__init__(message)
        self.failure_reason_class = failure_reason_class


def claim_next_local_runtime_action_request(
    session: Session,
    *,
    emitting_subsystem: str = "forge_local_runtime",
) -> RuntimePromotionExecutionRequest | None:
    candidate = (
        session.query(RuntimePromotionExecutionRequest)
        .filter(
            RuntimePromotionExecutionRequest.target_lane
            == TargetLane.LOCAL_RUNTIME_ACTION.value,
            RuntimePromotionExecutionRequest.target_subsystem
            == TargetSubsystem.FORGE_LOCAL_RUNTIME.value,
            RuntimePromotionExecutionRequest.requested_action
            == FIRST_LOCAL_RUNTIME_ACTION,
            RuntimePromotionExecutionRequest.request_status.in_(CLAIMABLE_REQUEST_STATUSES),
        )
        .order_by(RuntimePromotionExecutionRequest.requested_at.asc())
        .first()
    )
    if candidate is None:
        return None

    claimed_at = _utcnow()

    claim_result = session.execute(
        update(RuntimePromotionExecutionRequest)
        .where(
            RuntimePromotionExecutionRequest.execution_request_id
            == candidate.execution_request_id,
            RuntimePromotionExecutionRequest.request_status.in_(CLAIMABLE_REQUEST_STATUSES),
        )
        .values(
            request_status=ExecutionRequestStatus.ACCEPTED.value,
            updated_at=claimed_at,
        )
    )
    if (claim_result.rowcount or 0) != 1:
        session.rollback()
        return None

    session.expire_all()

    claimed_request = session.get(
        RuntimePromotionExecutionRequest,
        candidate.execution_request_id,
    )
    if claimed_request is None:
        session.rollback()
        return None

    append_execution_status(
        session,
        ExecutionStatusCreate(
            execution_request_id=claimed_request.execution_request_id,
            execution_state=ExecutionState.ACCEPTED,
            status_summary="Execution request accepted by bounded local runtime lane.",
            accepted_at=claimed_at,
            emitting_subsystem=emitting_subsystem,
        ),
    )
    session.flush()
    return claimed_request


def run_one_local_runtime_action(
    session: Session,
    *,
    timeout_seconds: float = 30.0,
    emitting_subsystem: str = "forge_local_runtime",
) -> WorkerRunResult | None:
    execution_request = claim_next_local_runtime_action_request(
        session,
        emitting_subsystem=emitting_subsystem,
    )
    if execution_request is None:
        return None

    return execute_claimed_local_runtime_action(
        session,
        execution_request_id=execution_request.execution_request_id,
        timeout_seconds=timeout_seconds,
        emitting_subsystem=emitting_subsystem,
    )


def execute_claimed_local_runtime_action(
    session: Session,
    *,
    execution_request_id: str,
    timeout_seconds: float = 30.0,
    emitting_subsystem: str = "forge_local_runtime",
) -> WorkerRunResult:
    execution_request = session.get(
        RuntimePromotionExecutionRequest,
        execution_request_id,
    )
    if execution_request is None:
        raise ValueError(f"Execution request not found: {execution_request_id}")

    try:
        _validate_execution_request(execution_request)

        started_at = _utcnow()
        append_execution_status(
            session,
            ExecutionStatusCreate(
                execution_request_id=execution_request.execution_request_id,
                execution_state=ExecutionState.RUNNING,
                status_summary="Execution started in bounded local runtime lane.",
                started_at=started_at,
                emitting_subsystem=emitting_subsystem,
            ),
        )
        session.flush()

        started_monotonic = monotonic()
        artifact_refs = _perform_supported_local_runtime_action(execution_request)

        if monotonic() - started_monotonic > timeout_seconds:
            raise TimeoutError("Execution exceeded bounded timeout budget.")

        completed_at = _utcnow()
        status_summary = "Bounded local runtime action completed successfully."
        append_execution_status(
            session,
            ExecutionStatusCreate(
                execution_request_id=execution_request.execution_request_id,
                execution_state=ExecutionState.COMPLETED,
                status_summary=status_summary,
                artifact_refs=artifact_refs,
                completed_at=completed_at,
                emitting_subsystem=emitting_subsystem,
            ),
        )
        session.flush()

        return WorkerRunResult(
            execution_request_id=execution_request.execution_request_id,
            terminal_state=ExecutionState.COMPLETED.value,
            status_summary=status_summary,
        )
    except TimeoutError as exc:
        timed_out_at = _utcnow()
        status_summary = str(exc)
        append_execution_status(
            session,
            ExecutionStatusCreate(
                execution_request_id=execution_request.execution_request_id,
                execution_state=ExecutionState.TIMED_OUT,
                status_summary=status_summary,
                failure_reason_class=FailureReasonClass.TIMEOUT,
                timed_out_at=timed_out_at,
                emitting_subsystem=emitting_subsystem,
            ),
        )
        session.flush()

        return WorkerRunResult(
            execution_request_id=execution_request.execution_request_id,
            terminal_state=ExecutionState.TIMED_OUT.value,
            status_summary=status_summary,
        )
    except Exception as exc:
        failed_at = _utcnow()
        status_summary = str(exc)
        failure_reason_class = getattr(
            exc,
            "failure_reason_class",
            FailureReasonClass.INVALID_REQUEST,
        )
        append_execution_status(
            session,
            ExecutionStatusCreate(
                execution_request_id=execution_request.execution_request_id,
                execution_state=ExecutionState.FAILED,
                status_summary=status_summary,
                failure_reason_class=failure_reason_class,
                failed_at=failed_at,
                emitting_subsystem=emitting_subsystem,
            ),
        )
        session.flush()

        return WorkerRunResult(
            execution_request_id=execution_request.execution_request_id,
            terminal_state=ExecutionState.FAILED.value,
            status_summary=status_summary,
        )


def _validate_execution_request(
    execution_request: RuntimePromotionExecutionRequest,
) -> FailureReasonClass:
    if execution_request.request_status not in {
        ExecutionRequestStatus.ACCEPTED.value,
        ExecutionRequestStatus.RUNNING.value,
    }:
        raise WorkerValidationError(
            "Execution request is not in an executable claimed state.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if execution_request.target_lane != TargetLane.LOCAL_RUNTIME_ACTION.value:
        raise WorkerValidationError(
            "Unsupported target lane for bounded worker.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if execution_request.target_subsystem != TargetSubsystem.FORGE_LOCAL_RUNTIME.value:
        raise WorkerValidationError(
            "Unsupported target subsystem for bounded worker.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if execution_request.requested_action != FIRST_LOCAL_RUNTIME_ACTION:
        raise WorkerValidationError(
            "Unsupported requested_action for bounded worker.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    authorization_class = getattr(
        execution_request,
        "authorization_class",
        AuthorizationClass.OPERATIONAL.value,
    )
    if authorization_class != AuthorizationClass.OPERATIONAL.value:
        raise WorkerValidationError(
            "Authorization class is not acceptable for bounded worker execution.",
            failure_reason_class=FailureReasonClass.POLICY_BLOCKED,
        )

    bounded_parameters = execution_request.bounded_parameters_json or {}
    if not isinstance(bounded_parameters, dict):
        raise WorkerValidationError(
            "bounded_parameters_json must be a dictionary.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if bounded_parameters.get("worker_action") != FIRST_LOCAL_RUNTIME_ACTION:
        raise WorkerValidationError(
            "bounded_parameters_json.worker_action mismatch.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if not bounded_parameters.get("candidate_id"):
        raise WorkerValidationError(
            "bounded_parameters_json.candidate_id is required.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if not bounded_parameters.get("issue_class"):
        raise WorkerValidationError(
            "bounded_parameters_json.issue_class is required.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    if execution_request.requested_action != FIRST_LOCAL_RUNTIME_ACTION:
        raise WorkerValidationError(
            "Unsupported bounded action for first worker slice.",
            failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        )

    return FailureReasonClass.NONE


def _perform_supported_local_runtime_action(
    execution_request: RuntimePromotionExecutionRequest,
) -> list[str]:
    bounded_parameters = execution_request.bounded_parameters_json or {}

    candidate_id = str(bounded_parameters["candidate_id"]).strip()
    issue_class = str(bounded_parameters["issue_class"]).strip()
    service = str(bounded_parameters.get("service") or "unknown_service").strip()

    if not candidate_id:
        raise ValueError("candidate_id must not be empty.")
    if not issue_class:
        raise ValueError("issue_class must not be empty.")

    return [
        f"worker_action:{FIRST_LOCAL_RUNTIME_ACTION}",
        f"candidate:{candidate_id}",
        f"service:{service}",
        f"issue_class:{issue_class}",
    ]
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.runtime_promotion.execution_handoff.contracts import AuthorizationClass
from app.runtime_promotion.execution_handoff.contracts import DecisionType
from app.runtime_promotion.execution_handoff.contracts import ExecutionClass
from app.runtime_promotion.execution_handoff.contracts import ExecutionRequestClass
from app.runtime_promotion.execution_handoff.contracts import ExecutionRequestStatus
from app.runtime_promotion.execution_handoff.contracts import HandoffStatus
from app.runtime_promotion.execution_handoff.contracts import (
    LocalRecommendationApprovalDecisionV1,
)
from app.runtime_promotion.execution_handoff.contracts import (
    LocalRecommendationExecutionRequestV1,
)
from app.runtime_promotion.execution_handoff.contracts import (
    LocalRecommendationVerificationResultV1,
)
from app.runtime_promotion.execution_handoff.contracts import RiskClass
from app.runtime_promotion.execution_handoff.contracts import SourceDomain
from app.runtime_promotion.execution_handoff.contracts import TargetLane
from app.runtime_promotion.execution_handoff.contracts import TargetSubsystem
from app.runtime_promotion.execution_handoff.contracts import VerificationObservedOutcome
from app.runtime_promotion.execution_handoff.models import RuntimePromotionApprovalDecision
from app.runtime_promotion.execution_handoff.models import RuntimePromotionExecutionRequest
from app.runtime_promotion.execution_handoff.models import RuntimePromotionVerificationResult


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


def _new_trace_id() -> str:
    return str(uuid4())


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def build_execution_request_idempotency_key(
    *,
    candidate_id: str,
    decision_artifact_id: str,
    execution_class: str,
    target_lane: str,
) -> str:
    raw = "::".join(
        [
            candidate_id.strip(),
            decision_artifact_id.strip(),
            execution_class.strip(),
            target_lane.strip(),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _append_unique_evidence_ref(
    evidence_refs: list[str],
    value: str | None,
) -> None:
    if value is None:
        return

    normalized = value.strip()
    if not normalized:
        return

    if normalized not in evidence_refs:
        evidence_refs.append(normalized)


def _get_worker_execution_result(
    execution_request: RuntimePromotionExecutionRequest,
) -> dict | None:
    bounded_parameters = execution_request.bounded_parameters_json or {}
    if not isinstance(bounded_parameters, dict):
        return None

    worker_execution_result = bounded_parameters.get("worker_execution_result")
    if not isinstance(worker_execution_result, dict):
        return None

    return worker_execution_result


def _build_verification_evidence_refs(
    execution_request: RuntimePromotionExecutionRequest,
    explicit_evidence_refs: list[str] | None,
) -> list[str]:
    evidence_refs: list[str] = []

    for ref in explicit_evidence_refs or []:
        _append_unique_evidence_ref(evidence_refs, ref)

    worker_execution_result = _get_worker_execution_result(execution_request)
    if worker_execution_result is None:
        return evidence_refs

    _append_unique_evidence_ref(
        evidence_refs,
        "verification:evidence:worker_execution_result_present",
    )

    maintenance_action_class = worker_execution_result.get("maintenance_action_class")
    if isinstance(maintenance_action_class, str) and maintenance_action_class.strip():
        _append_unique_evidence_ref(
            evidence_refs,
            (
                "verification:evidence:maintenance_action_class:"
                f"{maintenance_action_class.strip()}"
            ),
        )

    target_capability = worker_execution_result.get("target_capability")
    if isinstance(target_capability, str) and target_capability.strip():
        _append_unique_evidence_ref(
            evidence_refs,
            (
                "verification:evidence:target_capability:"
                f"{target_capability.strip()}"
            ),
        )

    return evidence_refs


def _build_grounded_verification_summary(
    execution_request: RuntimePromotionExecutionRequest,
    explicit_summary: str,
) -> str:
    base_summary = explicit_summary.strip()
    if not base_summary:
        return explicit_summary

    if "Verification basis:" in base_summary:
        return base_summary

    worker_execution_result = _get_worker_execution_result(execution_request)
    if worker_execution_result is None:
        return base_summary

    basis_parts = ["worker_execution_result present"]

    maintenance_action_class = _normalize_text(
        worker_execution_result.get("maintenance_action_class")
        if isinstance(worker_execution_result.get("maintenance_action_class"), str)
        else None
    )
    if maintenance_action_class is not None:
        basis_parts.append(
            f"maintenance_action_class={maintenance_action_class}"
        )

    target_capability = _normalize_text(
        worker_execution_result.get("target_capability")
        if isinstance(worker_execution_result.get("target_capability"), str)
        else None
    )
    if target_capability is not None:
        basis_parts.append(f"target_capability={target_capability}")

    return f"{base_summary} Verification basis: {'; '.join(basis_parts)}."


@dataclass(slots=True)
class ApprovalDecisionCreate:
    candidate_id: str
    recommendation_id: str
    operator_note: str | None
    approved_by: str | None = None
    source_domain: SourceDomain = SourceDomain.LOCAL
    authorization_class: AuthorizationClass = AuthorizationClass.OPERATIONAL
    execution_required: bool = True
    execution_class: ExecutionClass | None = ExecutionClass.LOCAL_RUNTIME_ACTION
    trace_id: str | None = None
    emitting_subsystem: str = "dataforge"


@dataclass(slots=True)
class ExecutionRequestCreate:
    candidate_id: str
    decision_artifact_id: str
    target_scope: str
    requested_action: str
    bounded_parameters: dict
    risk_class: RiskClass = RiskClass.LOW
    rollback_required: bool = False
    target_subsystem: TargetSubsystem = TargetSubsystem.FORGE_LOCAL_RUNTIME
    target_lane: TargetLane = TargetLane.LOCAL_RUNTIME_ACTION
    trace_id: str | None = None
    emitting_subsystem: str = "dataforge"


@dataclass(slots=True)
class ExecutionRequestUpsertResult:
    execution_request: RuntimePromotionExecutionRequest
    created: bool


@dataclass(slots=True)
class VerificationResultCreate:
    execution_request_id: str
    candidate_id: str
    verification_scope: str
    expected_gain: str
    observed_outcome: VerificationObservedOutcome
    verification_summary: str
    regression_detected: bool = False
    rollback_recommended: bool = False
    evidence_refs: list[str] | None = None
    trace_id: str | None = None
    parent_artifact_id: str | None = None
    emitting_subsystem: str = "dataforge"


def create_approval_decision(
    session: Session,
    payload: ApprovalDecisionCreate,
) -> RuntimePromotionApprovalDecision:
    approved_at = _utcnow()

    handoff_status = HandoffStatus.HANDOFF_NOT_REQUIRED
    if (
        payload.source_domain == SourceDomain.LOCAL
        and payload.execution_required
        and payload.execution_class == ExecutionClass.LOCAL_RUNTIME_ACTION
    ):
        handoff_status = HandoffStatus.HANDOFF_ELIGIBLE

    decision_artifact_id = _new_id()
    trace_id = payload.trace_id or _new_trace_id()

    decision = RuntimePromotionApprovalDecision(
        decision_artifact_id=decision_artifact_id,
        trace_id=trace_id,
        root_decision_artifact_id=decision_artifact_id,
        parent_artifact_id=None,
        lineage_step=0,
        emitting_subsystem=payload.emitting_subsystem,
        candidate_id=payload.candidate_id,
        recommendation_id=payload.recommendation_id,
        decision_type=DecisionType.APPROVE.value,
        operator_note=payload.operator_note,
        approved_at=approved_at,
        approved_by=payload.approved_by,
        source_domain=payload.source_domain.value,
        authorization_class=payload.authorization_class.value,
        execution_required=payload.execution_required,
        execution_class=payload.execution_class.value if payload.execution_class else None,
        handoff_status=handoff_status.value,
        created_at=approved_at,
        updated_at=approved_at,
    )

    session.add(decision)
    session.flush()
    return decision


def create_approval_decision_contract(
    decision: RuntimePromotionApprovalDecision,
) -> LocalRecommendationApprovalDecisionV1:
    return LocalRecommendationApprovalDecisionV1(
        decision_artifact_id=decision.decision_artifact_id,
        trace_id=decision.trace_id,
        root_decision_artifact_id=decision.root_decision_artifact_id,
        parent_artifact_id=decision.parent_artifact_id,
        lineage_step=decision.lineage_step,
        emitting_subsystem=decision.emitting_subsystem,
        candidate_id=decision.candidate_id,
        recommendation_id=decision.recommendation_id,
        decision_type=DecisionType(decision.decision_type),
        operator_note=decision.operator_note,
        approved_at=decision.approved_at,
        approved_by=decision.approved_by,
        source_domain=SourceDomain(decision.source_domain),
        authorization_class=AuthorizationClass(decision.authorization_class),
        execution_required=decision.execution_required,
        execution_class=(
            ExecutionClass(decision.execution_class)
            if decision.execution_class
            else None
        ),
        status=HandoffStatus(decision.handoff_status),
    )


def create_or_get_execution_request(
    session: Session,
    *,
    decision: RuntimePromotionApprovalDecision,
    payload: ExecutionRequestCreate,
) -> ExecutionRequestUpsertResult:
    if decision.handoff_status != HandoffStatus.HANDOFF_ELIGIBLE.value:
        raise ValueError("Decision is not handoff eligible.")

    if decision.execution_class != ExecutionClass.LOCAL_RUNTIME_ACTION.value:
        raise ValueError("Unsupported execution class for Slice 1.")

    idempotency_key = build_execution_request_idempotency_key(
        candidate_id=payload.candidate_id,
        decision_artifact_id=payload.decision_artifact_id,
        execution_class=decision.execution_class,
        target_lane=payload.target_lane.value,
    )

    existing = session.scalar(
        select(RuntimePromotionExecutionRequest).where(
            RuntimePromotionExecutionRequest.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return ExecutionRequestUpsertResult(
            execution_request=existing,
            created=False,
        )

    requested_at = _utcnow()
    trace_id = payload.trace_id or decision.trace_id

    execution_request = RuntimePromotionExecutionRequest(
        execution_request_id=_new_id(),
        trace_id=trace_id,
        root_decision_artifact_id=decision.root_decision_artifact_id,
        parent_artifact_id=decision.decision_artifact_id,
        lineage_step=1,
        emitting_subsystem=payload.emitting_subsystem,
        candidate_id=payload.candidate_id,
        decision_artifact_id=payload.decision_artifact_id,
        request_class=ExecutionRequestClass.APPROVED_RECOMMENDATION_HANDOFF.value,
        target_subsystem=payload.target_subsystem.value,
        target_lane=payload.target_lane.value,
        target_scope=payload.target_scope,
        requested_action=payload.requested_action,
        bounded_parameters_json=payload.bounded_parameters,
        risk_class=payload.risk_class.value,
        rollback_required=payload.rollback_required,
        idempotency_key=idempotency_key,
        requested_at=requested_at,
        request_status=ExecutionRequestStatus.CREATED.value,
        created_at=requested_at,
        updated_at=requested_at,
    )

    session.add(execution_request)
    session.flush()

    return ExecutionRequestUpsertResult(
        execution_request=execution_request,
        created=True,
    )


def create_execution_request_contract(
    execution_request: RuntimePromotionExecutionRequest,
) -> LocalRecommendationExecutionRequestV1:
    return LocalRecommendationExecutionRequestV1(
        execution_request_id=execution_request.execution_request_id,
        trace_id=execution_request.trace_id,
        root_decision_artifact_id=execution_request.root_decision_artifact_id,
        parent_artifact_id=execution_request.parent_artifact_id,
        lineage_step=execution_request.lineage_step,
        emitting_subsystem=execution_request.emitting_subsystem,
        candidate_id=execution_request.candidate_id,
        decision_artifact_id=execution_request.decision_artifact_id,
        request_class=ExecutionRequestClass(execution_request.request_class),
        target_subsystem=TargetSubsystem(execution_request.target_subsystem),
        target_lane=TargetLane(execution_request.target_lane),
        target_scope=execution_request.target_scope,
        requested_action=execution_request.requested_action,
        bounded_parameters=execution_request.bounded_parameters_json or {},
        risk_class=RiskClass(execution_request.risk_class),
        rollback_required=execution_request.rollback_required,
        idempotency_key=execution_request.idempotency_key,
        requested_at=execution_request.requested_at,
        request_status=ExecutionRequestStatus(execution_request.request_status),
    )


def create_verification_result(
    session: Session,
    payload: VerificationResultCreate,
) -> RuntimePromotionVerificationResult:
    execution_request = session.get(
        RuntimePromotionExecutionRequest,
        payload.execution_request_id,
    )
    if execution_request is None:
        raise ValueError(
            f"Execution request not found: {payload.execution_request_id}"
        )

    verified_at = _utcnow()
    evidence_refs = _build_verification_evidence_refs(
        execution_request,
        payload.evidence_refs,
    )
    verification_summary = _build_grounded_verification_summary(
        execution_request,
        payload.verification_summary,
    )

    verification = RuntimePromotionVerificationResult(
        verification_artifact_id=_new_id(),
        trace_id=payload.trace_id or execution_request.trace_id,
        root_decision_artifact_id=execution_request.root_decision_artifact_id,
        parent_artifact_id=payload.parent_artifact_id
        or execution_request.execution_request_id,
        lineage_step=max(execution_request.lineage_step + 2, 3),
        emitting_subsystem=payload.emitting_subsystem,
        execution_request_id=payload.execution_request_id,
        candidate_id=payload.candidate_id,
        verification_scope=payload.verification_scope,
        expected_gain=payload.expected_gain,
        observed_outcome=payload.observed_outcome.value,
        regression_detected=payload.regression_detected,
        rollback_recommended=payload.rollback_recommended,
        verification_summary=verification_summary,
        evidence_refs_json=evidence_refs,
        verified_at=verified_at,
    )

    session.add(verification)
    session.flush()
    return verification


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


def create_verification_result_contract(
    verification: RuntimePromotionVerificationResult,
) -> LocalRecommendationVerificationResultV1:
    return LocalRecommendationVerificationResultV1(
        verification_artifact_id=verification.verification_artifact_id,
        trace_id=verification.trace_id,
        root_decision_artifact_id=verification.root_decision_artifact_id,
        parent_artifact_id=verification.parent_artifact_id,
        lineage_step=verification.lineage_step,
        emitting_subsystem=verification.emitting_subsystem,
        execution_request_id=verification.execution_request_id,
        candidate_id=verification.candidate_id,
        verification_scope=verification.verification_scope,
        expected_gain=verification.expected_gain,
        observed_outcome=VerificationObservedOutcome(verification.observed_outcome),
        regression_detected=verification.regression_detected,
        rollback_recommended=verification.rollback_recommended,
        verification_summary=verification.verification_summary,
        evidence_refs=list(verification.evidence_refs_json or []),
        verified_at=verification.verified_at,
    )
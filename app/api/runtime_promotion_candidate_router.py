from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.runtime_promotion_candidate_models import (
    RuntimePromotionCandidate,
    RuntimePromotionCandidateDecision,
)
from app.models.runtime_promotion_candidate_schemas import (
    RuntimePromotionCandidateActionRequest,
    RuntimePromotionCandidateActionResponse,
    RuntimePromotionCandidateDecisionEntry,
    RuntimePromotionCandidateDetail,
    RuntimePromotionCandidateSummary,
)
from app.runtime_promotion.execution_handoff.contracts import HandoffStatus
from app.runtime_promotion.execution_handoff.service import (
    ApprovalDecisionCreate,
    ExecutionRequestCreate,
    create_approval_decision,
    create_approval_decision_contract,
    create_execution_request_contract,
    create_or_get_execution_request,
    create_verification_result_contract,
    get_latest_verification_result,
)
from app.runtime_promotion.execution_handoff.status_service import (
    build_execution_status_contract,
    build_execution_status_summary,
    build_verification_result_summary,
    get_latest_execution_status,
)

router = APIRouter(
    prefix="/api/v1/runtime-promotion/candidates",
    tags=["runtime-promotion-candidates"],
)

FIRST_LOCAL_RUNTIME_ACTION = "process_local_failure_pattern"


@router.get("", response_model=list[RuntimePromotionCandidateSummary])
def list_runtime_promotion_candidates(
    db: Session = Depends(get_db),
) -> list[RuntimePromotionCandidate]:
    return (
        db.query(RuntimePromotionCandidate)
        .order_by(RuntimePromotionCandidate.created_at.desc())
        .all()
    )


@router.get("/{candidate_id}", response_model=RuntimePromotionCandidateDetail)
def get_runtime_promotion_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> RuntimePromotionCandidateDetail:
    row = (
        db.query(RuntimePromotionCandidate)
        .filter(RuntimePromotionCandidate.candidate_id == candidate_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    history_rows = (
        db.query(RuntimePromotionCandidateDecision)
        .filter(RuntimePromotionCandidateDecision.candidate_id == candidate_id)
        .order_by(RuntimePromotionCandidateDecision.created_at.desc())
        .all()
    )

    execution_handoff = _build_execution_handoff_detail(
        candidate_id=row.candidate_id,
        db=db,
    )

    detail = RuntimePromotionCandidateDetail(
        candidate_id=row.candidate_id,
        receipt_id=row.receipt_id,
        candidate_type=row.candidate_type,
        source_envelope_type=row.source_envelope_type,
        service=row.service,
        fleet_member_id=row.fleet_member_id,
        issue_class=row.issue_class,
        severity=row.severity,
        title=row.title,
        summary=row.summary,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        evidence=row.evidence,
        source_payload=row.source_payload,
        decision_history=[
            RuntimePromotionCandidateDecisionEntry.model_validate(entry)
            for entry in history_rows
        ],
        execution_handoff=execution_handoff,
    )

    return detail


@router.post("/{candidate_id}/approve", response_model=RuntimePromotionCandidateActionResponse)
def approve_runtime_promotion_candidate(
    candidate_id: str,
    body: RuntimePromotionCandidateActionRequest,
    db: Session = Depends(get_db),
) -> RuntimePromotionCandidateActionResponse:
    return _apply_candidate_decision(
        candidate_id=candidate_id,
        new_status="approved",
        body=body,
        db=db,
    )


@router.post("/{candidate_id}/reject", response_model=RuntimePromotionCandidateActionResponse)
def reject_runtime_promotion_candidate(
    candidate_id: str,
    body: RuntimePromotionCandidateActionRequest,
    db: Session = Depends(get_db),
) -> RuntimePromotionCandidateActionResponse:
    return _apply_candidate_decision(
        candidate_id=candidate_id,
        new_status="rejected",
        body=body,
        db=db,
    )


def _apply_candidate_decision(
    candidate_id: str,
    new_status: str,
    body: RuntimePromotionCandidateActionRequest,
    db: Session,
) -> RuntimePromotionCandidateActionResponse:
    row = (
        db.query(RuntimePromotionCandidate)
        .filter(RuntimePromotionCandidate.candidate_id == candidate_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    prior_status = row.status
    row.status = new_status

    decision = RuntimePromotionCandidateDecision(
        candidate_id=row.candidate_id,
        prior_status=prior_status,
        new_status=new_status,
        operator_note=(body.reason or "").strip() or None,
        operator_identity=(body.operator_identity or "").strip() or "forgecommand",
    )

    db.add(decision)
    db.add(row)

    handoff_message: str | None = None

    if new_status == "approved":
        approval_decision = create_approval_decision(
            db,
            ApprovalDecisionCreate(
                candidate_id=row.candidate_id,
                recommendation_id=row.candidate_id,
                operator_note=decision.operator_note,
                approved_by=decision.operator_identity,
            ),
        )

        approval_contract = create_approval_decision_contract(approval_decision)

        if approval_contract.status == HandoffStatus.HANDOFF_ELIGIBLE:
            execution_request_result = create_or_get_execution_request(
                db,
                decision=approval_decision,
                payload=ExecutionRequestCreate(
                    candidate_id=row.candidate_id,
                    decision_artifact_id=approval_decision.decision_artifact_id,
                    target_scope=f"runtime_promotion_candidate:{row.candidate_id}",
                    requested_action=FIRST_LOCAL_RUNTIME_ACTION,
                    bounded_parameters={
                        "candidate_id": row.candidate_id,
                        "service": row.service,
                        "issue_class": row.issue_class,
                        "severity": row.severity,
                        "source_envelope_type": row.source_envelope_type,
                        "worker_action": FIRST_LOCAL_RUNTIME_ACTION,
                    },
                ),
            )
            execution_request_contract = create_execution_request_contract(
                execution_request_result.execution_request
            )
            if execution_request_result.created:
                handoff_message = (
                    " Execution handoff created: "
                    f"{execution_request_contract.execution_request_id}."
                )
            else:
                handoff_message = (
                    " Execution handoff already existed: "
                    f"{execution_request_contract.execution_request_id}."
                )
        elif approval_contract.status == HandoffStatus.HANDOFF_BLOCKED:
            handoff_message = " Execution handoff blocked under current rules."
        else:
            handoff_message = " Execution handoff not required."

    db.commit()
    db.refresh(row)

    verb = "approved" if new_status == "approved" else "rejected"
    if decision.operator_note:
        message = f"Candidate {verb}. Operator note captured: {decision.operator_note}"
    else:
        message = f"Candidate {verb}."

    if handoff_message:
        message += handoff_message

    return RuntimePromotionCandidateActionResponse(
        ok=True,
        candidate_id=row.candidate_id,
        status=row.status,
        message=message,
    )


def _build_execution_handoff_detail(
    *,
    candidate_id: str,
    db: Session,
) -> dict | None:
    from app.runtime_promotion.execution_handoff.models import (
        RuntimePromotionApprovalDecision,
        RuntimePromotionExecutionRequest,
    )

    approval = (
        db.query(RuntimePromotionApprovalDecision)
        .filter(RuntimePromotionApprovalDecision.candidate_id == candidate_id)
        .order_by(RuntimePromotionApprovalDecision.approved_at.desc())
        .first()
    )

    if approval is None:
        return None

    execution_request = (
        db.query(RuntimePromotionExecutionRequest)
        .filter(
            RuntimePromotionExecutionRequest.decision_artifact_id
            == approval.decision_artifact_id
        )
        .order_by(RuntimePromotionExecutionRequest.requested_at.desc())
        .first()
    )

    if execution_request is None:
        latest_status_summary = build_execution_status_summary(
            None,
            execution_request_id="",
        )
        latest_verification_summary = build_verification_result_summary(
            None,
            execution_request_id="",
        )
        return {
            "handoff_exists": False,
            "handoff_status": approval.handoff_status,
            "decision_artifact_id": approval.decision_artifact_id,
            "trace_id": approval.trace_id,
            "root_decision_artifact_id": approval.root_decision_artifact_id,
            "parent_artifact_id": approval.parent_artifact_id,
            "lineage_step": approval.lineage_step,
            "emitting_subsystem": approval.emitting_subsystem,
            "execution_request": None,
            "latest_execution_status": None,
            "latest_execution_summary": {
                "execution_request_id": latest_status_summary.execution_request_id,
                "latest_execution_state": latest_status_summary.latest_execution_state,
                "latest_status_summary": latest_status_summary.latest_status_summary,
                "latest_failure_reason_class": latest_status_summary.latest_failure_reason_class,
                "last_status_recorded_at": latest_status_summary.last_status_recorded_at,
            },
            "latest_verification": None,
            "latest_verification_summary": {
                "execution_request_id": latest_verification_summary.execution_request_id,
                "observed_outcome": latest_verification_summary.observed_outcome,
                "verification_summary": latest_verification_summary.verification_summary,
                "regression_detected": latest_verification_summary.regression_detected,
                "rollback_recommended": latest_verification_summary.rollback_recommended,
                "verified_at": latest_verification_summary.verified_at,
            },
        }

    latest_status = get_latest_execution_status(
        db,
        execution_request.execution_request_id,
    )
    latest_verification = get_latest_verification_result(
        db,
        execution_request.execution_request_id,
    )

    latest_status_contract = (
        build_execution_status_contract(latest_status)
        if latest_status is not None
        else None
    )
    latest_status_summary = build_execution_status_summary(
        latest_status,
        execution_request_id=execution_request.execution_request_id,
    )

    latest_verification_contract = (
        create_verification_result_contract(latest_verification)
        if latest_verification is not None
        else None
    )
    latest_verification_summary = build_verification_result_summary(
        latest_verification,
        execution_request_id=execution_request.execution_request_id,
    )

    return {
        "handoff_exists": True,
        "handoff_status": approval.handoff_status,
        "decision_artifact_id": approval.decision_artifact_id,
        "trace_id": approval.trace_id,
        "root_decision_artifact_id": approval.root_decision_artifact_id,
        "parent_artifact_id": approval.parent_artifact_id,
        "lineage_step": approval.lineage_step,
        "emitting_subsystem": approval.emitting_subsystem,
        "execution_request": create_execution_request_contract(
            execution_request
        ).model_dump(),
        "latest_execution_status": (
            latest_status_contract.model_dump()
            if latest_status_contract is not None
            else None
        ),
        "latest_execution_summary": {
            "execution_request_id": latest_status_summary.execution_request_id,
            "latest_execution_state": latest_status_summary.latest_execution_state,
            "latest_status_summary": latest_status_summary.latest_status_summary,
            "latest_failure_reason_class": latest_status_summary.latest_failure_reason_class,
            "last_status_recorded_at": latest_status_summary.last_status_recorded_at,
        },
        "latest_verification": (
            latest_verification_contract.model_dump()
            if latest_verification_contract is not None
            else None
        ),
        "latest_verification_summary": {
            "execution_request_id": latest_verification_summary.execution_request_id,
            "observed_outcome": latest_verification_summary.observed_outcome,
            "verification_summary": latest_verification_summary.verification_summary,
            "regression_detected": latest_verification_summary.regression_detected,
            "rollback_recommended": latest_verification_summary.rollback_recommended,
            "verified_at": latest_verification_summary.verified_at,
        },
    }
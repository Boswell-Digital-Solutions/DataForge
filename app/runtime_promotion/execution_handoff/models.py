from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database import Base


def _uuid_str() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RuntimePromotionApprovalDecision(Base):
    __tablename__ = "runtime_promotion_approval_decisions"

    decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=_uuid_str,
    )
    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    root_decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    parent_artifact_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    lineage_step: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    emitting_subsystem: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    recommendation_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    decision_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    operator_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    source_domain: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    authorization_class: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    execution_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    execution_class: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    handoff_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="handoff_not_required",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        Index(
            "ix_runtime_promotion_approval_decisions_candidate_approved",
            "candidate_id",
            "approved_at",
        ),
    )


class RuntimePromotionExecutionRequest(Base):
    __tablename__ = "runtime_promotion_execution_requests"

    execution_request_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=_uuid_str,
    )
    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    root_decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    parent_artifact_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    lineage_step: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )
    emitting_subsystem: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "runtime_promotion_approval_decisions.decision_artifact_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    request_class: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="approved_recommendation_handoff",
    )
    target_subsystem: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="forge_local_runtime",
    )
    target_lane: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="local_runtime_action",
    )
    target_scope: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    requested_action: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    bounded_parameters_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    risk_class: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    rollback_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    request_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="created",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        Index(
            "ix_runtime_promotion_execution_requests_candidate_status",
            "candidate_id",
            "request_status",
        ),
        Index(
            "ix_runtime_promotion_execution_requests_lane_status",
            "target_lane",
            "request_status",
        ),
    )


class RuntimePromotionExecutionStatus(Base):
    __tablename__ = "runtime_promotion_execution_statuses"

    execution_status_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=_uuid_str,
    )
    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    root_decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    parent_artifact_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    lineage_step: Mapped[int] = mapped_column(
        nullable=False,
        default=2,
    )
    emitting_subsystem: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    execution_request_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "runtime_promotion_execution_requests.execution_request_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    execution_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    status_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    failure_reason_class: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="none",
        index=True,
    )
    operator_visible_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    artifact_refs_json: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    timed_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )

    __table_args__ = (
        Index(
            "ix_runtime_promotion_execution_statuses_request_recorded",
            "execution_request_id",
            "recorded_at",
        ),
    )


class RuntimePromotionVerificationResult(Base):
    __tablename__ = "runtime_promotion_verification_results"

    verification_artifact_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=_uuid_str,
    )
    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    root_decision_artifact_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    parent_artifact_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    lineage_step: Mapped[int] = mapped_column(
        nullable=False,
        default=3,
    )
    emitting_subsystem: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    execution_request_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "runtime_promotion_execution_requests.execution_request_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    verification_scope: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    expected_gain: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    observed_outcome: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    regression_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    rollback_recommended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    verification_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )

    __table_args__ = (
        Index(
            "ix_runtime_promotion_verification_results_request_verified",
            "execution_request_id",
            "verified_at",
        ),
    )
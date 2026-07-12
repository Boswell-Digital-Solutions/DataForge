"""runtime promotion execution handoff tables

Revision ID: 20260401_01
Revises:
Create Date: 2026-04-01 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_01"
down_revision = "20260401_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_promotion_approval_decisions",
        sa.Column("decision_artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("root_decision_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("parent_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("lineage_step", sa.Integer(), nullable=False),
        sa.Column("emitting_subsystem", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("source_domain", sa.String(length=32), nullable=False),
        sa.Column("authorization_class", sa.String(length=64), nullable=False),
        sa.Column("execution_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("execution_class", sa.String(length=64), nullable=True),
        sa.Column("handoff_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_trace_id",
        "runtime_promotion_approval_decisions",
        ["trace_id"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_root_artifact_id",
        "runtime_promotion_approval_decisions",
        ["root_decision_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_parent_artifact_id",
        "runtime_promotion_approval_decisions",
        ["parent_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_emitting_subsystem",
        "runtime_promotion_approval_decisions",
        ["emitting_subsystem"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_candidate_id",
        "runtime_promotion_approval_decisions",
        ["candidate_id"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_recommendation_id",
        "runtime_promotion_approval_decisions",
        ["recommendation_id"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_approved_at",
        "runtime_promotion_approval_decisions",
        ["approved_at"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_handoff_status",
        "runtime_promotion_approval_decisions",
        ["handoff_status"],
    )
    op.create_index(
        "ix_runtime_promotion_approval_decisions_candidate_approved",
        "runtime_promotion_approval_decisions",
        ["candidate_id", "approved_at"],
    )

    op.create_table(
        "runtime_promotion_execution_requests",
        sa.Column("execution_request_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("root_decision_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("parent_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("lineage_step", sa.Integer(), nullable=False),
        sa.Column("emitting_subsystem", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("decision_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("request_class", sa.String(length=64), nullable=False),
        sa.Column("target_subsystem", sa.String(length=64), nullable=False),
        sa.Column("target_lane", sa.String(length=64), nullable=False),
        sa.Column("target_scope", sa.String(length=256), nullable=False),
        sa.Column("requested_action", sa.String(length=256), nullable=False),
        sa.Column("bounded_parameters_json", sa.JSON(), nullable=False),
        sa.Column("risk_class", sa.String(length=32), nullable=False),
        sa.Column("rollback_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_artifact_id"],
            ["runtime_promotion_approval_decisions.decision_artifact_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_runtime_promotion_execution_requests_idempotency_key",
        ),
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_trace_id",
        "runtime_promotion_execution_requests",
        ["trace_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_root_artifact_id",
        "runtime_promotion_execution_requests",
        ["root_decision_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_parent_artifact_id",
        "runtime_promotion_execution_requests",
        ["parent_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_emitting_subsystem",
        "runtime_promotion_execution_requests",
        ["emitting_subsystem"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_candidate_id",
        "runtime_promotion_execution_requests",
        ["candidate_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_decision_artifact_id",
        "runtime_promotion_execution_requests",
        ["decision_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_idempotency_key",
        "runtime_promotion_execution_requests",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_requested_at",
        "runtime_promotion_execution_requests",
        ["requested_at"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_request_status",
        "runtime_promotion_execution_requests",
        ["request_status"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_candidate_status",
        "runtime_promotion_execution_requests",
        ["candidate_id", "request_status"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_requests_lane_status",
        "runtime_promotion_execution_requests",
        ["target_lane", "request_status"],
    )

    op.create_table(
        "runtime_promotion_execution_statuses",
        sa.Column("execution_status_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("root_decision_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("parent_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("lineage_step", sa.Integer(), nullable=False),
        sa.Column("emitting_subsystem", sa.String(length=64), nullable=False),
        sa.Column("execution_request_id", sa.String(length=64), nullable=False),
        sa.Column("execution_state", sa.String(length=64), nullable=False),
        sa.Column("status_summary", sa.Text(), nullable=True),
        sa.Column("failure_reason_class", sa.String(length=64), nullable=False),
        sa.Column("operator_visible_notes", sa.Text(), nullable=True),
        sa.Column("artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timed_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_request_id"],
            ["runtime_promotion_execution_requests.execution_request_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_trace_id",
        "runtime_promotion_execution_statuses",
        ["trace_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_root_artifact_id",
        "runtime_promotion_execution_statuses",
        ["root_decision_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_parent_artifact_id",
        "runtime_promotion_execution_statuses",
        ["parent_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_emitting_subsystem",
        "runtime_promotion_execution_statuses",
        ["emitting_subsystem"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_execution_request_id",
        "runtime_promotion_execution_statuses",
        ["execution_request_id"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_execution_state",
        "runtime_promotion_execution_statuses",
        ["execution_state"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_failure_reason_class",
        "runtime_promotion_execution_statuses",
        ["failure_reason_class"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_recorded_at",
        "runtime_promotion_execution_statuses",
        ["recorded_at"],
    )
    op.create_index(
        "ix_runtime_promotion_execution_statuses_request_recorded",
        "runtime_promotion_execution_statuses",
        ["execution_request_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_request_recorded",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_recorded_at",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_failure_reason_class",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_execution_state",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_execution_request_id",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_emitting_subsystem",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_parent_artifact_id",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_root_artifact_id",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_statuses_trace_id",
        table_name="runtime_promotion_execution_statuses",
    )
    op.drop_table("runtime_promotion_execution_statuses")

    op.drop_index(
        "ix_runtime_promotion_execution_requests_lane_status",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_candidate_status",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_request_status",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_requested_at",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_idempotency_key",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_decision_artifact_id",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_candidate_id",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_emitting_subsystem",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_parent_artifact_id",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_root_artifact_id",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_index(
        "ix_runtime_promotion_execution_requests_trace_id",
        table_name="runtime_promotion_execution_requests",
    )
    op.drop_table("runtime_promotion_execution_requests")

    op.drop_index(
        "ix_runtime_promotion_approval_decisions_candidate_approved",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_handoff_status",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_approved_at",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_recommendation_id",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_candidate_id",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_emitting_subsystem",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_parent_artifact_id",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_root_artifact_id",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_index(
        "ix_runtime_promotion_approval_decisions_trace_id",
        table_name="runtime_promotion_approval_decisions",
    )
    op.drop_table("runtime_promotion_approval_decisions")
"""runtime promotion verification closeout table

Revision ID: 20260401_02
Revises: 20260401_01
Create Date: 2026-04-01 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_02"
down_revision = "20260401_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_promotion_verification_results",
        sa.Column("verification_artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("root_decision_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("parent_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("lineage_step", sa.Integer(), nullable=False),
        sa.Column("emitting_subsystem", sa.String(length=64), nullable=False),
        sa.Column("execution_request_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("verification_scope", sa.String(length=256), nullable=False),
        sa.Column("expected_gain", sa.Text(), nullable=False),
        sa.Column("observed_outcome", sa.String(length=64), nullable=False),
        sa.Column(
            "regression_detected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "rollback_recommended",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("verification_summary", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_request_id"],
            ["runtime_promotion_execution_requests.execution_request_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_trace_id",
        "runtime_promotion_verification_results",
        ["trace_id"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_root_artifact_id",
        "runtime_promotion_verification_results",
        ["root_decision_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_parent_artifact_id",
        "runtime_promotion_verification_results",
        ["parent_artifact_id"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_emitting_subsystem",
        "runtime_promotion_verification_results",
        ["emitting_subsystem"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_execution_request_id",
        "runtime_promotion_verification_results",
        ["execution_request_id"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_candidate_id",
        "runtime_promotion_verification_results",
        ["candidate_id"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_observed_outcome",
        "runtime_promotion_verification_results",
        ["observed_outcome"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_verified_at",
        "runtime_promotion_verification_results",
        ["verified_at"],
    )
    op.create_index(
        "ix_runtime_promotion_verification_results_request_verified",
        "runtime_promotion_verification_results",
        ["execution_request_id", "verified_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_promotion_verification_results_request_verified",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_verified_at",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_observed_outcome",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_candidate_id",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_execution_request_id",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_emitting_subsystem",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_parent_artifact_id",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_root_artifact_id",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_index(
        "ix_runtime_promotion_verification_results_trace_id",
        table_name="runtime_promotion_verification_results",
    )
    op.drop_table("runtime_promotion_verification_results")

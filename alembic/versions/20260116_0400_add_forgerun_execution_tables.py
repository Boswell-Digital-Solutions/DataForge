"""Add ForgeRun execution tables for Phase 2A

Creates:
- execution_index: Fast queryable index for run history
- run_evidence: JSONB storage for full RunEvidence.v1 documents

Revision ID: 20260116_0400
Revises: ea9a1ba37c87
Create Date: 2026-01-16 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260116_0400'
down_revision: Union[str, Sequence[str], None] = 'ea9a1ba37c87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ForgeRun execution tables."""

    # ==========================================================================
    # execution_index - Fast queryable index for /history and filtering
    # ==========================================================================
    # Design principles:
    # - Denormalized for fast reads (no JOINs needed for list view)
    # - Conditional columns (fail_reason, abort_kind, abort_reason) can be NULL
    # - Uses CHECK constraints to enforce conditional field rules
    # - JSONB for extensible metadata without schema changes

    op.create_table(
        'execution_index',
        # Primary identifiers
        sa.Column('run_id', sa.String(length=64), nullable=False, comment='Unique run identifier (e.g., run_abc123)'),
        sa.Column('trace_id', sa.String(length=64), nullable=False, comment='Distributed trace ID'),
        sa.Column('workflow_id', sa.String(length=64), nullable=False, comment='Workflow definition ID'),
        sa.Column('session_id', sa.String(length=64), nullable=False, comment='User session ID'),

        # Repository context
        sa.Column('repo_id', sa.String(length=255), nullable=False, comment='Repository identifier'),
        sa.Column('repo_sha', sa.String(length=64), nullable=False, comment='Git commit SHA'),
        sa.Column('branch', sa.String(length=255), nullable=False, comment='Git branch name'),

        # Execution mode
        sa.Column('mode', sa.String(length=20), nullable=False, comment='Run mode: interactive, batch, ci'),
        sa.Column('invoker', sa.String(length=20), nullable=True, comment='Invoker: cli, ui, api'),

        # Normalized terminal status (matches RunEvidence.v1)
        sa.Column('final_status', sa.String(length=20), nullable=False,
                  comment='Terminal status: pass, fail, aborted, system_fault'),

        # Conditional metadata - only populated when relevant
        sa.Column('fail_reason', sa.String(length=30), nullable=True,
                  comment='Semantic failure reason (only when final_status=fail)'),
        sa.Column('abort_kind', sa.String(length=10), nullable=True,
                  comment='Abort type: graceful, hard (only when final_status=aborted)'),
        sa.Column('abort_reason', sa.String(length=30), nullable=True,
                  comment='Why aborted (only when final_status=aborted)'),

        # Quality metrics
        sa.Column('promotion_ready', sa.Boolean(), nullable=False, default=False,
                  comment='Whether run output is ready for promotion'),
        sa.Column('confidence_floor', sa.Float(), nullable=False, default=0.0,
                  comment='Minimum confidence score across nodes (0.0-1.0)'),

        # Evidence references
        sa.Column('evidence_hash', sa.String(length=71), nullable=True,
                  comment='SHA256 hash of RunEvidence.v1 (sha256:...)'),
        sa.Column('artifact_bundle_pointer', sa.String(length=1024), nullable=True,
                  comment='Path or S3 URI to evidence bundle'),

        # Timing
        sa.Column('total_duration_ms', sa.Integer(), nullable=True,
                  comment='Total execution time in milliseconds'),
        sa.Column('node_count', sa.Integer(), nullable=True,
                  comment='Number of nodes executed'),
        sa.Column('attempt_count', sa.Integer(), nullable=True, default=1,
                  comment='Number of attempts (retries + 1)'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False, comment='When run started'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When run completed (NULL if in progress)'),

        # Extensible metadata (for future fields without migrations)
        sa.Column('metadata', postgresql.JSONB(), nullable=True,
                  comment='Additional metadata (risk_flags, notes, etc.)'),

        # Primary key
        sa.PrimaryKeyConstraint('run_id'),

        # Check constraints for conditional fields
        sa.CheckConstraint(
            "(final_status != 'fail') OR (fail_reason IS NOT NULL)",
            name='ck_execution_index_fail_reason_required'
        ),
        sa.CheckConstraint(
            "(final_status != 'aborted') OR (abort_kind IS NOT NULL AND abort_reason IS NOT NULL)",
            name='ck_execution_index_abort_metadata_required'
        ),
        sa.CheckConstraint(
            "(final_status IN ('fail', 'aborted')) OR (fail_reason IS NULL AND abort_kind IS NULL AND abort_reason IS NULL)",
            name='ck_execution_index_no_spurious_metadata'
        ),
        sa.CheckConstraint(
            "final_status IN ('pass', 'fail', 'aborted', 'system_fault')",
            name='ck_execution_index_valid_final_status'
        ),
        sa.CheckConstraint(
            "fail_reason IS NULL OR fail_reason IN ('quality_reject', 'constraint_violation', 'policy_violation', 'max_retries_exceeded', 'node_failure', 'validation_error', 'timeout', 'dependency_failure')",
            name='ck_execution_index_valid_fail_reason'
        ),
        sa.CheckConstraint(
            "abort_kind IS NULL OR abort_kind IN ('graceful', 'hard')",
            name='ck_execution_index_valid_abort_kind'
        ),
        sa.CheckConstraint(
            "abort_reason IS NULL OR abort_reason IN ('operator_cancel', 'safety_timeout', 'max_steps', 'policy_violation', 'resource_limit', 'external_signal')",
            name='ck_execution_index_valid_abort_reason'
        ),
    )

    # Indexes for common query patterns
    # Primary lookup
    op.create_index('ix_execution_index_run_id', 'execution_index', ['run_id'])
    op.create_index('ix_execution_index_trace_id', 'execution_index', ['trace_id'])

    # Filtering by workflow/session
    op.create_index('ix_execution_index_workflow_id', 'execution_index', ['workflow_id'])
    op.create_index('ix_execution_index_session_id', 'execution_index', ['session_id'])

    # Status-based queries (most common)
    op.create_index('ix_execution_index_final_status', 'execution_index', ['final_status'])
    op.create_index('ix_execution_index_fail_reason', 'execution_index', ['fail_reason'],
                    postgresql_where=sa.text("fail_reason IS NOT NULL"))

    # Time-based queries
    op.create_index('ix_execution_index_created_at', 'execution_index', ['created_at'])
    op.create_index('ix_execution_index_completed_at', 'execution_index', ['completed_at'],
                    postgresql_where=sa.text("completed_at IS NOT NULL"))

    # Composite indexes for common filter combinations
    op.create_index('idx_execution_workflow_status', 'execution_index', ['workflow_id', 'final_status'])
    op.create_index('idx_execution_workflow_created', 'execution_index', ['workflow_id', 'created_at'])
    op.create_index('idx_execution_status_created', 'execution_index', ['final_status', 'created_at'])
    op.create_index('idx_execution_repo_branch', 'execution_index', ['repo_id', 'branch'])

    # Quality metrics
    op.create_index('idx_execution_promotion_ready', 'execution_index', ['promotion_ready', 'created_at'],
                    postgresql_where=sa.text("promotion_ready = true"))

    # ==========================================================================
    # run_evidence - Full RunEvidence.v1 JSONB storage
    # ==========================================================================
    # Design principles:
    # - Store complete RunEvidence.v1 as JSONB for auditability
    # - execution_index has denormalized fields for fast queries
    # - This table is the source of truth, execution_index is the index

    op.create_table(
        'run_evidence',
        sa.Column('run_id', sa.String(length=64), nullable=False,
                  comment='Unique run identifier (matches execution_index.run_id)'),
        sa.Column('evidence_version', sa.String(length=20), nullable=False, default='RunEvidence.v1',
                  comment='Schema version'),
        sa.Column('evidence_hash', sa.String(length=71), nullable=False,
                  comment='SHA256 hash for integrity verification'),
        sa.Column('evidence', postgresql.JSONB(), nullable=False,
                  comment='Complete RunEvidence.v1 document'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),

        # Primary key and foreign key
        sa.PrimaryKeyConstraint('run_id'),
        sa.ForeignKeyConstraint(['run_id'], ['execution_index.run_id'], ondelete='CASCADE'),

        # Ensure hash matches schema pattern
        sa.CheckConstraint(
            "evidence_hash ~ '^sha256:[0-9a-f]{64}$'",
            name='ck_run_evidence_valid_hash'
        ),
    )

    # Indexes
    op.create_index('ix_run_evidence_run_id', 'run_evidence', ['run_id'])
    op.create_index('ix_run_evidence_evidence_hash', 'run_evidence', ['evidence_hash'])
    op.create_index('ix_run_evidence_created_at', 'run_evidence', ['created_at'])

    # GIN index for JSONB queries (e.g., searching by node_id in executions)
    op.create_index('idx_run_evidence_jsonb', 'run_evidence', ['evidence'],
                    postgresql_using='gin')


def downgrade() -> None:
    """Remove ForgeRun execution tables."""

    # Drop run_evidence table and indexes
    op.drop_index('idx_run_evidence_jsonb', table_name='run_evidence')
    op.drop_index('ix_run_evidence_created_at', table_name='run_evidence')
    op.drop_index('ix_run_evidence_evidence_hash', table_name='run_evidence')
    op.drop_index('ix_run_evidence_run_id', table_name='run_evidence')
    op.drop_table('run_evidence')

    # Drop execution_index table and indexes
    op.drop_index('idx_execution_promotion_ready', table_name='execution_index')
    op.drop_index('idx_execution_repo_branch', table_name='execution_index')
    op.drop_index('idx_execution_status_created', table_name='execution_index')
    op.drop_index('idx_execution_workflow_created', table_name='execution_index')
    op.drop_index('idx_execution_workflow_status', table_name='execution_index')
    op.drop_index('ix_execution_index_completed_at', table_name='execution_index')
    op.drop_index('ix_execution_index_created_at', table_name='execution_index')
    op.drop_index('ix_execution_index_fail_reason', table_name='execution_index')
    op.drop_index('ix_execution_index_final_status', table_name='execution_index')
    op.drop_index('ix_execution_index_session_id', table_name='execution_index')
    op.drop_index('ix_execution_index_workflow_id', table_name='execution_index')
    op.drop_index('ix_execution_index_trace_id', table_name='execution_index')
    op.drop_index('ix_execution_index_run_id', table_name='execution_index')
    op.drop_table('execution_index')

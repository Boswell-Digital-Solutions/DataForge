"""Create agentic reasoning tables (execution_experiences, skill_nominations, governed_broadcasts)

Revision ID: agentic_reasoning_001
Revises: edge_cites_001
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'agentic_reasoning_001'
down_revision: Union[str, Sequence[str], None] = 'edge_cites_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension already enabled in initial migration (9fe94997bec5)

    # ── Table 1: execution_experiences ──
    op.create_table(
        'execution_experiences',
        sa.Column('experience_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('forge_runs.run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', UUID(as_uuid=True), nullable=False),
        sa.Column('agent_archetype', sa.String(50), nullable=False),
        sa.Column('task_embedding', Vector(768), nullable=False),
        sa.Column('target_scope', JSON, nullable=False),
        sa.Column('execution_summary', sa.Text, nullable=False),
        sa.Column('outcome', sa.String(20), sa.CheckConstraint("outcome IN ('success', 'partial', 'failure')"), nullable=False),
        sa.Column('gate_results_snapshot', JSON, nullable=True),
        sa.Column('tool_sequence', JSON, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    # IVFFlat index on task_embedding for approximate nearest neighbor search
    op.execute("""
        CREATE INDEX ix_execution_experiences_embedding
        ON execution_experiences
        USING ivfflat (task_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    op.create_index('ix_execution_experiences_archetype_outcome', 'execution_experiences', ['agent_archetype', 'outcome'])
    op.create_index('ix_execution_experiences_run_id', 'execution_experiences', ['run_id'])
    op.create_index('ix_execution_experiences_created_at', 'execution_experiences', ['created_at'])
    op.execute("CREATE INDEX ix_execution_experiences_target_scope ON execution_experiences USING GIN (target_scope)")
    op.execute("CREATE INDEX ix_execution_experiences_gate_results ON execution_experiences USING GIN (gate_results_snapshot)")

    # ── Table 2: skill_nominations ──
    op.create_table(
        'skill_nominations',
        sa.Column('nomination_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('candidate_name', sa.String(200), nullable=False),
        sa.Column('tool_sequence', JSON, nullable=False),
        sa.Column('parameter_schemas', JSON, nullable=True),
        sa.Column('evidence_run_ids', sa.ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column('proposed_capability_category', sa.String(1), sa.CheckConstraint("proposed_capability_category IN ('A','B','C','D','E','F','G')"), nullable=True),
        sa.Column('proposed_capability_id', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), sa.CheckConstraint("status IN ('candidate', 'nominated', 'reviewing', 'approved', 'registered', 'rejected')"), nullable=False, server_default='candidate'),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    op.create_index('ix_skill_nominations_status', 'skill_nominations', ['status'])
    op.create_index('ix_skill_nominations_created_at', 'skill_nominations', ['created_at'])

    # ── Table 3: governed_broadcasts ──
    op.create_table(
        'governed_broadcasts',
        sa.Column('broadcast_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_agent_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_run_id', UUID(as_uuid=True), sa.ForeignKey('forge_runs.run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_scope', JSON, nullable=False),
        sa.Column('knowledge_type', sa.String(30), sa.CheckConstraint("knowledge_type IN ('context_discovery', 'error_signal', 'dependency_finding', 'scope_overlap')"), nullable=False),
        sa.Column('payload', JSON, nullable=False),
        sa.Column('provenance', JSON, nullable=True),
        sa.Column('trust_metadata', JSON, nullable=True),
        sa.Column('delivered_to', sa.ARRAY(UUID(as_uuid=True)), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    op.create_index('ix_governed_broadcasts_source_run_id', 'governed_broadcasts', ['source_run_id'])
    op.create_index('ix_governed_broadcasts_knowledge_type', 'governed_broadcasts', ['knowledge_type'])
    op.create_index('ix_governed_broadcasts_created_at', 'governed_broadcasts', ['created_at'])
    op.execute("CREATE INDEX ix_governed_broadcasts_target_scope ON governed_broadcasts USING GIN (target_scope)")
    op.execute("CREATE INDEX ix_governed_broadcasts_payload ON governed_broadcasts USING GIN (payload)")


def downgrade() -> None:
    op.drop_table('governed_broadcasts')
    op.drop_table('skill_nominations')
    op.drop_table('execution_experiences')

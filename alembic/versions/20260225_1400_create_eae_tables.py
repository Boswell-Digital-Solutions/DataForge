"""Create EAE tables (pf_evidence_items, pf_retrieval_runs) and
ALTER pf_ai_audit_log with evidence bundle columns.

Revision ID: eae_001
Revises: pressforge_001
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'eae_001'
down_revision: Union[str, Sequence[str], None] = 'pressforge_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table 1: pf_evidence_items ──
    op.create_table(
        'pf_evidence_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        # Classification
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source', sa.String(500), nullable=True),
        sa.Column('url', sa.String(2000), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),

        # Content
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(71), nullable=False),
        sa.Column('excerpt', sa.Text, nullable=True),

        # Trust & classification
        sa.Column('trust_tier', sa.Integer, nullable=False, server_default='1'),
        sa.Column('entity_tags', JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('metadata', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        # Search
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('search_vector', TSVECTOR, nullable=True),

        # Provenance
        sa.Column('source_chunk_id', sa.Integer, nullable=True),
        sa.Column('ingested_by', sa.String(50), nullable=True),

        # Lifecycle
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('stale_at', sa.DateTime(timezone=True), nullable=True),

        # Constraints
        sa.CheckConstraint('trust_tier BETWEEN 1 AND 5', name='ck_pf_evidence_trust_tier'),
    )

     # FK to chunks if applicable
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chunks') THEN
                ALTER TABLE pf_evidence_items
                    ADD CONSTRAINT fk_pf_evidence_source_chunk
                    FOREIGN KEY (source_chunk_id)
                    REFERENCES chunks(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # Indexes
    op.create_index('idx_pf_evidence_kind', 'pf_evidence_items', ['kind'])
    op.create_index('idx_pf_evidence_trust', 'pf_evidence_items', ['trust_tier'])
    op.create_index('idx_pf_evidence_published', 'pf_evidence_items', ['published_at'], postgresql_ops={'published_at': 'DESC'})
    op.execute("""
        CREATE INDEX idx_pf_evidence_active
        ON pf_evidence_items (is_active)
        WHERE is_active = true
    """)
    op.execute("""
        CREATE INDEX idx_pf_evidence_entity_tags
        ON pf_evidence_items USING GIN (entity_tags)
    """)
    op.execute("""
        CREATE INDEX idx_pf_evidence_embedding
        ON pf_evidence_items USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX idx_pf_evidence_tsvector
        ON pf_evidence_items USING GIN (search_vector)
    """)
    op.execute("""
        CREATE INDEX idx_pf_evidence_stale
        ON pf_evidence_items (stale_at)
        WHERE stale_at IS NOT NULL
    """)

    # Auto-maintain tsvector
    op.execute("""
        CREATE TRIGGER pf_evidence_tsvector_update
            BEFORE INSERT OR UPDATE ON pf_evidence_items
            FOR EACH ROW EXECUTE FUNCTION
            tsvector_update_trigger(search_vector, 'pg_catalog.english', title, content)
    """)

    # ── Table 2: pf_retrieval_runs ──
    op.create_table(
        'pf_retrieval_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        # What was asked
        sa.Column('task', sa.String(50), nullable=False),
        sa.Column('campaign_id', UUID(as_uuid=True), nullable=True),
        sa.Column('query_spec', JSONB, nullable=False),
        sa.Column('query_hash', sa.String(71), nullable=False),

        # What was searched
        sa.Column('filters_applied', JSONB, nullable=False),
        sa.Column('sub_query_count', sa.Integer, nullable=False, server_default='1'),

        # What was found
        sa.Column('candidate_count', sa.Integer, nullable=False),
        sa.Column('candidate_ids', JSONB, nullable=False),
        sa.Column('topk_ids', JSONB, nullable=False),
        sa.Column('topk_hashes', JSONB, nullable=False),
        sa.Column('rerank_scores', JSONB, nullable=False),

        # Bundle output
        sa.Column('bundle_id', UUID(as_uuid=True), nullable=False),
        sa.Column('bundle_hash', sa.String(71), nullable=False),
        sa.Column('item_count', sa.Integer, nullable=False),
        sa.Column('total_tokens', sa.Integer, nullable=False),

        # Performance
        sa.Column('cache_hit', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('latency_ms', sa.Integer, nullable=False),

        # Coverage quality
        sa.Column('coverage_score', sa.Float, nullable=False),
        sa.Column('missing_kinds', JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column('warnings', JSONB, server_default=sa.text("'[]'::jsonb")),
    )

    # FK to campaigns if applicable
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pf_campaigns') THEN
                ALTER TABLE pf_retrieval_runs
                    ADD CONSTRAINT fk_pf_retrieval_campaign
                    FOREIGN KEY (campaign_id)
                    REFERENCES pf_campaigns(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    op.create_index('idx_pf_retrieval_runs_task', 'pf_retrieval_runs', ['task'])
    op.create_index('idx_pf_retrieval_runs_campaign', 'pf_retrieval_runs', ['campaign_id'])
    op.create_index('idx_pf_retrieval_runs_created', 'pf_retrieval_runs', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_pf_retrieval_runs_query_hash', 'pf_retrieval_runs', ['query_hash'])
    op.create_index('idx_pf_retrieval_runs_bundle', 'pf_retrieval_runs', ['bundle_id'])

    # ── ALTER pf_ai_audit_log: Add EAE columns ──
    op.add_column('pf_ai_audit_log', sa.Column('evidence_bundle_id', UUID(as_uuid=True), nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('bundle_hash', sa.String(71), nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('model_route', sa.String(100), nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('output_payload', JSONB, nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('cited_evidence_ids', JSONB, nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('uncited_evidence_ids', JSONB, nullable=True))
    op.add_column('pf_ai_audit_log', sa.Column('missing_evidence_warnings', JSONB, nullable=True))

    op.create_index('idx_pf_ai_audit_bundle', 'pf_ai_audit_log', ['evidence_bundle_id'])
    op.create_index('idx_pf_ai_audit_bundle_hash', 'pf_ai_audit_log', ['bundle_hash'])


def downgrade() -> None:
    # Drop new indexes on pf_ai_audit_log
    op.drop_index('idx_pf_ai_audit_bundle_hash', table_name='pf_ai_audit_log')
    op.drop_index('idx_pf_ai_audit_bundle', table_name='pf_ai_audit_log')

    # Drop new columns from pf_ai_audit_log
    op.drop_column('pf_ai_audit_log', 'missing_evidence_warnings')
    op.drop_column('pf_ai_audit_log', 'uncited_evidence_ids')
    op.drop_column('pf_ai_audit_log', 'cited_evidence_ids')
    op.drop_column('pf_ai_audit_log', 'output_payload')
    op.drop_column('pf_ai_audit_log', 'model_route')
    op.drop_column('pf_ai_audit_log', 'bundle_hash')
    op.drop_column('pf_ai_audit_log', 'evidence_bundle_id')

    # Drop pf_retrieval_runs
    op.drop_table('pf_retrieval_runs')

    # Drop trigger + table pf_evidence_items
    op.execute("DROP TRIGGER IF EXISTS pf_evidence_tsvector_update ON pf_evidence_items")
    op.drop_table('pf_evidence_items')

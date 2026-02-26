"""Add pf_match_results table and pf_pitches Phase 2 columns
(evidence_bundle_id, subject_variants).

Revision ID: pressforge_phase2_001
Revises: eae_001
Create Date: 2026-02-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'pressforge_phase2_001'
down_revision: Union[str, Sequence[str], None] = 'eae_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table: pf_match_results ──
    op.create_table(
        'pf_match_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('journalist_id', UUID(as_uuid=True), sa.ForeignKey('pf_journalists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_score', sa.Float, nullable=False, comment='0.0–1.0 composite match score'),
        sa.Column('beat_relevance', sa.Float, nullable=True),
        sa.Column('recency_score', sa.Float, nullable=True),
        sa.Column('audience_overlap', sa.Float, nullable=True),
        sa.Column('evidence_bundle_id', UUID(as_uuid=True), nullable=True, comment='EAE bundle used for match'),
        sa.Column('ai_rationale', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='suggested'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("status IN ('suggested', 'accepted', 'rejected')", name='ck_pf_match_status'),
    )
    op.create_index('ix_pf_match_results_campaign', 'pf_match_results', ['campaign_id'])
    op.create_index('ix_pf_match_results_journalist', 'pf_match_results', ['journalist_id'])
    op.create_index('ix_pf_match_results_score', 'pf_match_results', ['match_score'])

    # ── ALTER pf_pitches: add Phase 2 columns ──
    op.add_column('pf_pitches', sa.Column('evidence_bundle_id', UUID(as_uuid=True), nullable=True,
                                          comment='EAE bundle used for generation'))
    op.add_column('pf_pitches', sa.Column('subject_variants', JSONB, nullable=True,
                                          comment='AI-generated subject line variants'))


def downgrade() -> None:
    op.drop_column('pf_pitches', 'subject_variants')
    op.drop_column('pf_pitches', 'evidence_bundle_id')
    op.drop_index('ix_pf_match_results_score', table_name='pf_match_results')
    op.drop_index('ix_pf_match_results_journalist', table_name='pf_match_results')
    op.drop_index('ix_pf_match_results_campaign', table_name='pf_match_results')
    op.drop_table('pf_match_results')

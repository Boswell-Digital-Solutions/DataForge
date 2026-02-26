"""Add v1.2 columns to pf_campaigns and pf_evidence_items.

pf_campaigns: campaign_type, geo_share_pre, geo_share_post, cost_per_cycle
pf_evidence_items: ai_stance, disclosure_policy

Revision ID: pressforge_v12_002
Revises: pressforge_v12_001
Create Date: 2026-02-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'pressforge_v12_002'
down_revision: Union[str, Sequence[str], None] = 'pressforge_v12_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pf_campaigns: campaign type + GEO share tracking + cost tracking ──
    op.add_column('pf_campaigns', sa.Column(
        'campaign_type', sa.String(30), nullable=False, server_default='book_launch',
    ))
    op.add_column('pf_campaigns', sa.Column(
        'geo_share_pre', sa.Float, nullable=True, comment='Pre-campaign AI citation rate',
    ))
    op.add_column('pf_campaigns', sa.Column(
        'geo_share_post', sa.Float, nullable=True, comment='Post-campaign AI citation rate',
    ))
    op.add_column('pf_campaigns', sa.Column(
        'cost_per_cycle', sa.Float, nullable=True, comment='Computed from automation run token costs',
    ))
    op.create_check_constraint(
        'ck_pf_campaign_type',
        'pf_campaigns',
        "campaign_type IN ('book_launch', 'series_continuation', 'author_platform', 'backlist_revival')",
    )

    # ── pf_evidence_items: AI stance tracking + disclosure policy ──
    op.add_column('pf_evidence_items', sa.Column(
        'ai_stance', sa.String(20), nullable=True,
        comment='For journalist kinds: receptive/neutral/cautious/hostile/unknown',
    ))
    op.add_column('pf_evidence_items', sa.Column(
        'disclosure_policy', sa.Text, nullable=True,
        comment='Outlet-level AI content policy text',
    ))
    op.create_check_constraint(
        'ck_pf_evidence_ai_stance',
        'pf_evidence_items',
        "ai_stance IS NULL OR ai_stance IN ('receptive', 'neutral', 'cautious', 'hostile', 'unknown')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_pf_evidence_ai_stance', 'pf_evidence_items')
    op.drop_column('pf_evidence_items', 'disclosure_policy')
    op.drop_column('pf_evidence_items', 'ai_stance')
    op.drop_constraint('ck_pf_campaign_type', 'pf_campaigns')
    op.drop_column('pf_campaigns', 'cost_per_cycle')
    op.drop_column('pf_campaigns', 'geo_share_post')
    op.drop_column('pf_campaigns', 'geo_share_pre')
    op.drop_column('pf_campaigns', 'campaign_type')

"""Create PressForge tables (pf_journalists, pf_campaigns, pf_pitches,
pf_outreach_events, pf_coverage, pf_domain_reputation, pf_ai_audit_log)

Revision ID: pressforge_001
Revises: compression_dict_001
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'pressforge_001'
down_revision: Union[str, Sequence[str], None] = 'compression_dict_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table 1: pf_journalists ──
    op.create_table(
        'pf_journalists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.Text, nullable=True, comment='Encrypted at app layer in later phases'),
        sa.Column('beat', sa.String(100), nullable=True),
        sa.Column('publication', sa.String(200), nullable=True),
        sa.Column('bio', sa.Text, nullable=True),
        sa.Column('social_links', JSONB, nullable=False, server_default='{}'),
        sa.Column('coverage_embedding', Vector(1536), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('consent_status', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive', 'do_not_contact')", name='ck_pf_journalist_status'),
        sa.CheckConstraint("consent_status IN ('unknown', 'legitimate_interest', 'opted_in', 'opted_out')", name='ck_pf_journalist_consent'),
    )
    op.create_index('ix_pf_journalists_beat', 'pf_journalists', ['beat'])
    op.create_index('ix_pf_journalists_publication', 'pf_journalists', ['publication'])
    op.create_index('ix_pf_journalists_status', 'pf_journalists', ['status'])
    op.execute("""
        CREATE INDEX ix_pf_journalists_embedding
        ON pf_journalists
        USING ivfflat (coverage_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # ── Table 2: pf_campaigns ──
    op.create_table(
        'pf_campaigns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False, comment='FK concept to AuthorForge project'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('news_angle', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='DISCOVER'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('DISCOVER', 'MATCH', 'GENERATE', 'LABEL', 'REVIEW', 'EXECUTE', 'MONITOR', 'COMPLETE')",
            name='ck_pf_campaign_status',
        ),
    )
    op.create_index('ix_pf_campaigns_project_id', 'pf_campaigns', ['project_id'])
    op.create_index('ix_pf_campaigns_status', 'pf_campaigns', ['status'])

    # ── Table 3: pf_pitches ──
    op.create_table(
        'pf_pitches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('journalist_id', UUID(as_uuid=True), sa.ForeignKey('pf_journalists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('ai_generated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('ai_rationale', sa.Text, nullable=True),
        sa.Column('humanity_score', sa.Float, nullable=True, comment='0.0=pure AI, 1.0=fully human-edited'),
        sa.Column('human_verification_checksum', sa.String(128), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'reviewed', 'approved', 'sent', 'rejected')", name='ck_pf_pitch_status'),
    )
    op.create_index('ix_pf_pitches_campaign_id', 'pf_pitches', ['campaign_id'])
    op.create_index('ix_pf_pitches_journalist_id', 'pf_pitches', ['journalist_id'])

    # ── Table 4: pf_outreach_events ──
    op.create_table(
        'pf_outreach_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('pitch_id', UUID(as_uuid=True), sa.ForeignKey('pf_pitches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(20), nullable=False),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("event_type IN ('send', 'reply', 'bounce', 'open')", name='ck_pf_outreach_event_type'),
    )
    op.create_index('ix_pf_outreach_events_pitch_id', 'pf_outreach_events', ['pitch_id'])
    op.create_index('ix_pf_outreach_events_type', 'pf_outreach_events', ['event_type'])

    # ── Table 5: pf_coverage ──
    op.create_table(
        'pf_coverage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('journalist_id', UUID(as_uuid=True), sa.ForeignKey('pf_journalists.id', ondelete='SET NULL'), nullable=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('article_url', sa.Text, nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('ai_sentiment_score', sa.Float, nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_pf_coverage_journalist_id', 'pf_coverage', ['journalist_id'])
    op.create_index('ix_pf_coverage_campaign_id', 'pf_coverage', ['campaign_id'])

    # ── Table 6: pf_domain_reputation ──
    op.create_table(
        'pf_domain_reputation',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('domain', sa.String(255), nullable=False, unique=True),
        sa.Column('dmarc_status', sa.String(10), nullable=False, server_default='unknown'),
        sa.Column('spf_status', sa.String(10), nullable=False, server_default='unknown'),
        sa.Column('dkim_status', sa.String(10), nullable=False, server_default='unknown'),
        sa.Column('warmup_state', sa.String(10), nullable=False, server_default='cold'),
        sa.Column('bounce_rate', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("dmarc_status IN ('pass', 'fail', 'none', 'unknown')", name='ck_pf_domain_dmarc'),
        sa.CheckConstraint("spf_status IN ('pass', 'fail', 'none', 'unknown')", name='ck_pf_domain_spf'),
        sa.CheckConstraint("dkim_status IN ('pass', 'fail', 'none', 'unknown')", name='ck_pf_domain_dkim'),
        sa.CheckConstraint("warmup_state IN ('cold', 'warming', 'warm')", name='ck_pf_domain_warmup'),
    )

    # ── Table 7: pf_ai_audit_log (append-only) ──
    op.create_table(
        'pf_ai_audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_type', sa.String(50), nullable=False, comment='e.g. match, pitch_generation, subject_variants'),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('input_hash', sa.String(128), nullable=True),
        sa.Column('rationale', sa.Text, nullable=True),
        sa.Column('personalization_notes', sa.Text, nullable=True),
        sa.Column('campaign_id', UUID(as_uuid=True), nullable=True),
        sa.Column('journalist_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_pf_ai_audit_log_campaign_id', 'pf_ai_audit_log', ['campaign_id'])
    op.create_index('ix_pf_ai_audit_log_created_at', 'pf_ai_audit_log', ['created_at'])


def downgrade() -> None:
    op.drop_table('pf_ai_audit_log')
    op.drop_table('pf_domain_reputation')
    op.drop_table('pf_coverage')
    op.drop_table('pf_outreach_events')
    op.drop_table('pf_pitches')
    op.drop_table('pf_campaigns')
    op.drop_table('pf_journalists')

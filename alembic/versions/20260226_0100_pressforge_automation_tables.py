"""Add PressForge v1.2 automation, governance, GEO, draftset, promptpack, outcome tables.

11 new tables: pf_automation_jobs, pf_automation_runs, pf_automation_alerts,
pf_automation_overrides, pf_agent_logs, pf_provider_configs, pf_geo_probes,
pf_geo_probe_templates, pf_social_draftsets, pf_prompt_packs, pf_campaign_outcomes.

Revision ID: pressforge_v12_001
Revises: pressforge_phase2_001
Create Date: 2026-02-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'pressforge_v12_001'
down_revision: Union[str, Sequence[str], None] = 'pressforge_phase2_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table: pf_automation_jobs ──
    op.create_table(
        'pf_automation_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_key', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('cron_schedule', sa.String(100), nullable=False),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('tier', sa.Integer, nullable=False),
        sa.Column('cost_class', sa.String(20), nullable=False, server_default='low'),
        sa.Column('last_run_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('tier BETWEEN 1 AND 4', name='ck_pf_auto_job_tier'),
        sa.CheckConstraint("cost_class IN ('low', 'medium', 'high')", name='ck_pf_auto_job_cost_class'),
    )

    # ── Table: pf_automation_runs ──
    op.create_table(
        'pf_automation_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('pf_automation_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_key', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('ended_at', sa.DateTime, nullable=True),
        sa.Column('attempt', sa.Integer, nullable=False, server_default='1'),
        sa.Column('inputs_hash', sa.String(128), nullable=True),
        sa.Column('summary', JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('cost_tokens', sa.Integer, nullable=True),
        sa.Column('batch_id', sa.String(200), nullable=True),
        sa.Column('provider_used', sa.String(50), nullable=True),
        sa.Column('provider_latency_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'skipped')",
            name='ck_pf_auto_run_status',
        ),
    )
    op.create_index('ix_pf_auto_runs_job_id', 'pf_automation_runs', ['job_id'])
    op.create_index('ix_pf_auto_runs_job_key', 'pf_automation_runs', ['job_key'])
    op.create_index('ix_pf_auto_runs_status', 'pf_automation_runs', ['status'])

    # ── Table: pf_automation_alerts ──
    op.create_table(
        'pf_automation_alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('pf_automation_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_key', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('context', JSONB, nullable=False, server_default='{}'),
        sa.Column('dismissed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('dismissed_by', sa.String(100), nullable=True),
        sa.Column('dismissed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("severity IN ('info', 'warn', 'high')", name='ck_pf_auto_alert_severity'),
    )
    op.create_index('ix_pf_auto_alerts_job_key', 'pf_automation_alerts', ['job_key'])
    op.create_index('ix_pf_auto_alerts_severity', 'pf_automation_alerts', ['severity'])

    # ── Table: pf_automation_overrides ──
    op.create_table(
        'pf_automation_overrides',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_key', sa.String(100), nullable=False),
        sa.Column('override_config', JSONB, nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pf_auto_overrides_job_key', 'pf_automation_overrides', ['job_key'])

    # ── Table: pf_agent_logs (append-only) ──
    op.create_table(
        'pf_agent_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('pf_automation_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_key', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('input_state', JSONB, nullable=False, server_default='{}'),
        sa.Column('decision_rationale', sa.Text, nullable=False),
        sa.Column('output_action', JSONB, nullable=False, server_default='{}'),
        sa.Column('risk_flags', JSONB, nullable=False, server_default='{}'),
        sa.Column('accepted', sa.Boolean, nullable=True),
        sa.Column('accepted_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "action_type IN ('route_priority', 'suggest_config', 'widen_query', 'escalate_human', 'auto_pause', 'reactive_trigger', 'self_heal')",
            name='ck_pf_agent_log_action_type',
        ),
    )
    op.create_index('ix_pf_agent_logs_run_id', 'pf_agent_logs', ['run_id'])
    op.create_index('ix_pf_agent_logs_job_key', 'pf_agent_logs', ['job_key'])

    # ── Table: pf_provider_configs ──
    op.create_table(
        'pf_provider_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider_key', sa.String(50), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('api_base_url', sa.String(500), nullable=True),
        sa.Column('supports_batch', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('batch_endpoint', sa.String(500), nullable=True),
        sa.Column('cost_per_1m_input', sa.Float, nullable=True),
        sa.Column('cost_per_1m_output', sa.Float, nullable=True),
        sa.Column('max_context_window', sa.Integer, nullable=True),
        sa.Column('supports_structured_output', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('circuit_breaker_status', sa.String(20), nullable=False, server_default='closed'),
        sa.Column('last_health_check_at', sa.DateTime, nullable=True),
        sa.Column('rate_limit_rpm', sa.Integer, nullable=True),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "circuit_breaker_status IN ('closed', 'open', 'half_open')",
            name='ck_pf_provider_circuit_breaker',
        ),
    )

    # ── Table: pf_geo_probe_templates (must precede pf_geo_probes for FK) ──
    op.create_table(
        'pf_geo_probe_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('prompt_text', sa.Text, nullable=False),
        sa.Column('intent_category', sa.String(100), nullable=True),
        sa.Column('funnel_stage', sa.String(50), nullable=True),
        sa.Column('auto_generated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pf_geo_templates_campaign_id', 'pf_geo_probe_templates', ['campaign_id'])

    # ── Table: pf_geo_probes ──
    op.create_table(
        'pf_geo_probes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('template_id', UUID(as_uuid=True), sa.ForeignKey('pf_geo_probe_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('prompt_text', sa.Text, nullable=False),
        sa.Column('prompt_category', sa.String(100), nullable=True),
        sa.Column('response_excerpt', sa.Text, nullable=True),
        sa.Column('brand_mentioned', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('citation_found', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('competitor_mentions', JSONB, nullable=False, server_default='[]'),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('model_version', sa.String(100), nullable=True),
        sa.Column('probed_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name='ck_pf_geo_probe_sentiment',
        ),
    )
    op.create_index('ix_pf_geo_probes_campaign_id', 'pf_geo_probes', ['campaign_id'])
    op.create_index('ix_pf_geo_probes_provider', 'pf_geo_probes', ['provider'])
    op.create_index('ix_pf_geo_probes_probed_at', 'pf_geo_probes', ['probed_at'])

    # ── Table: pf_social_draftsets ──
    op.create_table(
        'pf_social_draftsets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bundle_hash', sa.String(71), nullable=True),
        sa.Column('intent', sa.String(50), nullable=True),
        sa.Column('platforms', JSONB, nullable=False, server_default='[]'),
        sa.Column('drafts', JSONB, nullable=False, server_default='[]'),
        sa.Column('schema_json_ld', JSONB, nullable=True),
        sa.Column('coverage_warnings', JSONB, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('draft', 'reviewed', 'approved')", name='ck_pf_draftset_status'),
    )
    op.create_index('ix_pf_draftsets_campaign_id', 'pf_social_draftsets', ['campaign_id'])

    # ── Table: pf_prompt_packs ──
    op.create_table(
        'pf_prompt_packs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pack_name', sa.String(200), nullable=True),
        sa.Column('sora_prompt', sa.Text, nullable=True),
        sa.Column('chatgpt_image_prompt', sa.Text, nullable=True),
        sa.Column('gemini_prompt', sa.Text, nullable=True),
        sa.Column('negative_constraints', sa.Text, nullable=True),
        sa.Column('aspect_ratios', JSONB, nullable=False, server_default='{}'),
        sa.Column('alt_text', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('draft', 'reviewed', 'approved')", name='ck_pf_promptpack_status'),
    )
    op.create_index('ix_pf_promptpacks_campaign_id', 'pf_prompt_packs', ['campaign_id'])

    # ── Table: pf_campaign_outcomes ──
    op.create_table(
        'pf_campaign_outcomes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('pf_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bundle_hash', sa.String(71), nullable=True),
        sa.Column('outcome_type', sa.String(50), nullable=False),
        sa.Column('outcome_weight', sa.Integer, nullable=False),
        sa.Column('journalist_id', UUID(as_uuid=True), sa.ForeignKey('pf_journalists.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('context', JSONB, nullable=False, server_default='{}'),
        sa.Column('discovered_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "outcome_type IN ('coverage_secured', 'followup_requested', 'reply_received', 'open_confirmed', 'bounce', 'anti_ai_flagged')",
            name='ck_pf_outcome_type',
        ),
    )
    op.create_index('ix_pf_outcomes_campaign_id', 'pf_campaign_outcomes', ['campaign_id'])
    op.create_index('ix_pf_outcomes_type', 'pf_campaign_outcomes', ['outcome_type'])


def downgrade() -> None:
    op.drop_table('pf_campaign_outcomes')
    op.drop_table('pf_prompt_packs')
    op.drop_table('pf_social_draftsets')
    op.drop_table('pf_geo_probes')
    op.drop_table('pf_geo_probe_templates')
    op.drop_table('pf_provider_configs')
    op.drop_table('pf_agent_logs')
    op.drop_table('pf_automation_overrides')
    op.drop_table('pf_automation_alerts')
    op.drop_table('pf_automation_runs')
    op.drop_table('pf_automation_jobs')

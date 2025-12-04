"""add_team_organization_tables

Revision ID: aada9fc461fe
Revises: 2c5cb5b2cd5a
Create Date: 2025-12-01 14:55:33.838728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'aada9fc461fe'
down_revision: Union[str, Sequence[str], None] = '2c5cb5b2cd5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add Team & Organization Learning tables (Phase 4.1)."""

    # Create enum types
    team_role_enum = postgresql.ENUM(
        'owner', 'admin', 'member', 'viewer',
        name='teamrole',
        create_type=False
    )
    team_role_enum.create(op.get_bind(), checkfirst=True)

    invite_status_enum = postgresql.ENUM(
        'pending', 'accepted', 'declined', 'expired',
        name='invitestatus',
        create_type=False
    )
    invite_status_enum.create(op.get_bind(), checkfirst=True)

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('organization_type', sa.String(length=50), nullable=True),
        sa.Column('team_size', sa.Integer(), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('member_count', sa.Integer(), nullable=True, default=0),
        sa.Column('project_count', sa.Integer(), nullable=True, default=0),
        sa.Column('total_sessions', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_teams_id', 'teams', ['id'])
    op.create_index('ix_teams_name', 'teams', ['name'])
    op.create_index('ix_teams_slug', 'teams', ['slug'])
    op.create_index('ix_teams_owner_id', 'teams', ['owner_id'])
    op.create_index('ix_teams_industry', 'teams', ['industry'])
    op.create_index('ix_teams_is_active', 'teams', ['is_active'])
    op.create_index('ix_teams_is_public', 'teams', ['is_public'])
    op.create_index('ix_teams_created_at', 'teams', ['created_at'])

    # Create team_members association table
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', team_role_enum, nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('invited_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_members_id', 'team_members', ['id'])
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])
    op.create_index('ix_team_members_role', 'team_members', ['role'])
    op.create_index('ix_team_members_joined_at', 'team_members', ['joined_at'])
    op.create_index('ix_team_members_is_active', 'team_members', ['is_active'])
    op.create_index('ix_team_members_team_user', 'team_members', ['team_id', 'user_id'], unique=True)

    # Create team_invites table
    op.create_table(
        'team_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('invited_email', sa.String(length=255), nullable=False),
        sa.Column('invited_user_id', sa.Integer(), nullable=True),
        sa.Column('invited_by', sa.Integer(), nullable=True),
        sa.Column('role', team_role_enum, nullable=False, server_default='member'),
        sa.Column('status', invite_status_enum, nullable=False, server_default='pending'),
        sa.Column('invite_token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_token')
    )
    op.create_index('ix_team_invites_id', 'team_invites', ['id'])
    op.create_index('ix_team_invites_team_id', 'team_invites', ['team_id'])
    op.create_index('ix_team_invites_invited_email', 'team_invites', ['invited_email'])
    op.create_index('ix_team_invites_invited_user_id', 'team_invites', ['invited_user_id'])
    op.create_index('ix_team_invites_invited_by', 'team_invites', ['invited_by'])
    op.create_index('ix_team_invites_status', 'team_invites', ['status'])
    op.create_index('ix_team_invites_invite_token', 'team_invites', ['invite_token'])
    op.create_index('ix_team_invites_expires_at', 'team_invites', ['expires_at'])
    op.create_index('ix_team_invites_created_at', 'team_invites', ['created_at'])

    # Create team_projects table
    op.create_table(
        'team_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('is_team_template', sa.Boolean(), nullable=True, default=False),
        sa.Column('visibility', sa.String(length=20), nullable=True, server_default='team'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['vibeforge_projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_projects_id', 'team_projects', ['id'])
    op.create_index('ix_team_projects_team_id', 'team_projects', ['team_id'])
    op.create_index('ix_team_projects_project_id', 'team_projects', ['project_id'])
    op.create_index('ix_team_projects_is_team_template', 'team_projects', ['is_team_template'])
    op.create_index('ix_team_projects_visibility', 'team_projects', ['visibility'])
    op.create_index('ix_team_projects_created_by', 'team_projects', ['created_by'])
    op.create_index('ix_team_projects_created_at', 'team_projects', ['created_at'])
    op.create_index('ix_team_projects_team_project', 'team_projects', ['team_id', 'project_id'], unique=True)

    # Create team_learning_aggregates table
    op.create_table(
        'team_learning_aggregates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('member_count_snapshot', sa.Integer(), nullable=False),
        sa.Column('top_languages', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('language_trends', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('top_stacks', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('stack_combinations', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('common_project_types', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('avg_project_complexity', sa.Float(), nullable=True),
        sa.Column('avg_team_size_preference', sa.Float(), nullable=True),
        sa.Column('overall_success_rate', sa.Float(), nullable=True),
        sa.Column('projects_completed', sa.Integer(), nullable=True, default=0),
        sa.Column('projects_abandoned', sa.Integer(), nullable=True, default=0),
        sa.Column('avg_satisfaction_score', sa.Float(), nullable=True),
        sa.Column('total_llm_queries', sa.Integer(), nullable=True, default=0),
        sa.Column('avg_tokens_per_session', sa.Float(), nullable=True),
        sa.Column('most_used_provider', sa.String(length=50), nullable=True),
        sa.Column('most_used_model', sa.String(length=100), nullable=True),
        sa.Column('avg_session_duration_minutes', sa.Float(), nullable=True),
        sa.Column('avg_steps_revisited', sa.Float(), nullable=True),
        sa.Column('recommendation_override_rate', sa.Float(), nullable=True),
        sa.Column('recommended_languages', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('recommended_stacks', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('improvement_suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_learning_aggregates_id', 'team_learning_aggregates', ['id'])
    op.create_index('ix_team_learning_aggregates_team_id', 'team_learning_aggregates', ['team_id'])
    op.create_index('ix_team_learning_aggregates_computed_at', 'team_learning_aggregates', ['computed_at'])
    op.create_index('ix_team_learning_aggregates_period_start', 'team_learning_aggregates', ['period_start'])
    op.create_index('ix_team_learning_aggregates_period_end', 'team_learning_aggregates', ['period_end'])
    op.create_index('ix_team_learning_team_period', 'team_learning_aggregates', ['team_id', 'period_start', 'period_end'])

    # Create team_insights table
    op.create_table(
        'team_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('actionable_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('data_sources', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('impact_estimate', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_acted_upon', sa.Boolean(), nullable=True, default=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('generated_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_insights_id', 'team_insights', ['id'])
    op.create_index('ix_team_insights_team_id', 'team_insights', ['team_id'])
    op.create_index('ix_team_insights_insight_type', 'team_insights', ['insight_type'])
    op.create_index('ix_team_insights_category', 'team_insights', ['category'])
    op.create_index('ix_team_insights_priority', 'team_insights', ['priority'])
    op.create_index('ix_team_insights_is_active', 'team_insights', ['is_active'])
    op.create_index('ix_team_insights_is_read', 'team_insights', ['is_read'])
    op.create_index('ix_team_insights_is_acted_upon', 'team_insights', ['is_acted_upon'])
    op.create_index('ix_team_insights_created_at', 'team_insights', ['created_at'])
    op.create_index('ix_team_insights_expires_at', 'team_insights', ['expires_at'])
    op.create_index('ix_team_insights_team_active', 'team_insights', ['team_id', 'is_active', 'created_at'])


def downgrade() -> None:
    """Downgrade schema - Remove Team & Organization Learning tables."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('ix_team_insights_team_active', table_name='team_insights')
    op.drop_index('ix_team_insights_expires_at', table_name='team_insights')
    op.drop_index('ix_team_insights_created_at', table_name='team_insights')
    op.drop_index('ix_team_insights_is_acted_upon', table_name='team_insights')
    op.drop_index('ix_team_insights_is_read', table_name='team_insights')
    op.drop_index('ix_team_insights_is_active', table_name='team_insights')
    op.drop_index('ix_team_insights_priority', table_name='team_insights')
    op.drop_index('ix_team_insights_category', table_name='team_insights')
    op.drop_index('ix_team_insights_insight_type', table_name='team_insights')
    op.drop_index('ix_team_insights_team_id', table_name='team_insights')
    op.drop_index('ix_team_insights_id', table_name='team_insights')
    op.drop_table('team_insights')

    op.drop_index('ix_team_learning_team_period', table_name='team_learning_aggregates')
    op.drop_index('ix_team_learning_aggregates_period_end', table_name='team_learning_aggregates')
    op.drop_index('ix_team_learning_aggregates_period_start', table_name='team_learning_aggregates')
    op.drop_index('ix_team_learning_aggregates_computed_at', table_name='team_learning_aggregates')
    op.drop_index('ix_team_learning_aggregates_team_id', table_name='team_learning_aggregates')
    op.drop_index('ix_team_learning_aggregates_id', table_name='team_learning_aggregates')
    op.drop_table('team_learning_aggregates')

    op.drop_index('ix_team_projects_team_project', table_name='team_projects')
    op.drop_index('ix_team_projects_created_at', table_name='team_projects')
    op.drop_index('ix_team_projects_created_by', table_name='team_projects')
    op.drop_index('ix_team_projects_visibility', table_name='team_projects')
    op.drop_index('ix_team_projects_is_team_template', table_name='team_projects')
    op.drop_index('ix_team_projects_project_id', table_name='team_projects')
    op.drop_index('ix_team_projects_team_id', table_name='team_projects')
    op.drop_index('ix_team_projects_id', table_name='team_projects')
    op.drop_table('team_projects')

    op.drop_index('ix_team_invites_created_at', table_name='team_invites')
    op.drop_index('ix_team_invites_expires_at', table_name='team_invites')
    op.drop_index('ix_team_invites_invite_token', table_name='team_invites')
    op.drop_index('ix_team_invites_status', table_name='team_invites')
    op.drop_index('ix_team_invites_invited_by', table_name='team_invites')
    op.drop_index('ix_team_invites_invited_user_id', table_name='team_invites')
    op.drop_index('ix_team_invites_invited_email', table_name='team_invites')
    op.drop_index('ix_team_invites_team_id', table_name='team_invites')
    op.drop_index('ix_team_invites_id', table_name='team_invites')
    op.drop_table('team_invites')

    op.drop_index('ix_team_members_team_user', table_name='team_members')
    op.drop_index('ix_team_members_is_active', table_name='team_members')
    op.drop_index('ix_team_members_joined_at', table_name='team_members')
    op.drop_index('ix_team_members_role', table_name='team_members')
    op.drop_index('ix_team_members_user_id', table_name='team_members')
    op.drop_index('ix_team_members_team_id', table_name='team_members')
    op.drop_index('ix_team_members_id', table_name='team_members')
    op.drop_table('team_members')

    op.drop_index('ix_teams_created_at', table_name='teams')
    op.drop_index('ix_teams_is_public', table_name='teams')
    op.drop_index('ix_teams_is_active', table_name='teams')
    op.drop_index('ix_teams_industry', table_name='teams')
    op.drop_index('ix_teams_owner_id', table_name='teams')
    op.drop_index('ix_teams_slug', table_name='teams')
    op.drop_index('ix_teams_name', table_name='teams')
    op.drop_index('ix_teams_id', table_name='teams')
    op.drop_table('teams')

    # Drop enum types
    sa.Enum(name='invitestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamrole').drop(op.get_bind(), checkfirst=True)

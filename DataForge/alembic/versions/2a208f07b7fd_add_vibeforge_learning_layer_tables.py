"""add_vibeforge_learning_layer_tables

Revision ID: 2a208f07b7fd
Revises: 60a104999620
Create Date: 2025-11-22 23:26:37.397421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2a208f07b7fd'
down_revision: Union[str, Sequence[str], None] = '60a104999620'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add VibeForge learning layer tables."""
    
    # Create enum types
    project_type_enum = postgresql.ENUM(
        'web', 'mobile', 'desktop', 'api', 'ai_ml', 'other',
        name='projecttype',
        create_type=False
    )
    project_type_enum.create(op.get_bind(), checkfirst=True)
    
    outcome_status_enum = postgresql.ENUM(
        'success', 'partial', 'failure', 'unknown',
        name='outcomestatus',
        create_type=False
    )
    outcome_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create vibeforge_projects table
    op.create_table(
        'vibeforge_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('project_type', project_type_enum, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('selected_languages', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('selected_stack', sa.String(length=100), nullable=False),
        sa.Column('intent_description', sa.Text(), nullable=True),
        sa.Column('team_size', sa.Integer(), nullable=True),
        sa.Column('timeline_estimate', sa.String(length=50), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vibeforge_projects_id', 'vibeforge_projects', ['id'])
    op.create_index('ix_vibeforge_projects_project_name', 'vibeforge_projects', ['project_name'])
    op.create_index('ix_vibeforge_projects_project_type', 'vibeforge_projects', ['project_type'])
    op.create_index('ix_vibeforge_projects_selected_stack', 'vibeforge_projects', ['selected_stack'])
    op.create_index('ix_vibeforge_projects_user_id', 'vibeforge_projects', ['user_id'])
    op.create_index('ix_vibeforge_projects_created_at', 'vibeforge_projects', ['created_at'])
    
    # Create project_sessions table
    op.create_table(
        'project_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('session_started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('session_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('steps_completed', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('steps_revisited', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('languages_viewed', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('languages_considered', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('languages_final', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('stacks_viewed', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('stacks_compared', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('stack_recommended', sa.String(length=100), nullable=True),
        sa.Column('stack_final', sa.String(length=100), nullable=True),
        sa.Column('stack_override', sa.Boolean(), nullable=True, default=False),
        sa.Column('llm_queries', sa.Integer(), nullable=True, default=0),
        sa.Column('llm_provider_used', sa.String(length=50), nullable=True),
        sa.Column('llm_tokens_consumed', sa.Integer(), nullable=True, default=0),
        sa.Column('abandoned', sa.Boolean(), nullable=True, default=False),
        sa.Column('feedback_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['vibeforge_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_sessions_id', 'project_sessions', ['id'])
    op.create_index('ix_project_sessions_project_id', 'project_sessions', ['project_id'])
    op.create_index('ix_project_sessions_session_started_at', 'project_sessions', ['session_started_at'])
    
    # Create stack_outcomes table
    op.create_table(
        'stack_outcomes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('stack_id', sa.String(length=100), nullable=False),
        sa.Column('project_type', project_type_enum, nullable=False),
        sa.Column('languages_used', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('outcome_status', outcome_status_enum, nullable=False),
        sa.Column('build_successful', sa.Boolean(), nullable=True),
        sa.Column('tests_passed', sa.Boolean(), nullable=True),
        sa.Column('deployed_successfully', sa.Boolean(), nullable=True),
        sa.Column('build_time_seconds', sa.Integer(), nullable=True),
        sa.Column('test_pass_rate', sa.Float(), nullable=True),
        sa.Column('deployment_time_seconds', sa.Integer(), nullable=True),
        sa.Column('user_satisfaction', sa.Integer(), nullable=True),
        sa.Column('would_recommend', sa.Boolean(), nullable=True),
        sa.Column('issues_count', sa.Integer(), nullable=True, default=0),
        sa.Column('issue_types', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fix_iterations', sa.Integer(), nullable=True, default=0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['vibeforge_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stack_outcomes_id', 'stack_outcomes', ['id'])
    op.create_index('ix_stack_outcomes_project_id', 'stack_outcomes', ['project_id'])
    op.create_index('ix_stack_outcomes_stack_id', 'stack_outcomes', ['stack_id'])
    op.create_index('ix_stack_outcomes_project_type', 'stack_outcomes', ['project_type'])
    op.create_index('ix_stack_outcomes_outcome_status', 'stack_outcomes', ['outcome_status'])
    op.create_index('ix_stack_outcomes_recorded_at', 'stack_outcomes', ['recorded_at'])
    
    # Create model_performance table
    op.create_table(
        'model_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prompt_type', sa.String(length=50), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_prompt', sa.Integer(), nullable=True),
        sa.Column('tokens_completion', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('recommendation_accepted', sa.Boolean(), nullable=True),
        sa.Column('recommendation_helpful', sa.Boolean(), nullable=True),
        sa.Column('recommendation_confidence', sa.Float(), nullable=True),
        sa.Column('experiment_id', sa.String(length=100), nullable=True),
        sa.Column('variant', sa.String(length=50), nullable=True),
        sa.Column('context_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['project_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_performance_id', 'model_performance', ['id'])
    op.create_index('ix_model_performance_session_id', 'model_performance', ['session_id'])
    op.create_index('ix_model_performance_provider', 'model_performance', ['provider'])
    op.create_index('ix_model_performance_model_name', 'model_performance', ['model_name'])
    op.create_index('ix_model_performance_experiment_id', 'model_performance', ['experiment_id'])
    op.create_index('ix_model_performance_created_at', 'model_performance', ['created_at'])
    
    # Create language_preferences table
    op.create_table(
        'language_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('language_id', sa.String(length=50), nullable=False),
        sa.Column('language_name', sa.String(length=100), nullable=False),
        sa.Column('times_selected', sa.Integer(), nullable=True, default=0),
        sa.Column('times_viewed', sa.Integer(), nullable=True, default=0),
        sa.Column('times_considered', sa.Integer(), nullable=True, default=0),
        sa.Column('successful_projects', sa.Integer(), nullable=True, default=0),
        sa.Column('failed_projects', sa.Integer(), nullable=True, default=0),
        sa.Column('avg_satisfaction', sa.Float(), nullable=True),
        sa.Column('project_types_used_in', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('paired_with_languages', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('paired_with_stacks', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_language_preferences_id', 'language_preferences', ['id'])
    op.create_index('ix_language_preferences_user_id', 'language_preferences', ['user_id'])
    op.create_index('ix_language_preferences_language_id', 'language_preferences', ['language_id'])
    op.create_index('ix_language_preferences_user_language', 'language_preferences', ['user_id', 'language_id'])


def downgrade() -> None:
    """Downgrade schema - Remove VibeForge learning layer tables."""
    op.drop_table('language_preferences')
    op.drop_table('model_performance')
    op.drop_table('stack_outcomes')
    op.drop_table('project_sessions')
    op.drop_table('vibeforge_projects')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS outcomestatus')
    op.execute('DROP TYPE IF EXISTS projecttype')

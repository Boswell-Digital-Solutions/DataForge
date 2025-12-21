"""add authorforge tables

Revision ID: add_authorforge_001
Revises: 9fe94997bec5
Create Date: 2025-11-16

Adds AuthorForge project management tables:
- projects
- manuscripts
- characters
- locations
- story_arcs
- brainstorm_sessions
- project_genres association table

"""
from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str | None = 'add_authorforge_001'
down_revision: str | None = '9fe94997bec5'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Note: Enum types (genreenum, projectstatus) are created automatically by SQLAlchemy
    # when the first table using them is created

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'completed', 'archived', name='projectstatus'), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('target_word_count', sa.Integer(), nullable=True),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)

    # Create project_genres association table
    op.create_table(
        'project_genres',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('genre', sa.Enum('fantasy', 'scifi', 'christian_fiction', 'general', name='genreenum'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id', 'genre')
    )

    # Create manuscripts table
    op.create_table(
        'manuscripts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('chapter_number', sa.Integer(), nullable=True),
        sa.Column('scene_number', sa.Integer(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_manuscripts_id'), 'manuscripts', ['id'], unique=False)
    op.create_index(op.f('ix_manuscripts_project_id'), 'manuscripts', ['project_id'], unique=False)

    # Create characters table
    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('profile', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('personality', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('relationships', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('arc_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_characters_id'), 'characters', ['id'], unique=False)
    op.create_index(op.f('ix_characters_project_id'), 'characters', ['project_id'], unique=False)

    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_id'), 'locations', ['id'], unique=False)
    op.create_index(op.f('ix_locations_project_id'), 'locations', ['project_id'], unique=False)

    # Create story_arcs table
    op.create_table(
        'story_arcs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('arc_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('beats', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('graph_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_story_arcs_id'), 'story_arcs', ['id'], unique=False)
    op.create_index(op.f('ix_story_arcs_project_id'), 'story_arcs', ['project_id'], unique=False)

    # Create brainstorm_sessions table
    op.create_table(
        'brainstorm_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('genre', sa.Enum('fantasy', 'scifi', 'christian_fiction', 'general', name='genreenum'), nullable=False),
        sa.Column('ideas', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('expanded_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brainstorm_sessions_id'), 'brainstorm_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_brainstorm_sessions_user_id'), 'brainstorm_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_brainstorm_sessions_project_id'), 'brainstorm_sessions', ['project_id'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_brainstorm_sessions_project_id'), table_name='brainstorm_sessions')
    op.drop_index(op.f('ix_brainstorm_sessions_user_id'), table_name='brainstorm_sessions')
    op.drop_index(op.f('ix_brainstorm_sessions_id'), table_name='brainstorm_sessions')
    op.drop_table('brainstorm_sessions')

    op.drop_index(op.f('ix_story_arcs_project_id'), table_name='story_arcs')
    op.drop_index(op.f('ix_story_arcs_id'), table_name='story_arcs')
    op.drop_table('story_arcs')

    op.drop_index(op.f('ix_locations_project_id'), table_name='locations')
    op.drop_index(op.f('ix_locations_id'), table_name='locations')
    op.drop_table('locations')

    op.drop_index(op.f('ix_characters_project_id'), table_name='characters')
    op.drop_index(op.f('ix_characters_id'), table_name='characters')
    op.drop_table('characters')

    op.drop_index(op.f('ix_manuscripts_project_id'), table_name='manuscripts')
    op.drop_index(op.f('ix_manuscripts_id'), table_name='manuscripts')
    op.drop_table('manuscripts')

    op.drop_table('project_genres')

    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_user_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')

    # Drop enum types
    op.execute('DROP TYPE projectstatus')
    op.execute('DROP TYPE genreenum')

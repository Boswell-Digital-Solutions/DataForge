"""add_due_diligence_tables

Revision ID: 76650c588f3a
Revises: add_authorforge_001
Create Date: 2025-11-16 20:48:39.480220

"""
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76650c588f3a'
down_revision: Union[str, Sequence[str], None] = 'add_authorforge_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add Due Diligence tables."""

    # Create diligence_projects table
    op.create_table(
        'diligence_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('git_url', sa.String(length=500), nullable=True),
        sa.Column('repo_path', sa.String(length=500), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('project_metadata', sa.JSON(), nullable=True),
        sa.Column('current_health_status', sa.Enum('green', 'yellow', 'red', name='overallrating'), nullable=True),
        sa.Column('latest_review_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_diligence_projects_id', 'diligence_projects', ['id'])
    op.create_index('ix_diligence_projects_name', 'diligence_projects', ['name'])

    # Create diligence_reviews table
    op.create_table(
        'diligence_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_name', sa.String(length=255), nullable=True),
        sa.Column('review_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('review_type', sa.String(length=50), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('risks', sa.JSON(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('code_quality_score', sa.Float(), nullable=True),
        sa.Column('security_score', sa.Float(), nullable=True),
        sa.Column('architecture_score', sa.Float(), nullable=True),
        sa.Column('operations_score', sa.Float(), nullable=True),
        sa.Column('documentation_score', sa.Float(), nullable=True),
        sa.Column('overall_rating', sa.Enum('green', 'yellow', 'red', name='overallrating'), nullable=True),
        sa.Column('raw_report_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['diligence_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_diligence_reviews_id', 'diligence_reviews', ['id'])
    op.create_index('ix_diligence_reviews_project_id', 'diligence_reviews', ['project_id'])

    # Create diligence_findings table
    op.create_table(
        'diligence_findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.Enum('high', 'medium', 'low', name='findingseverity'), nullable=False),
        sa.Column('status', sa.Enum('open', 'in_progress', 'resolved', name='findingstatus'), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['review_id'], ['diligence_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_diligence_findings_id', 'diligence_findings', ['id'])
    op.create_index('ix_diligence_findings_review_id', 'diligence_findings', ['review_id'])
    op.create_index('ix_diligence_findings_severity', 'diligence_findings', ['severity'])
    op.create_index('ix_diligence_findings_status', 'diligence_findings', ['status'])


def downgrade() -> None:
    """Downgrade schema - Remove Due Diligence tables."""

    # Drop tables in reverse order (due to foreign keys)
    op.drop_index('ix_diligence_findings_status', table_name='diligence_findings')
    op.drop_index('ix_diligence_findings_severity', table_name='diligence_findings')
    op.drop_index('ix_diligence_findings_review_id', table_name='diligence_findings')
    op.drop_index('ix_diligence_findings_id', table_name='diligence_findings')
    op.drop_table('diligence_findings')

    op.drop_index('ix_diligence_reviews_project_id', table_name='diligence_reviews')
    op.drop_index('ix_diligence_reviews_id', table_name='diligence_reviews')
    op.drop_table('diligence_reviews')

    op.drop_index('ix_diligence_projects_name', table_name='diligence_projects')
    op.drop_index('ix_diligence_projects_id', table_name='diligence_projects')
    op.drop_table('diligence_projects')

    # Drop enums (PostgreSQL specific)
    sa.Enum(name='findingstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='findingseverity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='overallrating').drop(op.get_bind(), checkfirst=True)

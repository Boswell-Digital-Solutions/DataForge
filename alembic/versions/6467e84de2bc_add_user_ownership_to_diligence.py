"""add_user_ownership_to_diligence

Revision ID: 6467e84de2bc
Revises: 5261d2b005d9
Create Date: 2025-11-16 21:02:08.198037

"""
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6467e84de2bc'
down_revision: Union[str, Sequence[str], None] = '5261d2b005d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user ownership to diligence projects for security."""
    # Add user_id column to diligence_projects
    op.add_column('diligence_projects',
        sa.Column('user_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_diligence_projects_user_id',
        'diligence_projects', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create index for user_id lookups
    op.create_index('ix_diligence_projects_user_id', 'diligence_projects', ['user_id'])

    # Set existing projects to first admin user (if any exist)
    # In production, you'd want to assign these properly
    op.execute("""
        UPDATE diligence_projects
        SET user_id = (SELECT id FROM users WHERE is_admin = true LIMIT 1)
        WHERE user_id IS NULL
    """)

    # Make user_id NOT NULL after setting existing records
    op.alter_column('diligence_projects', 'user_id', nullable=False)


def downgrade() -> None:
    """Remove user ownership from diligence projects."""
    op.drop_index('ix_diligence_projects_user_id', table_name='diligence_projects')
    op.drop_constraint('fk_diligence_projects_user_id', 'diligence_projects', type_='foreignkey')
    op.drop_column('diligence_projects', 'user_id')

"""rename_metadata_to_project_metadata

Revision ID: 5261d2b005d9
Revises: 76650c588f3a
Create Date: 2025-11-16 20:54:19.119349

"""
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5261d2b005d9'
down_revision: Union[str, Sequence[str], None] = '76650c588f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename metadata column to project_metadata to avoid SQLAlchemy conflict."""
    op.alter_column('diligence_projects', 'metadata', new_column_name='project_metadata')


def downgrade() -> None:
    """Revert metadata column name."""
    op.alter_column('diligence_projects', 'project_metadata', new_column_name='metadata')

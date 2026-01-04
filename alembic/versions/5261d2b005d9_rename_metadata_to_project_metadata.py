"""rename_metadata_to_project_metadata

Revision ID: 5261d2b005d9
Revises: 76650c588f3a
Create Date: 2025-11-16 20:54:19.119349

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    bind = op.get_bind()
    # Only rename if the old column exists; otherwise this migration is a no-op.
    exists = bind.execute(sa.text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'diligence_projects'
          AND column_name = 'metadata'
        LIMIT 1
    """)).scalar()

    if exists:
        op.alter_column('diligence_projects', 'metadata', new_column_name='project_metadata')
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5261d2b005d9'
down_revision: Union[str, Sequence[str], None] = '76650c588f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def downgrade() -> None:
    """Revert metadata column name."""
    op.alter_column('diligence_projects', 'project_metadata', new_column_name='metadata')

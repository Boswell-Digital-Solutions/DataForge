"""merge map cartographer and source entity heads

Revision ID: merge_carto_source
Revises: map_carto_001, entity_source_001
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_carto_source'
down_revision: Union[str, Sequence[str], None] = ('map_carto_001', 'entity_source_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge heads

Revision ID: 34fa1f6a4cbd
Revises: 6467e84de2bc, performance_indexes_001
Create Date: 2025-11-21 22:09:51.473711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34fa1f6a4cbd'
down_revision: Union[str, Sequence[str], None] = ('6467e84de2bc', 'performance_indexes_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

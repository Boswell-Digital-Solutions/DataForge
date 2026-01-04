"""merge remaining heads (final)

Revision ID: ea9a1ba37c87
Revises: 20251221_0500, 7f3a8b9c2d4e, add_tarcie_events
Create Date: 2026-01-04 00:44:18.742858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea9a1ba37c87'
down_revision: Union[str, Sequence[str], None] = ('20251221_0500', '7f3a8b9c2d4e', 'add_tarcie_events')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

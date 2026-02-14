"""merge forgerun and authorforge v2 heads

Revision ID: d14fdfe1b4d0
Revises: 20260116_0400, af_v2_001
Create Date: 2026-02-12 00:36:10.663492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd14fdfe1b4d0'
down_revision: Union[str, Sequence[str], None] = ('20260116_0400', 'af_v2_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

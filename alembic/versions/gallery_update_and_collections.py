"""Add asset updated_at and collection tables

Revision ID: gallery_collections_001
Revises: merge_carto_source
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'gallery_collections_001'
down_revision: Union[str, Sequence[str], None] = 'merge_carto_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add updated_at to assets
    op.add_column('assets', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Asset collections
    op.create_table(
        'asset_collections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Collection-asset junction
    op.create_table(
        'collection_assets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('asset_collections.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('collection_id', 'asset_id', name='uq_collection_asset'),
    )


def downgrade() -> None:
    op.drop_table('collection_assets')
    op.drop_table('asset_collections')
    op.drop_column('assets', 'updated_at')

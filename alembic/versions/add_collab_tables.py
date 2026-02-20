"""add collaboration tables (Y.js sync)

Revision ID: collab_001
Revises: d14fdfe1b4d0
Create Date: 2026-02-12

A2 EXCEPTION: Despite this Alembic migration, the collab tables are
canonically owned by the Fastify API (pg-migrate-forge migrations 002 + 004).
This migration exists for schema awareness only — on a fresh DB where
Fastify migrations run first, these tables already exist when Alembic
reaches this revision. Rationale for Fastify-local ownership:
  1. JWT signing — COLLAB_SECRET held by Fastify; sync server token
     validation at WS upgrade must be low-latency.
  2. Binary snapshots — collab_snapshots stores raw Y.js BYTEA blobs,
     unsuitable for DataForge's JSON REST API.
  3. Ephemeral scope — collab rooms are session-scoped, not long-term data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'collab_001'
down_revision: Union[str, Sequence[str], None] = 'd14fdfe1b4d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- collab_rooms ---
    op.create_table('collab_rooms',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('scene_id', sa.Integer()),
        sa.Column('module', sa.String(), nullable=False, server_default='smithy'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('owner_name', sa.String(), server_default='Author'),
    )

    # --- collab_snapshots ---
    op.create_table('collab_snapshots',
        sa.Column('room_id', sa.String(), sa.ForeignKey('collab_rooms.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('snapshot', sa.LargeBinary(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- collab_tokens ---
    op.create_table('collab_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('room_id', sa.String(), sa.ForeignKey('collab_rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='beta'),
        sa.Column('label', sa.String()),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('collab_tokens')
    op.drop_table('collab_snapshots')
    op.drop_table('collab_rooms')

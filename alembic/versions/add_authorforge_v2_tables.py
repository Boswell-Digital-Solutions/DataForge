"""add authorforge v2 tables (spec v3)

Revision ID: af_v2_001
Revises: ea9a1ba37c87
Create Date: 2026-02-11

Adds 18 new tables for AuthorForge Architecture Spec v3:
chapters, scenes, lore_entities, lore_edges, arcs, beats, style_profiles,
assets, factions, consistency_alerts, covers, map_nodes, map_edges,
map_edge_modifiers, map_regions, lore_pins, character_knowledge, journeys.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'af_v2_001'
down_revision: Union[str, Sequence[str], None] = 'ea9a1ba37c87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enum types (use raw SQL with IF NOT EXISTS for idempotency) ---
    # Fix for AF-T0-003: Avoid "type already exists" error on non-fresh DBs
    conn = op.get_bind()

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE scenestatus AS ENUM ('blank', 'draft', 'revision', 'final');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE entitykind AS ENUM ('character', 'location', 'artifact', 'magic_rule', 'event', 'faction', 'creature', 'theme');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE edgetype AS ENUM ('member_of', 'contradicts', 'governs', 'influences', 'located_in', 'relates_to');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE knowledgetype AS ENUM ('visited', 'heard_of', 'rumored');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE assetsourcetype AS ENUM ('upload', 'ai_generated', 'url');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE assettype AS ENUM ('image', 'icon', 'texture', 'cover');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE pintype AS ENUM ('battle', 'event', 'landmark', 'note');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """))

    # Now define the enum types for SQLAlchemy (create_type=False since we created them above)
    scene_status = sa.Enum('blank', 'draft', 'revision', 'final', name='scenestatus', create_type=False)
    entity_kind = sa.Enum('character', 'location', 'artifact', 'magic_rule', 'event', 'faction', 'creature', 'theme', name='entitykind', create_type=False)
    edge_type = sa.Enum('member_of', 'contradicts', 'governs', 'influences', 'located_in', 'relates_to', name='edgetype', create_type=False)
    knowledge_type = sa.Enum('visited', 'heard_of', 'rumored', name='knowledgetype', create_type=False)
    asset_source_type = sa.Enum('upload', 'ai_generated', 'url', name='assetsourcetype', create_type=False)
    asset_type = sa.Enum('image', 'icon', 'texture', 'cover', name='assettype', create_type=False)
    pin_type = sa.Enum('battle', 'event', 'landmark', 'note', name='pintype', create_type=False)

    # --- chapters ---
    op.create_table('chapters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('word_count', sa.Integer(), server_default='0'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- scenes ---
    op.create_table('scenes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('chapter_id', sa.Integer(), sa.ForeignKey('chapters.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('goal', sa.Text()),
        sa.Column('content_html', sa.Text(), server_default=''),
        sa.Column('status', scene_status, server_default='blank'),
        sa.Column('word_count', sa.Integer(), server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- lore_entities ---
    op.create_table('lore_entities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('kind', entity_kind, nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), index=True),
        sa.Column('summary', sa.Text()),
        sa.Column('attributes_json', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- lore_edges ---
    op.create_table('lore_edges',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('lore_entities.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('lore_entities.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('edge_type', edge_type, nullable=False, index=True),
        sa.Column('properties_json', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- arcs ---
    op.create_table('arcs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('color', sa.String(7)),
        sa.Column('arc_type', sa.String(50)),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- beats ---
    op.create_table('beats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('arc_id', sa.Integer(), sa.ForeignKey('arcs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('scene_id', sa.Integer(), sa.ForeignKey('scenes.id', ondelete='SET NULL'), index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('intensity', sa.Float(), server_default='0.5'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- style_profiles ---
    op.create_table('style_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), index=True),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('style_profiles.id', ondelete='SET NULL')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('rules_json', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- assets ---
    op.create_table('assets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='SET NULL'), index=True),
        sa.Column('source_type', asset_source_type, nullable=False),
        sa.Column('cdn_url', sa.Text()),
        sa.Column('asset_type', asset_type, nullable=False),
        sa.Column('filename', sa.String(500)),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('metadata_json', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- factions ---
    op.create_table('factions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('alignment', sa.String(50)),
        sa.Column('goal', sa.Text()),
        sa.Column('description', sa.Text()),
        sa.Column('members_json', sa.JSON(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- consistency_alerts ---
    op.create_table('consistency_alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('scene_id', sa.Integer(), sa.ForeignKey('scenes.id', ondelete='SET NULL')),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(50)),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('context_json', sa.JSON(), server_default='{}'),
        sa.Column('resolved', sa.Boolean(), server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- covers ---
    op.create_table('covers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('trim_width', sa.Float(), nullable=False),
        sa.Column('trim_height', sa.Float(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('paper_type', sa.String(50)),
        sa.Column('binding', sa.String(50), server_default='softcover'),
        sa.Column('spine_width', sa.Float()),
        sa.Column('layers_json', sa.JSON(), server_default='[]'),
        sa.Column('barcode_isbn', sa.String(13)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- map_nodes ---
    op.create_table('map_nodes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('kind', sa.String(50)),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('biome', sa.String(50)),
        sa.Column('elevation', sa.Float()),
        sa.Column('population', sa.Integer()),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('lore_entities.id', ondelete='SET NULL')),
        sa.Column('era_from', sa.Integer()),
        sa.Column('era_to', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # --- map_edges ---
    op.create_table('map_edges',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('from_id', sa.Integer(), sa.ForeignKey('map_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('to_id', sa.Integer(), sa.ForeignKey('map_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('distance_km', sa.Float(), nullable=False),
        sa.Column('terrain_penalty', sa.Float(), server_default='1.0'),
        sa.Column('infra_bonus', sa.Float(), server_default='1.0'),
        sa.Column('bidirectional', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- map_edge_modifiers ---
    op.create_table('map_edge_modifiers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('edge_id', sa.Integer(), sa.ForeignKey('map_edges.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('active_from', sa.Integer()),
        sa.Column('active_to', sa.Integer()),
        sa.Column('multiplier', sa.Float(), server_default='1.0'),
        sa.Column('reason', sa.Text()),
        sa.Column('priority', sa.Integer(), server_default='0'),
    )

    # --- map_regions ---
    op.create_table('map_regions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('biome', sa.String(50), nullable=False),
        sa.Column('path_data', sa.Text(), nullable=False),
        sa.Column('era_from', sa.Integer()),
        sa.Column('era_to', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- lore_pins ---
    op.create_table('lore_pins',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('scene_ref', sa.Integer(), sa.ForeignKey('scenes.id', ondelete='SET NULL')),
        sa.Column('pin_type', pin_type),
        sa.Column('era', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- character_knowledge ---
    op.create_table('character_knowledge',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('lore_entities.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('map_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('knowledge_type', knowledge_type, nullable=False),
        sa.Column('acquired_scene_id', sa.Integer(), sa.ForeignKey('scenes.id', ondelete='SET NULL')),
    )

    # --- journeys ---
    op.create_table('journeys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('from_id', sa.Integer(), sa.ForeignKey('map_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_id', sa.Integer(), sa.ForeignKey('map_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('timeline_t', sa.Integer()),
        sa.Column('path_json', sa.JSON()),
        sa.Column('total_days', sa.Float()),
        sa.Column('proof_hash', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('journeys')
    op.drop_table('character_knowledge')
    op.drop_table('lore_pins')
    op.drop_table('map_regions')
    op.drop_table('map_edge_modifiers')
    op.drop_table('map_edges')
    op.drop_table('map_nodes')
    op.drop_table('covers')
    op.drop_table('consistency_alerts')
    op.drop_table('factions')
    op.drop_table('assets')
    op.drop_table('style_profiles')
    op.drop_table('beats')
    op.drop_table('arcs')
    op.drop_table('lore_edges')
    op.drop_table('lore_entities')
    op.drop_table('scenes')
    op.drop_table('chapters')

    # Drop enum types
    sa.Enum(name='pintype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assettype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assetsourcetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='knowledgetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='edgetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='entitykind').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='scenestatus').drop(op.get_bind(), checkfirst=True)

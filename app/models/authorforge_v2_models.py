"""
AuthorForge V2 Database Models

Extends DataForge with the full AuthorForge Architecture Spec v3 data model:
chapters, scenes, knowledge graph (entities + edges), arcs, beats,
style profiles, assets, factions, consistency alerts, covers,
and Cartographer's Forge map tables.

These models share the same database as DataForge for seamless integration.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, ForeignKey,
    DateTime, Enum as SQLEnum, JSON, LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# ============================================
# Enums
# ============================================

class SceneStatus(str, enum.Enum):
    BLANK = "blank"
    DRAFT = "draft"
    REVISION = "revision"
    FINAL = "final"


class EntityKind(str, enum.Enum):
    CHARACTER = "character"
    LOCATION = "location"
    ARTIFACT = "artifact"
    MAGIC_RULE = "magic_rule"
    EVENT = "event"
    FACTION = "faction"
    CREATURE = "creature"
    THEME = "theme"


class EdgeType(str, enum.Enum):
    MEMBER_OF = "member_of"
    CONTRADICTS = "contradicts"
    GOVERNS = "governs"
    INFLUENCES = "influences"
    LOCATED_IN = "located_in"
    RELATES_TO = "relates_to"


class AlertTier(int, enum.Enum):
    LOW = 1
    MODERATE = 2
    CRITICAL = 3


class KnowledgeType(str, enum.Enum):
    VISITED = "visited"
    HEARD_OF = "heard_of"
    RUMORED = "rumored"


class AssetSourceType(str, enum.Enum):
    UPLOAD = "upload"
    AI_GENERATED = "ai_generated"
    URL = "url"


class AssetType(str, enum.Enum):
    IMAGE = "image"
    ICON = "icon"
    TEXTURE = "texture"
    COVER = "cover"


class PinType(str, enum.Enum):
    BATTLE = "battle"
    EVENT = "event"
    LANDMARK = "landmark"
    NOTE = "note"


# ============================================
# Core Writing Models
# ============================================

class Chapter(Base):
    """Ordered chapter entries within a project."""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="chapters")
    scenes = relationship("Scene", back_populates="chapter", cascade="all, delete-orphan", order_by="Scene.sort_order")


class Scene(Base):
    """Individual writing units within a chapter."""
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    goal = Column(Text)
    content_html = Column(Text, default="")
    status = Column(SQLEnum(SceneStatus), default=SceneStatus.BLANK)
    word_count = Column(Integer, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    chapter = relationship("Chapter", back_populates="scenes")


# ============================================
# Knowledge Graph Models (Lore)
# ============================================

class LoreEntity(Base):
    """Generic knowledge graph node for the Lore system (Constellation Canvas)."""
    __tablename__ = "lore_entities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(SQLEnum(EntityKind), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)
    summary = Column(Text)
    attributes_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="lore_entities")
    outgoing_edges = relationship("LoreEdge", foreign_keys="LoreEdge.source_id", back_populates="source", cascade="all, delete-orphan")
    incoming_edges = relationship("LoreEdge", foreign_keys="LoreEdge.target_id", back_populates="target", cascade="all, delete-orphan")


class LoreEdge(Base):
    """Knowledge graph relationship between two entities."""
    __tablename__ = "lore_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("lore_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("lore_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type = Column(SQLEnum(EdgeType), nullable=False, index=True)
    properties_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("LoreEntity", foreign_keys=[source_id], back_populates="outgoing_edges")
    target = relationship("LoreEntity", foreign_keys=[target_id], back_populates="incoming_edges")


# ============================================
# Story Structure Models (Anvil)
# ============================================

class Arc(Base):
    """Story structure arc for the Arc Weaver (Anvil module)."""
    __tablename__ = "arcs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    color = Column(String(7))  # hex color e.g. #FF6A3D
    arc_type = Column(String(50))  # main_plot, subplot, character_arc, thematic
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="arcs")
    beats = relationship("Beat", back_populates="arc", cascade="all, delete-orphan", order_by="Beat.sort_order")


class Beat(Base):
    """Arc pivot point linking arcs to scenes."""
    __tablename__ = "beats"

    id = Column(Integer, primary_key=True, index=True)
    arc_id = Column(Integer, ForeignKey("arcs.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    intensity = Column(Float, default=0.5)  # 0.0 to 1.0
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    arc = relationship("Arc", back_populates="beats")
    scene = relationship("Scene", backref="beats")


# ============================================
# Style System (Crucible)
# ============================================

class StyleProfile(Base):
    """Cascading style rules for the Crucible module."""
    __tablename__ = "style_profiles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    scope = Column(String(50), nullable=False)  # global, user, project, document
    parent_id = Column(Integer, ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    rules_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("StyleProfile", remote_side="StyleProfile.id", backref="children")


# ============================================
# Asset Library (Gallery)
# ============================================

class Asset(Base):
    """Unified image asset for the Gallery module."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(SQLEnum(AssetSourceType), nullable=False)
    cdn_url = Column(Text)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    filename = Column(String(500))
    tags = Column(JSON, default=[])
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# World Organizations
# ============================================

class Faction(Base):
    """World organizations for the Lore module."""
    __tablename__ = "factions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    alignment = Column(String(50))
    goal = Column(Text)
    description = Column(Text)
    members_json = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="factions")


# ============================================
# Consistency Guard
# ============================================

class ConsistencyAlert(Base):
    """Consistency Guard findings with three-tier notification model."""
    __tablename__ = "consistency_alerts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)
    tier = Column(Integer, nullable=False)  # 1=LOW, 2=MODERATE, 3=CRITICAL
    alert_type = Column(String(50))  # trait, temporal, physical, plot_hole, travel, magic_rule
    description = Column(Text, nullable=False)
    context_json = Column(JSON, default={})  # entity refs, quotes, suggestions
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", backref="consistency_alerts")


# ============================================
# Cover Forge
# ============================================

class Cover(Base):
    """Book cover design project for Cover Forge module."""
    __tablename__ = "covers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # ingram_spark, kdp, bn_press
    trim_width = Column(Float, nullable=False)  # inches
    trim_height = Column(Float, nullable=False)
    page_count = Column(Integer, nullable=False)
    paper_type = Column(String(50))  # white_50, cream_50, color_80
    binding = Column(String(50), default="softcover")
    spine_width = Column(Float)  # computed, inches
    layers_json = Column(JSON, default=[])  # [{type, zone, position, styling, z_order}]
    barcode_isbn = Column(String(13))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="covers")


# ============================================
# Cartographer's Forge (World Map Builder)
# ============================================

class MapNode(Base):
    """Location node on the world map."""
    __tablename__ = "map_nodes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(50))  # city, town, village, fortress, ruin, landmark
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    biome = Column(String(50))  # plains, forest, desert, mountain, ocean, swamp, tundra, volcanic
    elevation = Column(Float)
    population = Column(Integer)
    entity_id = Column(Integer, ForeignKey("lore_entities.id", ondelete="SET NULL"), nullable=True)
    era_from = Column(Integer)
    era_to = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="map_nodes")
    entity = relationship("LoreEntity", backref="map_nodes")


class MapEdge(Base):
    """Road or path between two map locations."""
    __tablename__ = "map_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_id = Column(Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    to_id = Column(Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    distance_km = Column(Float, nullable=False)
    terrain_penalty = Column(Float, default=1.0)
    infra_bonus = Column(Float, default=1.0)
    bidirectional = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_node = relationship("MapNode", foreign_keys=[from_id], backref="outgoing_roads")
    to_node = relationship("MapNode", foreign_keys=[to_id], backref="incoming_roads")
    modifiers = relationship("MapEdgeModifier", back_populates="edge", cascade="all, delete-orphan")


class MapEdgeModifier(Base):
    """Timeline-indexed changes to a map edge (road destroyed, bridge built, etc.)."""
    __tablename__ = "map_edge_modifiers"

    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(Integer, ForeignKey("map_edges.id", ondelete="CASCADE"), nullable=False, index=True)
    active_from = Column(Integer)
    active_to = Column(Integer)
    multiplier = Column(Float, default=1.0)
    reason = Column(Text)
    priority = Column(Integer, default=0)

    edge = relationship("MapEdge", back_populates="modifiers")


class MapRegion(Base):
    """Painted biome polygon on the world map."""
    __tablename__ = "map_regions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    biome = Column(String(50), nullable=False)
    path_data = Column(Text, nullable=False)  # SVG path data
    era_from = Column(Integer)
    era_to = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", backref="map_regions")


class LorePin(Base):
    """Narrative marker on the world map linking to manuscript scenes."""
    __tablename__ = "lore_pins"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    scene_ref = Column(Integer, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)
    pin_type = Column(SQLEnum(PinType))
    era = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", backref="lore_pins")
    scene = relationship("Scene", backref="lore_pins")


class CharacterKnowledge(Base):
    """Fog of Knowledge: tracks what each character knows about map locations."""
    __tablename__ = "character_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("lore_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_type = Column(SQLEnum(KnowledgeType), nullable=False)
    acquired_scene_id = Column(Integer, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)

    entity = relationship("LoreEntity", backref="knowledge")
    node = relationship("MapNode", backref="known_by")
    acquired_scene = relationship("Scene", backref="knowledge_reveals")


class Journey(Base):
    """Cached travel calculation between two map nodes."""
    __tablename__ = "journeys"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    from_id = Column(Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False)
    to_id = Column(Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False)
    method = Column(String(50), nullable=False)  # walking, horseback, caravan, ship, airship
    timeline_t = Column(Integer)
    path_json = Column(JSON)  # ordered list of node IDs in the path
    total_days = Column(Float)
    proof_hash = Column(String(64))  # determinism audit hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", backref="journeys")
    from_node = relationship("MapNode", foreign_keys=[from_id])
    to_node = relationship("MapNode", foreign_keys=[to_id])


# ============================================
# Collaboration Tables (Y.js sync)
# ============================================

class CollabRoom(Base):
    """Collaboration room for real-time Y.js editing sessions."""
    __tablename__ = "collab_rooms"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    scene_id = Column(Integer)
    module = Column(String, nullable=False, server_default="smithy")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    owner_name = Column(String, server_default="Author")

    snapshots = relationship("CollabSnapshot", back_populates="room", cascade="all, delete-orphan")
    tokens = relationship("CollabToken", back_populates="room", cascade="all, delete-orphan")


class CollabSnapshot(Base):
    """Binary Y.js document snapshot for persistence."""
    __tablename__ = "collab_snapshots"

    room_id = Column(String, ForeignKey("collab_rooms.id", ondelete="CASCADE"), primary_key=True)
    snapshot = Column(LargeBinary, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("CollabRoom", back_populates="snapshots")


class CollabToken(Base):
    """Share link token for room access with role-based permissions."""
    __tablename__ = "collab_tokens"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("collab_rooms.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False, server_default="beta")
    label = Column(String)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))

    room = relationship("CollabRoom", back_populates="tokens")

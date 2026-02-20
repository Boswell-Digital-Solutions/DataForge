"""
AuthorForge V2 Pydantic Schemas

API request/response models for all AuthorForge V2 endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# Enums (match SQLAlchemy enums)
# ============================================

class SceneStatusEnum(str, Enum):
    BLANK = "blank"
    DRAFT = "draft"
    REVISION = "revision"
    FINAL = "final"


class EntityKindEnum(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    ARTIFACT = "artifact"
    MAGIC_RULE = "magic_rule"
    EVENT = "event"
    FACTION = "faction"
    CREATURE = "creature"
    THEME = "theme"
    SOURCE = "source"


class EdgeTypeEnum(str, Enum):
    MEMBER_OF = "member_of"
    CONTRADICTS = "contradicts"
    GOVERNS = "governs"
    INFLUENCES = "influences"
    LOCATED_IN = "located_in"
    RELATES_TO = "relates_to"


class KnowledgeTypeEnum(str, Enum):
    VISITED = "visited"
    HEARD_OF = "heard_of"
    RUMORED = "rumored"


class AssetSourceTypeEnum(str, Enum):
    UPLOAD = "upload"
    AI_GENERATED = "ai_generated"
    URL = "url"


class AssetTypeEnum(str, Enum):
    IMAGE = "image"
    ICON = "icon"
    TEXTURE = "texture"
    COVER = "cover"


class PinTypeEnum(str, Enum):
    BATTLE = "battle"
    EVENT = "event"
    LANDMARK = "landmark"
    NOTE = "note"


# ============================================
# Chapter Schemas
# ============================================

class ChapterCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    sort_order: int = 0
    notes: Optional[str] = None


class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    sort_order: Optional[int] = None
    word_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class ChapterResponse(BaseModel):
    id: int
    project_id: int
    title: str
    sort_order: int
    word_count: int = 0
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChapterWithScenes(ChapterResponse):
    scenes: List["SceneResponse"] = []


# ============================================
# Scene Schemas
# ============================================

class SceneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    goal: Optional[str] = None
    content_html: str = ""
    status: SceneStatusEnum = SceneStatusEnum.BLANK
    sort_order: int = 0
    notes: Optional[str] = None


class SceneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    goal: Optional[str] = None
    content_html: Optional[str] = None
    status: Optional[SceneStatusEnum] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class SceneResponse(BaseModel):
    id: int
    chapter_id: int
    title: str
    goal: Optional[str] = None
    content_html: str = ""
    status: SceneStatusEnum = SceneStatusEnum.BLANK
    word_count: int = 0
    sort_order: int = 0
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Entity Schemas (Knowledge Graph Nodes)
# ============================================

class EntityCreate(BaseModel):
    kind: EntityKindEnum
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None
    attributes_json: Dict[str, Any] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    kind: Optional[EntityKindEnum] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None
    attributes_json: Optional[Dict[str, Any]] = None


class EntityResponse(BaseModel):
    id: int
    project_id: int
    kind: EntityKindEnum
    name: str
    slug: Optional[str] = None
    summary: Optional[str] = None
    attributes_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Edge Schemas (Knowledge Graph Relationships)
# ============================================

class EdgeCreate(BaseModel):
    source_id: int
    target_id: int
    edge_type: EdgeTypeEnum
    properties_json: Dict[str, Any] = Field(default_factory=dict)


class EdgeResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    edge_type: EdgeTypeEnum
    properties_json: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Arc Schemas
# ============================================

class ArcCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: Optional[str] = Field(None, max_length=7)
    arc_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class ArcUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = Field(None, max_length=7)
    arc_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class ArcResponse(BaseModel):
    id: int
    project_id: int
    name: str
    color: Optional[str] = None
    arc_type: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ArcWithBeats(ArcResponse):
    beats: List["BeatResponse"] = []


# ============================================
# Beat Schemas
# ============================================

class BeatCreate(BaseModel):
    scene_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = None
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    sort_order: int = 0


class BeatUpdate(BaseModel):
    scene_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0)
    sort_order: Optional[int] = None


class BeatResponse(BaseModel):
    id: int
    arc_id: int
    scene_id: Optional[int] = None
    title: str
    summary: Optional[str] = None
    intensity: float = 0.5
    sort_order: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Style Profile Schemas
# ============================================

class StyleProfileCreate(BaseModel):
    scope: str = Field(..., max_length=50)
    parent_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=255)
    rules_json: Dict[str, Any] = Field(default_factory=dict)


class StyleProfileUpdate(BaseModel):
    scope: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rules_json: Optional[Dict[str, Any]] = None


class StyleProfileResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    scope: str
    parent_id: Optional[int] = None
    name: str
    rules_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Asset Schemas
# ============================================

class AssetCreate(BaseModel):
    source_type: AssetSourceTypeEnum
    cdn_url: Optional[str] = None
    asset_type: AssetTypeEnum
    filename: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class AssetResponse(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    source_type: AssetSourceTypeEnum
    cdn_url: Optional[str] = None
    asset_type: AssetTypeEnum
    filename: Optional[str] = None
    tags: List[str] = []
    metadata_json: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Faction Schemas
# ============================================

class FactionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    alignment: Optional[str] = Field(None, max_length=50)
    goal: Optional[str] = None
    description: Optional[str] = None
    members_json: List[Any] = Field(default_factory=list)


class FactionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    alignment: Optional[str] = Field(None, max_length=50)
    goal: Optional[str] = None
    description: Optional[str] = None
    members_json: Optional[List[Any]] = None


class FactionResponse(BaseModel):
    id: int
    project_id: int
    name: str
    alignment: Optional[str] = None
    goal: Optional[str] = None
    description: Optional[str] = None
    members_json: List[Any] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Consistency Alert Schemas
# ============================================

class ConsistencyAlertCreate(BaseModel):
    scene_id: Optional[int] = None
    tier: int = Field(..., ge=1, le=3)
    alert_type: Optional[str] = Field(None, max_length=50)
    description: str = Field(..., min_length=1)
    context_json: Dict[str, Any] = Field(default_factory=dict)


class ConsistencyAlertUpdate(BaseModel):
    resolved: Optional[bool] = None
    context_json: Optional[Dict[str, Any]] = None


class ConsistencyAlertResponse(BaseModel):
    id: int
    project_id: int
    scene_id: Optional[int] = None
    tier: int
    alert_type: Optional[str] = None
    description: str
    context_json: Dict[str, Any] = {}
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Cover Schemas
# ============================================

class CoverCreate(BaseModel):
    platform: str = Field(..., max_length=50)
    trim_width: float = Field(..., gt=0)
    trim_height: float = Field(..., gt=0)
    page_count: int = Field(..., gt=0)
    paper_type: Optional[str] = Field(None, max_length=50)
    binding: str = "softcover"
    spine_width: Optional[float] = None
    layers_json: List[Dict[str, Any]] = Field(default_factory=list)
    barcode_isbn: Optional[str] = Field(None, max_length=13)


class CoverUpdate(BaseModel):
    platform: Optional[str] = Field(None, max_length=50)
    trim_width: Optional[float] = Field(None, gt=0)
    trim_height: Optional[float] = Field(None, gt=0)
    page_count: Optional[int] = Field(None, gt=0)
    paper_type: Optional[str] = Field(None, max_length=50)
    binding: Optional[str] = None
    spine_width: Optional[float] = None
    layers_json: Optional[List[Dict[str, Any]]] = None
    barcode_isbn: Optional[str] = Field(None, max_length=13)


class CoverResponse(BaseModel):
    id: int
    project_id: int
    platform: str
    trim_width: float
    trim_height: float
    page_count: int
    paper_type: Optional[str] = None
    binding: str = "softcover"
    spine_width: Optional[float] = None
    layers_json: List[Dict[str, Any]] = []
    barcode_isbn: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Map Node Schemas
# ============================================

class MapNodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    kind: Optional[str] = Field(None, max_length=50)
    x: float
    y: float
    biome: Optional[str] = Field(None, max_length=50)
    elevation: Optional[float] = None
    population: Optional[int] = None
    entity_id: Optional[int] = None
    era_from: Optional[int] = None
    era_to: Optional[int] = None


class MapNodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    kind: Optional[str] = Field(None, max_length=50)
    x: Optional[float] = None
    y: Optional[float] = None
    biome: Optional[str] = Field(None, max_length=50)
    elevation: Optional[float] = None
    population: Optional[int] = None
    entity_id: Optional[int] = None
    era_from: Optional[int] = None
    era_to: Optional[int] = None


class MapNodeResponse(BaseModel):
    id: int
    project_id: int
    name: str
    kind: Optional[str] = None
    x: float
    y: float
    biome: Optional[str] = None
    elevation: Optional[float] = None
    population: Optional[int] = None
    entity_id: Optional[int] = None
    era_from: Optional[int] = None
    era_to: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Map Edge Schemas
# ============================================

class MapEdgeCreate(BaseModel):
    from_id: int
    to_id: int
    distance_km: float = Field(..., gt=0)
    terrain_penalty: float = 1.0
    infra_bonus: float = 1.0
    bidirectional: bool = True


class MapEdgeResponse(BaseModel):
    id: int
    from_id: int
    to_id: int
    distance_km: float
    terrain_penalty: float = 1.0
    infra_bonus: float = 1.0
    bidirectional: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Edge Modifier Schemas
# ============================================

class MapEdgeModifierCreate(BaseModel):
    active_from: Optional[int] = None
    active_to: Optional[int] = None
    multiplier: float = 1.0
    reason: Optional[str] = None
    priority: int = 0


class MapEdgeModifierResponse(BaseModel):
    id: int
    edge_id: int
    active_from: Optional[int] = None
    active_to: Optional[int] = None
    multiplier: float = 1.0
    reason: Optional[str] = None
    priority: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Map Region Schemas
# ============================================

class MapRegionCreate(BaseModel):
    biome: str = Field(..., max_length=50)
    path_data: str = Field(..., min_length=1)
    era_from: Optional[int] = None
    era_to: Optional[int] = None


class MapRegionResponse(BaseModel):
    id: int
    project_id: int
    biome: str
    path_data: str
    era_from: Optional[int] = None
    era_to: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Lore Pin Schemas
# ============================================

class LorePinCreate(BaseModel):
    x: float
    y: float
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scene_ref: Optional[int] = None
    pin_type: Optional[PinTypeEnum] = None
    era: Optional[int] = None


class LorePinUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scene_ref: Optional[int] = None
    pin_type: Optional[PinTypeEnum] = None
    era: Optional[int] = None


class LorePinResponse(BaseModel):
    id: int
    project_id: int
    x: float
    y: float
    title: str
    description: Optional[str] = None
    scene_ref: Optional[int] = None
    pin_type: Optional[PinTypeEnum] = None
    era: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Character Knowledge Schemas
# ============================================

class CharacterKnowledgeCreate(BaseModel):
    entity_id: int
    node_id: int
    knowledge_type: KnowledgeTypeEnum
    acquired_scene_id: Optional[int] = None


class CharacterKnowledgeResponse(BaseModel):
    id: int
    entity_id: int
    node_id: int
    knowledge_type: KnowledgeTypeEnum
    acquired_scene_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Journey Schemas
# ============================================

class JourneyCreate(BaseModel):
    from_id: int
    to_id: int
    method: str = Field(..., max_length=50)
    timeline_t: Optional[int] = None
    path_json: Optional[List[int]] = None
    total_days: Optional[float] = None
    proof_hash: Optional[str] = Field(None, max_length=64)


class JourneyResponse(BaseModel):
    id: int
    project_id: int
    from_id: int
    to_id: int
    method: str
    timeline_t: Optional[int] = None
    path_json: Optional[List[int]] = None
    total_days: Optional[float] = None
    proof_hash: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Cartographer's Forge — Settings / Viewports / Exports
# ============================================

class MapSettingsUpdate(BaseModel):
    canvas_width: Optional[int] = None
    canvas_height: Optional[int] = None
    scale_km_per_unit: Optional[float] = None
    grid_enabled: Optional[bool] = None
    grid_size: Optional[int] = None


class MapSettingsResponse(BaseModel):
    project_id: int
    canvas_width: int
    canvas_height: int
    scale_km_per_unit: float
    grid_enabled: bool
    grid_size: int

    model_config = ConfigDict(from_attributes=True)


class MapViewportCreate(BaseModel):
    name: str = "Full Map"
    crop_x: float = 0
    crop_y: float = 0
    crop_w: float = 640
    crop_h: float = 400
    output_width: int = 1920
    output_height: int = 1200
    dpi: int = 150
    show_labels: bool = True
    show_roads: bool = True
    show_pins: bool = True
    show_grid: bool = False
    show_compass: bool = True
    is_default: bool = False


class MapViewportUpdate(BaseModel):
    name: Optional[str] = None
    crop_x: Optional[float] = None
    crop_y: Optional[float] = None
    crop_w: Optional[float] = None
    crop_h: Optional[float] = None
    output_width: Optional[int] = None
    output_height: Optional[int] = None
    dpi: Optional[int] = None
    show_labels: Optional[bool] = None
    show_roads: Optional[bool] = None
    show_pins: Optional[bool] = None
    show_grid: Optional[bool] = None
    show_compass: Optional[bool] = None
    is_default: Optional[bool] = None


class MapViewportResponse(BaseModel):
    id: str
    project_id: int
    name: str
    crop_x: float
    crop_y: float
    crop_w: float
    crop_h: float
    output_width: int
    output_height: int
    dpi: int
    show_labels: bool
    show_roads: bool
    show_pins: bool
    show_grid: bool
    show_compass: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MapExportCreate(BaseModel):
    viewport_id: Optional[str] = None
    name: str = "Untitled Export"
    format: str = "png"
    dpi: int = 150
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    file_size: Optional[int] = None
    svg_hash: Optional[str] = None


class MapExportResponse(BaseModel):
    id: str
    project_id: int
    viewport_id: Optional[str] = None
    name: str
    format: str
    dpi: int
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    file_size: Optional[int] = None
    svg_hash: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Forward reference resolution
ChapterWithScenes.model_rebuild()
ArcWithBeats.model_rebuild()

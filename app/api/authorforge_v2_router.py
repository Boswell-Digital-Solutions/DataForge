"""
AuthorForge V2 API Router

Endpoints for chapters, scenes, knowledge graph, arcs, beats,
style profiles, assets, factions, alerts, covers, and map features.
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import User
from app.models.authorforge_v2_schemas import (
    # Chapters
    ChapterCreate, ChapterUpdate, ChapterResponse, ChapterWithScenes,
    # Scenes
    SceneCreate, SceneUpdate, SceneResponse,
    # Entities
    EntityCreate, EntityUpdate, EntityResponse,
    # Edges
    EdgeCreate, EdgeResponse,
    # Arcs
    ArcCreate, ArcUpdate, ArcResponse, ArcWithBeats,
    # Beats
    BeatCreate, BeatUpdate, BeatResponse,
    # Style Profiles
    StyleProfileCreate, StyleProfileUpdate, StyleProfileResponse,
    # Assets
    AssetCreate, AssetResponse,
    # Factions
    FactionCreate, FactionUpdate, FactionResponse,
    # Alerts
    ConsistencyAlertCreate, ConsistencyAlertUpdate, ConsistencyAlertResponse,
    # Covers
    CoverCreate, CoverUpdate, CoverResponse,
    # Map
    MapNodeCreate, MapNodeUpdate, MapNodeResponse,
    MapEdgeCreate, MapEdgeResponse,
    MapEdgeModifierCreate, MapEdgeModifierResponse,
    MapRegionCreate, MapRegionResponse,
    LorePinCreate, LorePinUpdate, LorePinResponse,
    CharacterKnowledgeCreate, CharacterKnowledgeResponse,
    JourneyCreate, JourneyResponse,
)
from app.api import authorforge_v2_crud as crud
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["authorforge-v2"])


# ============================================
# Chapters
# ============================================

@router.get("/{project_id}/chapters", response_model=List[ChapterResponse])
def list_chapters(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_chapters(db, project_id, current_user.id)


@router.get("/{project_id}/chapters/full", response_model=List[ChapterWithScenes])
def list_chapters_with_scenes(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List chapters with nested scenes (for outline view)."""
    return crud.list_chapters(db, project_id, current_user.id)


@router.post("/{project_id}/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
def create_chapter(
    project_id: int,
    data: ChapterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ch = crud.create_chapter(db, project_id, current_user.id, data)
    if not ch:
        raise HTTPException(status_code=404, detail="Project not found")
    return ch


@router.patch("/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(
    chapter_id: int,
    data: ChapterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ch = crud.update_chapter(db, chapter_id, current_user.id, data)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return ch


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_chapter(db, chapter_id, current_user.id):
        raise HTTPException(status_code=404, detail="Chapter not found")


# ============================================
# Scenes
# ============================================

@router.get("/chapters/{chapter_id}/scenes", response_model=List[SceneResponse])
def list_scenes(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_scenes(db, chapter_id, current_user.id)


@router.post("/chapters/{chapter_id}/scenes", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
def create_scene(
    chapter_id: int,
    data: SceneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sc = crud.create_scene(db, chapter_id, current_user.id, data)
    if not sc:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return sc


@router.get("/scenes/{scene_id}", response_model=SceneResponse)
def get_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sc = crud.get_scene(db, scene_id, current_user.id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scene not found")
    return sc


@router.patch("/scenes/{scene_id}", response_model=SceneResponse)
def update_scene(
    scene_id: int,
    data: SceneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sc = crud.update_scene(db, scene_id, current_user.id, data)
    if not sc:
        raise HTTPException(status_code=404, detail="Scene not found")
    return sc


@router.delete("/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_scene(db, scene_id, current_user.id):
        raise HTTPException(status_code=404, detail="Scene not found")


# ============================================
# Entities (Knowledge Graph Nodes)
# ============================================

@router.get("/{project_id}/entities", response_model=List[EntityResponse])
def list_entities(
    project_id: int,
    kind: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_entities(db, project_id, current_user.id, kind=kind)


@router.post("/{project_id}/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(
    project_id: int,
    data: EntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ent = crud.create_entity(db, project_id, current_user.id, data)
    if not ent:
        raise HTTPException(status_code=404, detail="Project not found")
    return ent


@router.get("/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ent = crud.get_entity(db, entity_id, current_user.id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    return ent


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
def update_entity(
    entity_id: int,
    data: EntityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ent = crud.update_entity(db, entity_id, current_user.id, data)
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    return ent


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_entity(db, entity_id, current_user.id):
        raise HTTPException(status_code=404, detail="Entity not found")


# ============================================
# Edges (Knowledge Graph Relationships)
# ============================================

@router.get("/{project_id}/edges", response_model=List[EdgeResponse])
def list_edges(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_edges(db, project_id, current_user.id)


@router.post("/{project_id}/edges", response_model=EdgeResponse, status_code=status.HTTP_201_CREATED)
def create_edge(
    project_id: int,
    data: EdgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    edge = crud.create_edge(db, project_id, current_user.id, data)
    if not edge:
        raise HTTPException(status_code=404, detail="Project or entities not found")
    return edge


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edge(
    edge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_edge(db, edge_id, current_user.id):
        raise HTTPException(status_code=404, detail="Edge not found")


# ============================================
# Arcs
# ============================================

@router.get("/{project_id}/arcs", response_model=List[ArcResponse])
def list_arcs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_arcs(db, project_id, current_user.id)


@router.get("/{project_id}/arcs/full", response_model=List[ArcWithBeats])
def list_arcs_with_beats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List arcs with nested beats."""
    return crud.list_arcs(db, project_id, current_user.id)


@router.post("/{project_id}/arcs", response_model=ArcResponse, status_code=status.HTTP_201_CREATED)
def create_arc(
    project_id: int,
    data: ArcCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    arc = crud.create_arc(db, project_id, current_user.id, data)
    if not arc:
        raise HTTPException(status_code=404, detail="Project not found")
    return arc


@router.patch("/arcs/{arc_id}", response_model=ArcResponse)
def update_arc(
    arc_id: int,
    data: ArcUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    arc = crud.update_arc(db, arc_id, current_user.id, data)
    if not arc:
        raise HTTPException(status_code=404, detail="Arc not found")
    return arc


@router.delete("/arcs/{arc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_arc(
    arc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_arc(db, arc_id, current_user.id):
        raise HTTPException(status_code=404, detail="Arc not found")


# ============================================
# Beats
# ============================================

@router.get("/arcs/{arc_id}/beats", response_model=List[BeatResponse])
def list_beats(
    arc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_beats(db, arc_id, current_user.id)


@router.post("/arcs/{arc_id}/beats", response_model=BeatResponse, status_code=status.HTTP_201_CREATED)
def create_beat(
    arc_id: int,
    data: BeatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    beat = crud.create_beat(db, arc_id, current_user.id, data)
    if not beat:
        raise HTTPException(status_code=404, detail="Arc not found")
    return beat


@router.patch("/beats/{beat_id}", response_model=BeatResponse)
def update_beat(
    beat_id: int,
    data: BeatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    beat = crud.update_beat(db, beat_id, current_user.id, data)
    if not beat:
        raise HTTPException(status_code=404, detail="Beat not found")
    return beat


@router.delete("/beats/{beat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beat(
    beat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_beat(db, beat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Beat not found")


# ============================================
# Style Profiles
# ============================================

@router.get("/{project_id}/styles", response_model=List[StyleProfileResponse])
def list_style_profiles(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_style_profiles(db, project_id, current_user.id)


@router.post("/{project_id}/styles", response_model=StyleProfileResponse, status_code=status.HTTP_201_CREATED)
def create_style_profile(
    project_id: int,
    data: StyleProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sp = crud.create_style_profile(db, project_id, current_user.id, data)
    if not sp:
        raise HTTPException(status_code=404, detail="Project not found")
    return sp


@router.patch("/styles/{profile_id}", response_model=StyleProfileResponse)
def update_style_profile(
    profile_id: int,
    data: StyleProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sp = crud.update_style_profile(db, profile_id, current_user.id, data)
    if not sp:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return sp


@router.delete("/styles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_style_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_style_profile(db, profile_id, current_user.id):
        raise HTTPException(status_code=404, detail="Style profile not found")


# ============================================
# Assets
# ============================================

@router.get("/assets", response_model=List[AssetResponse])
def list_assets(
    project_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_assets(db, current_user.id, project_id=project_id, asset_type=asset_type)


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    data: AssetCreate,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.create_asset(db, current_user.id, project_id, data)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_asset(db, asset_id, current_user.id):
        raise HTTPException(status_code=404, detail="Asset not found")


# ============================================
# Factions
# ============================================

@router.get("/{project_id}/factions", response_model=List[FactionResponse])
def list_factions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_factions(db, project_id, current_user.id)


@router.post("/{project_id}/factions", response_model=FactionResponse, status_code=status.HTTP_201_CREATED)
def create_faction(
    project_id: int,
    data: FactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = crud.create_faction(db, project_id, current_user.id, data)
    if not f:
        raise HTTPException(status_code=404, detail="Project not found")
    return f


@router.patch("/factions/{faction_id}", response_model=FactionResponse)
def update_faction(
    faction_id: int,
    data: FactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = crud.update_faction(db, faction_id, current_user.id, data)
    if not f:
        raise HTTPException(status_code=404, detail="Faction not found")
    return f


@router.delete("/factions/{faction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faction(
    faction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_faction(db, faction_id, current_user.id):
        raise HTTPException(status_code=404, detail="Faction not found")


# ============================================
# Consistency Alerts
# ============================================

@router.get("/{project_id}/alerts", response_model=List[ConsistencyAlertResponse])
def list_alerts(
    project_id: int,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_alerts(db, project_id, current_user.id, resolved=resolved)


@router.post("/{project_id}/alerts", response_model=ConsistencyAlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    project_id: int,
    data: ConsistencyAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = crud.create_alert(db, project_id, current_user.id, data)
    if not alert:
        raise HTTPException(status_code=404, detail="Project not found")
    return alert


@router.patch("/alerts/{alert_id}", response_model=ConsistencyAlertResponse)
def update_alert(
    alert_id: int,
    data: ConsistencyAlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = crud.update_alert(db, alert_id, current_user.id, data)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ============================================
# Covers
# ============================================

@router.get("/{project_id}/covers", response_model=List[CoverResponse])
def list_covers(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_covers(db, project_id, current_user.id)


@router.post("/{project_id}/covers", response_model=CoverResponse, status_code=status.HTTP_201_CREATED)
def create_cover(
    project_id: int,
    data: CoverCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = crud.create_cover(db, project_id, current_user.id, data)
    if not c:
        raise HTTPException(status_code=404, detail="Project not found")
    return c


@router.patch("/covers/{cover_id}", response_model=CoverResponse)
def update_cover(
    cover_id: int,
    data: CoverUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = crud.update_cover(db, cover_id, current_user.id, data)
    if not c:
        raise HTTPException(status_code=404, detail="Cover not found")
    return c


@router.delete("/covers/{cover_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover(
    cover_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_cover(db, cover_id, current_user.id):
        raise HTTPException(status_code=404, detail="Cover not found")


# ============================================
# Map — Nodes
# ============================================

@router.get("/{project_id}/map/nodes", response_model=List[MapNodeResponse])
def list_map_nodes(
    project_id: int,
    era: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_map_nodes(db, project_id, current_user.id, era=era)


@router.post("/{project_id}/map/nodes", response_model=MapNodeResponse, status_code=status.HTTP_201_CREATED)
def create_map_node(
    project_id: int,
    data: MapNodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = crud.create_map_node(db, project_id, current_user.id, data)
    if not n:
        raise HTTPException(status_code=404, detail="Project not found")
    return n


@router.patch("/map/nodes/{node_id}", response_model=MapNodeResponse)
def update_map_node(
    node_id: int,
    data: MapNodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = crud.update_map_node(db, node_id, current_user.id, data)
    if not n:
        raise HTTPException(status_code=404, detail="Map node not found")
    return n


@router.delete("/map/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_map_node(db, node_id, current_user.id):
        raise HTTPException(status_code=404, detail="Map node not found")


# ============================================
# Map — Edges
# ============================================

@router.get("/{project_id}/map/edges", response_model=List[MapEdgeResponse])
def list_map_edges(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_map_edges(db, project_id, current_user.id)


@router.post("/{project_id}/map/edges", response_model=MapEdgeResponse, status_code=status.HTTP_201_CREATED)
def create_map_edge(
    project_id: int,
    data: MapEdgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    me = crud.create_map_edge(db, project_id, current_user.id, data)
    if not me:
        raise HTTPException(status_code=404, detail="Project or nodes not found")
    return me


@router.delete("/map/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map_edge(
    edge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_map_edge(db, edge_id, current_user.id):
        raise HTTPException(status_code=404, detail="Map edge not found")


# ============================================
# Map — Edge Modifiers
# ============================================

@router.get("/map/edges/{edge_id}/modifiers", response_model=List[MapEdgeModifierResponse])
def list_map_edge_modifiers(
    edge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_map_edge_modifiers(db, edge_id, current_user.id)


@router.post("/map/edges/{edge_id}/modifiers", response_model=MapEdgeModifierResponse, status_code=status.HTTP_201_CREATED)
def create_map_edge_modifier(
    edge_id: int,
    data: MapEdgeModifierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mod = crud.create_map_edge_modifier(db, edge_id, current_user.id, data)
    if not mod:
        raise HTTPException(status_code=404, detail="Map edge not found")
    return mod


@router.delete("/map/modifiers/{modifier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map_edge_modifier(
    modifier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_map_edge_modifier(db, modifier_id, current_user.id):
        raise HTTPException(status_code=404, detail="Modifier not found")


# ============================================
# Map — Regions
# ============================================

@router.get("/{project_id}/map/regions", response_model=List[MapRegionResponse])
def list_map_regions(
    project_id: int,
    era: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_map_regions(db, project_id, current_user.id, era=era)


@router.post("/{project_id}/map/regions", response_model=MapRegionResponse, status_code=status.HTTP_201_CREATED)
def create_map_region(
    project_id: int,
    data: MapRegionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = crud.create_map_region(db, project_id, current_user.id, data)
    if not r:
        raise HTTPException(status_code=404, detail="Project not found")
    return r


@router.delete("/map/regions/{region_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map_region(
    region_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_map_region(db, region_id, current_user.id):
        raise HTTPException(status_code=404, detail="Region not found")


# ============================================
# Map — Lore Pins
# ============================================

@router.get("/{project_id}/map/pins", response_model=List[LorePinResponse])
def list_lore_pins(
    project_id: int,
    era: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_lore_pins(db, project_id, current_user.id, era=era)


@router.post("/{project_id}/map/pins", response_model=LorePinResponse, status_code=status.HTTP_201_CREATED)
def create_lore_pin(
    project_id: int,
    data: LorePinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pin = crud.create_lore_pin(db, project_id, current_user.id, data)
    if not pin:
        raise HTTPException(status_code=404, detail="Project not found")
    return pin


@router.patch("/map/pins/{pin_id}", response_model=LorePinResponse)
def update_lore_pin(
    pin_id: int,
    data: LorePinUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pin = crud.update_lore_pin(db, pin_id, current_user.id, data)
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found")
    return pin


@router.delete("/map/pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lore_pin(
    pin_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_lore_pin(db, pin_id, current_user.id):
        raise HTTPException(status_code=404, detail="Pin not found")


# ============================================
# Map — Character Knowledge (Fog of Knowledge)
# ============================================

@router.get("/{project_id}/map/knowledge", response_model=List[CharacterKnowledgeResponse])
def list_character_knowledge(
    project_id: int,
    entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_character_knowledge(db, project_id, current_user.id, entity_id=entity_id)


@router.post("/{project_id}/map/knowledge", response_model=CharacterKnowledgeResponse, status_code=status.HTTP_201_CREATED)
def create_character_knowledge(
    project_id: int,
    data: CharacterKnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ck = crud.create_character_knowledge(db, project_id, current_user.id, data)
    if not ck:
        raise HTTPException(status_code=404, detail="Project or entity not found")
    return ck


@router.delete("/map/knowledge/{ck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character_knowledge(
    ck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_character_knowledge(db, ck_id, current_user.id):
        raise HTTPException(status_code=404, detail="Knowledge record not found")


# ============================================
# Map — Journeys
# ============================================

@router.get("/{project_id}/map/journeys", response_model=List[JourneyResponse])
def list_journeys(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_journeys(db, project_id, current_user.id)


@router.post("/{project_id}/map/journeys", response_model=JourneyResponse, status_code=status.HTTP_201_CREATED)
def create_journey(
    project_id: int,
    data: JourneyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    j = crud.create_journey(db, project_id, current_user.id, data)
    if not j:
        raise HTTPException(status_code=404, detail="Project or nodes not found")
    return j


@router.delete("/map/journeys/{journey_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud.delete_journey(db, journey_id, current_user.id):
        raise HTTPException(status_code=404, detail="Journey not found")

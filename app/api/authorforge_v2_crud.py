"""
CRUD operations for AuthorForge V2 tables.

All queries enforce user ownership through the project FK chain.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func as sql_func
from typing import List, Optional
from datetime import datetime

from app.models.authorforge_models import Project
from app.models.authorforge_v2_models import (
    Chapter, Scene, LoreEntity, LoreEdge,
    Arc, Beat, StyleProfile, Asset, Faction,
    ConsistencyAlert, Cover,
    MapNode, MapEdge, MapEdgeModifier, MapRegion,
    LorePin, CharacterKnowledge, Journey,
)
from app.models.authorforge_v2_schemas import (
    ChapterCreate, ChapterUpdate,
    SceneCreate, SceneUpdate,
    EntityCreate, EntityUpdate,
    EdgeCreate,
    ArcCreate, ArcUpdate,
    BeatCreate, BeatUpdate,
    StyleProfileCreate, StyleProfileUpdate,
    AssetCreate,
    FactionCreate, FactionUpdate,
    ConsistencyAlertCreate, ConsistencyAlertUpdate,
    CoverCreate, CoverUpdate,
    MapNodeCreate, MapNodeUpdate,
    MapEdgeCreate,
    MapEdgeModifierCreate,
    MapRegionCreate,
    LorePinCreate, LorePinUpdate,
    CharacterKnowledgeCreate,
    JourneyCreate,
)


# ============================================
# Helpers
# ============================================

def _verify_project(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """Verify the user owns the project. Returns the project or None."""
    return db.query(Project).filter(
        and_(Project.id == project_id, Project.user_id == user_id)
    ).first()


def _update_chapter_word_count(db: Session, chapter_id: int) -> None:
    """Recalculate chapter word_count from its scenes."""
    total = db.query(sql_func.coalesce(sql_func.sum(Scene.word_count), 0)).filter(
        Scene.chapter_id == chapter_id
    ).scalar()
    db.query(Chapter).filter(Chapter.id == chapter_id).update(
        {"word_count": total, "updated_at": datetime.utcnow()}
    )


# ============================================
# Chapters
# ============================================

def list_chapters(db: Session, project_id: int, user_id: int) -> List[Chapter]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(Chapter).filter(
        Chapter.project_id == project_id
    ).order_by(Chapter.sort_order).all()


def get_chapter(db: Session, chapter_id: int, user_id: int) -> Optional[Chapter]:
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch or not _verify_project(db, ch.project_id, user_id):
        return None
    return ch


def create_chapter(db: Session, project_id: int, user_id: int, data: ChapterCreate) -> Optional[Chapter]:
    if not _verify_project(db, project_id, user_id):
        return None
    ch = Chapter(project_id=project_id, **data.model_dump())
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def update_chapter(db: Session, chapter_id: int, user_id: int, data: ChapterUpdate) -> Optional[Chapter]:
    ch = get_chapter(db, chapter_id, user_id)
    if not ch:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ch, field, value)
    ch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ch)
    return ch


def delete_chapter(db: Session, chapter_id: int, user_id: int) -> bool:
    ch = get_chapter(db, chapter_id, user_id)
    if not ch:
        return False
    db.delete(ch)
    db.commit()
    return True


# ============================================
# Scenes
# ============================================

def _count_words(html: str) -> int:
    """Rough word count from HTML content."""
    import re
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(text.split())


def list_scenes(db: Session, chapter_id: int, user_id: int) -> List[Scene]:
    ch = get_chapter(db, chapter_id, user_id)
    if not ch:
        return []
    return db.query(Scene).filter(
        Scene.chapter_id == chapter_id
    ).order_by(Scene.sort_order).all()


def get_scene(db: Session, scene_id: int, user_id: int) -> Optional[Scene]:
    sc = db.query(Scene).filter(Scene.id == scene_id).first()
    if not sc:
        return None
    ch = db.query(Chapter).filter(Chapter.id == sc.chapter_id).first()
    if not ch or not _verify_project(db, ch.project_id, user_id):
        return None
    return sc


def create_scene(db: Session, chapter_id: int, user_id: int, data: SceneCreate) -> Optional[Scene]:
    ch = get_chapter(db, chapter_id, user_id)
    if not ch:
        return None
    word_count = _count_words(data.content_html)
    sc = Scene(chapter_id=chapter_id, word_count=word_count, **data.model_dump())
    db.add(sc)
    db.commit()
    db.refresh(sc)
    _update_chapter_word_count(db, chapter_id)
    db.commit()
    return sc


def update_scene(db: Session, scene_id: int, user_id: int, data: SceneUpdate) -> Optional[Scene]:
    sc = get_scene(db, scene_id, user_id)
    if not sc:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if "content_html" in update_data:
        update_data["word_count"] = _count_words(update_data["content_html"])
    for field, value in update_data.items():
        setattr(sc, field, value)
    sc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sc)
    _update_chapter_word_count(db, sc.chapter_id)
    db.commit()
    return sc


def delete_scene(db: Session, scene_id: int, user_id: int) -> bool:
    sc = get_scene(db, scene_id, user_id)
    if not sc:
        return False
    chapter_id = sc.chapter_id
    db.delete(sc)
    db.commit()
    _update_chapter_word_count(db, chapter_id)
    db.commit()
    return True


# ============================================
# Entities (Knowledge Graph Nodes)
# ============================================

def list_entities(db: Session, project_id: int, user_id: int, kind: Optional[str] = None) -> List[LoreEntity]:
    if not _verify_project(db, project_id, user_id):
        return []
    q = db.query(LoreEntity).filter(LoreEntity.project_id == project_id)
    if kind:
        q = q.filter(LoreEntity.kind == kind)
    return q.order_by(LoreEntity.name).all()


def get_entity(db: Session, entity_id: int, user_id: int) -> Optional[LoreEntity]:
    ent = db.query(LoreEntity).filter(LoreEntity.id == entity_id).first()
    if not ent or not _verify_project(db, ent.project_id, user_id):
        return None
    return ent


def create_entity(db: Session, project_id: int, user_id: int, data: EntityCreate) -> Optional[LoreEntity]:
    if not _verify_project(db, project_id, user_id):
        return None
    ent = LoreEntity(project_id=project_id, **data.model_dump())
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ent


def update_entity(db: Session, entity_id: int, user_id: int, data: EntityUpdate) -> Optional[LoreEntity]:
    ent = get_entity(db, entity_id, user_id)
    if not ent:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ent, field, value)
    ent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ent)
    return ent


def delete_entity(db: Session, entity_id: int, user_id: int) -> bool:
    ent = get_entity(db, entity_id, user_id)
    if not ent:
        return False
    db.delete(ent)
    db.commit()
    return True


# ============================================
# Edges (Knowledge Graph Relationships)
# ============================================

def list_edges(db: Session, project_id: int, user_id: int) -> List[LoreEdge]:
    if not _verify_project(db, project_id, user_id):
        return []
    # Edges belong to a project through their source entity
    entity_ids = db.query(LoreEntity.id).filter(LoreEntity.project_id == project_id).subquery()
    return db.query(LoreEdge).filter(
        LoreEdge.source_id.in_(entity_ids)
    ).all()


def create_edge(db: Session, project_id: int, user_id: int, data: EdgeCreate) -> Optional[LoreEdge]:
    if not _verify_project(db, project_id, user_id):
        return None
    # Verify both entities belong to this project
    source = db.query(LoreEntity).filter(
        and_(LoreEntity.id == data.source_id, LoreEntity.project_id == project_id)
    ).first()
    target = db.query(LoreEntity).filter(
        and_(LoreEntity.id == data.target_id, LoreEntity.project_id == project_id)
    ).first()
    if not source or not target:
        return None
    edge = LoreEdge(**data.model_dump())
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def delete_edge(db: Session, edge_id: int, user_id: int) -> bool:
    edge = db.query(LoreEdge).filter(LoreEdge.id == edge_id).first()
    if not edge:
        return False
    source = db.query(LoreEntity).filter(LoreEntity.id == edge.source_id).first()
    if not source or not _verify_project(db, source.project_id, user_id):
        return False
    db.delete(edge)
    db.commit()
    return True


# ============================================
# Arcs
# ============================================

def list_arcs(db: Session, project_id: int, user_id: int) -> List[Arc]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(Arc).filter(Arc.project_id == project_id).order_by(Arc.name).all()


def get_arc(db: Session, arc_id: int, user_id: int) -> Optional[Arc]:
    arc = db.query(Arc).filter(Arc.id == arc_id).first()
    if not arc or not _verify_project(db, arc.project_id, user_id):
        return None
    return arc


def create_arc(db: Session, project_id: int, user_id: int, data: ArcCreate) -> Optional[Arc]:
    if not _verify_project(db, project_id, user_id):
        return None
    arc = Arc(project_id=project_id, **data.model_dump())
    db.add(arc)
    db.commit()
    db.refresh(arc)
    return arc


def update_arc(db: Session, arc_id: int, user_id: int, data: ArcUpdate) -> Optional[Arc]:
    arc = get_arc(db, arc_id, user_id)
    if not arc:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(arc, field, value)
    arc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(arc)
    return arc


def delete_arc(db: Session, arc_id: int, user_id: int) -> bool:
    arc = get_arc(db, arc_id, user_id)
    if not arc:
        return False
    db.delete(arc)
    db.commit()
    return True


# ============================================
# Beats
# ============================================

def list_beats(db: Session, arc_id: int, user_id: int) -> List[Beat]:
    arc = get_arc(db, arc_id, user_id)
    if not arc:
        return []
    return db.query(Beat).filter(Beat.arc_id == arc_id).order_by(Beat.sort_order).all()


def create_beat(db: Session, arc_id: int, user_id: int, data: BeatCreate) -> Optional[Beat]:
    arc = get_arc(db, arc_id, user_id)
    if not arc:
        return None
    beat = Beat(arc_id=arc_id, **data.model_dump())
    db.add(beat)
    db.commit()
    db.refresh(beat)
    return beat


def update_beat(db: Session, beat_id: int, user_id: int, data: BeatUpdate) -> Optional[Beat]:
    beat = db.query(Beat).filter(Beat.id == beat_id).first()
    if not beat:
        return None
    arc = get_arc(db, beat.arc_id, user_id)
    if not arc:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(beat, field, value)
    beat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(beat)
    return beat


def delete_beat(db: Session, beat_id: int, user_id: int) -> bool:
    beat = db.query(Beat).filter(Beat.id == beat_id).first()
    if not beat:
        return False
    arc = get_arc(db, beat.arc_id, user_id)
    if not arc:
        return False
    db.delete(beat)
    db.commit()
    return True


# ============================================
# Style Profiles
# ============================================

def list_style_profiles(db: Session, project_id: int, user_id: int) -> List[StyleProfile]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(StyleProfile).filter(StyleProfile.project_id == project_id).all()


def get_style_profile(db: Session, profile_id: int, user_id: int) -> Optional[StyleProfile]:
    sp = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
    if not sp:
        return None
    if sp.project_id and not _verify_project(db, sp.project_id, user_id):
        return None
    return sp


def create_style_profile(
    db: Session, project_id: int, user_id: int, data: StyleProfileCreate
) -> Optional[StyleProfile]:
    if not _verify_project(db, project_id, user_id):
        return None
    sp = StyleProfile(project_id=project_id, **data.model_dump())
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp


def update_style_profile(
    db: Session, profile_id: int, user_id: int, data: StyleProfileUpdate
) -> Optional[StyleProfile]:
    sp = get_style_profile(db, profile_id, user_id)
    if not sp:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sp, field, value)
    sp.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sp)
    return sp


def delete_style_profile(db: Session, profile_id: int, user_id: int) -> bool:
    sp = get_style_profile(db, profile_id, user_id)
    if not sp:
        return False
    db.delete(sp)
    db.commit()
    return True


# ============================================
# Assets
# ============================================

def list_assets(
    db: Session, user_id: int, project_id: Optional[int] = None, asset_type: Optional[str] = None
) -> List[Asset]:
    q = db.query(Asset).filter(Asset.user_id == user_id)
    if project_id:
        q = q.filter(Asset.project_id == project_id)
    if asset_type:
        q = q.filter(Asset.asset_type == asset_type)
    return q.order_by(Asset.created_at.desc()).all()


def create_asset(
    db: Session, user_id: int, project_id: Optional[int], data: AssetCreate
) -> Asset:
    asset = Asset(user_id=user_id, project_id=project_id, **data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, user_id: int) -> bool:
    asset = db.query(Asset).filter(
        and_(Asset.id == asset_id, Asset.user_id == user_id)
    ).first()
    if not asset:
        return False
    db.delete(asset)
    db.commit()
    return True


# ============================================
# Factions
# ============================================

def list_factions(db: Session, project_id: int, user_id: int) -> List[Faction]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(Faction).filter(Faction.project_id == project_id).order_by(Faction.name).all()


def get_faction(db: Session, faction_id: int, user_id: int) -> Optional[Faction]:
    f = db.query(Faction).filter(Faction.id == faction_id).first()
    if not f or not _verify_project(db, f.project_id, user_id):
        return None
    return f


def create_faction(db: Session, project_id: int, user_id: int, data: FactionCreate) -> Optional[Faction]:
    if not _verify_project(db, project_id, user_id):
        return None
    f = Faction(project_id=project_id, **data.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def update_faction(db: Session, faction_id: int, user_id: int, data: FactionUpdate) -> Optional[Faction]:
    f = get_faction(db, faction_id, user_id)
    if not f:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(f, field, value)
    f.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(f)
    return f


def delete_faction(db: Session, faction_id: int, user_id: int) -> bool:
    f = get_faction(db, faction_id, user_id)
    if not f:
        return False
    db.delete(f)
    db.commit()
    return True


# ============================================
# Consistency Alerts
# ============================================

def list_alerts(
    db: Session, project_id: int, user_id: int, resolved: Optional[bool] = None
) -> List[ConsistencyAlert]:
    if not _verify_project(db, project_id, user_id):
        return []
    q = db.query(ConsistencyAlert).filter(ConsistencyAlert.project_id == project_id)
    if resolved is not None:
        q = q.filter(ConsistencyAlert.resolved == resolved)
    return q.order_by(ConsistencyAlert.tier.desc(), ConsistencyAlert.created_at.desc()).all()


def create_alert(
    db: Session, project_id: int, user_id: int, data: ConsistencyAlertCreate
) -> Optional[ConsistencyAlert]:
    if not _verify_project(db, project_id, user_id):
        return None
    alert = ConsistencyAlert(project_id=project_id, **data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update_alert(
    db: Session, alert_id: int, user_id: int, data: ConsistencyAlertUpdate
) -> Optional[ConsistencyAlert]:
    alert = db.query(ConsistencyAlert).filter(ConsistencyAlert.id == alert_id).first()
    if not alert or not _verify_project(db, alert.project_id, user_id):
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("resolved") is True and not alert.resolved:
        update_data["resolved_at"] = datetime.utcnow()
    for field, value in update_data.items():
        setattr(alert, field, value)
    db.commit()
    db.refresh(alert)
    return alert


# ============================================
# Covers
# ============================================

def list_covers(db: Session, project_id: int, user_id: int) -> List[Cover]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(Cover).filter(Cover.project_id == project_id).all()


def get_cover(db: Session, cover_id: int, user_id: int) -> Optional[Cover]:
    c = db.query(Cover).filter(Cover.id == cover_id).first()
    if not c or not _verify_project(db, c.project_id, user_id):
        return None
    return c


def create_cover(db: Session, project_id: int, user_id: int, data: CoverCreate) -> Optional[Cover]:
    if not _verify_project(db, project_id, user_id):
        return None
    c = Cover(project_id=project_id, **data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_cover(db: Session, cover_id: int, user_id: int, data: CoverUpdate) -> Optional[Cover]:
    c = get_cover(db, cover_id, user_id)
    if not c:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c


def delete_cover(db: Session, cover_id: int, user_id: int) -> bool:
    c = get_cover(db, cover_id, user_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


# ============================================
# Map Nodes
# ============================================

def list_map_nodes(db: Session, project_id: int, user_id: int, era: Optional[int] = None) -> List[MapNode]:
    if not _verify_project(db, project_id, user_id):
        return []
    q = db.query(MapNode).filter(MapNode.project_id == project_id)
    if era is not None:
        q = q.filter(
            (MapNode.era_from.is_(None) | (MapNode.era_from <= era)),
            (MapNode.era_to.is_(None) | (MapNode.era_to >= era)),
        )
    return q.all()


def get_map_node(db: Session, node_id: int, user_id: int) -> Optional[MapNode]:
    n = db.query(MapNode).filter(MapNode.id == node_id).first()
    if not n or not _verify_project(db, n.project_id, user_id):
        return None
    return n


def create_map_node(db: Session, project_id: int, user_id: int, data: MapNodeCreate) -> Optional[MapNode]:
    if not _verify_project(db, project_id, user_id):
        return None
    n = MapNode(project_id=project_id, **data.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def update_map_node(db: Session, node_id: int, user_id: int, data: MapNodeUpdate) -> Optional[MapNode]:
    n = get_map_node(db, node_id, user_id)
    if not n:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(n, field, value)
    n.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(n)
    return n


def delete_map_node(db: Session, node_id: int, user_id: int) -> bool:
    n = get_map_node(db, node_id, user_id)
    if not n:
        return False
    db.delete(n)
    db.commit()
    return True


# ============================================
# Map Edges
# ============================================

def list_map_edges(db: Session, project_id: int, user_id: int) -> List[MapEdge]:
    if not _verify_project(db, project_id, user_id):
        return []
    node_ids = db.query(MapNode.id).filter(MapNode.project_id == project_id).subquery()
    return db.query(MapEdge).filter(MapEdge.from_id.in_(node_ids)).all()


def create_map_edge(db: Session, project_id: int, user_id: int, data: MapEdgeCreate) -> Optional[MapEdge]:
    if not _verify_project(db, project_id, user_id):
        return None
    # Verify both nodes belong to this project
    from_node = db.query(MapNode).filter(
        and_(MapNode.id == data.from_id, MapNode.project_id == project_id)
    ).first()
    to_node = db.query(MapNode).filter(
        and_(MapNode.id == data.to_id, MapNode.project_id == project_id)
    ).first()
    if not from_node or not to_node:
        return None
    me = MapEdge(**data.model_dump())
    db.add(me)
    db.commit()
    db.refresh(me)
    return me


def delete_map_edge(db: Session, edge_id: int, user_id: int) -> bool:
    me = db.query(MapEdge).filter(MapEdge.id == edge_id).first()
    if not me:
        return False
    from_node = db.query(MapNode).filter(MapNode.id == me.from_id).first()
    if not from_node or not _verify_project(db, from_node.project_id, user_id):
        return False
    db.delete(me)
    db.commit()
    return True


# ============================================
# Map Edge Modifiers
# ============================================

def list_map_edge_modifiers(db: Session, edge_id: int, user_id: int) -> List[MapEdgeModifier]:
    me = db.query(MapEdge).filter(MapEdge.id == edge_id).first()
    if not me:
        return []
    from_node = db.query(MapNode).filter(MapNode.id == me.from_id).first()
    if not from_node or not _verify_project(db, from_node.project_id, user_id):
        return []
    return db.query(MapEdgeModifier).filter(MapEdgeModifier.edge_id == edge_id).order_by(MapEdgeModifier.priority).all()


def create_map_edge_modifier(
    db: Session, edge_id: int, user_id: int, data: MapEdgeModifierCreate
) -> Optional[MapEdgeModifier]:
    me = db.query(MapEdge).filter(MapEdge.id == edge_id).first()
    if not me:
        return None
    from_node = db.query(MapNode).filter(MapNode.id == me.from_id).first()
    if not from_node or not _verify_project(db, from_node.project_id, user_id):
        return None
    mod = MapEdgeModifier(edge_id=edge_id, **data.model_dump())
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return mod


def delete_map_edge_modifier(db: Session, modifier_id: int, user_id: int) -> bool:
    mod = db.query(MapEdgeModifier).filter(MapEdgeModifier.id == modifier_id).first()
    if not mod:
        return False
    me = db.query(MapEdge).filter(MapEdge.id == mod.edge_id).first()
    if not me:
        return False
    from_node = db.query(MapNode).filter(MapNode.id == me.from_id).first()
    if not from_node or not _verify_project(db, from_node.project_id, user_id):
        return False
    db.delete(mod)
    db.commit()
    return True


# ============================================
# Map Regions
# ============================================

def list_map_regions(db: Session, project_id: int, user_id: int, era: Optional[int] = None) -> List[MapRegion]:
    if not _verify_project(db, project_id, user_id):
        return []
    q = db.query(MapRegion).filter(MapRegion.project_id == project_id)
    if era is not None:
        q = q.filter(
            (MapRegion.era_from.is_(None) | (MapRegion.era_from <= era)),
            (MapRegion.era_to.is_(None) | (MapRegion.era_to >= era)),
        )
    return q.all()


def create_map_region(db: Session, project_id: int, user_id: int, data: MapRegionCreate) -> Optional[MapRegion]:
    if not _verify_project(db, project_id, user_id):
        return None
    r = MapRegion(project_id=project_id, **data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def delete_map_region(db: Session, region_id: int, user_id: int) -> bool:
    r = db.query(MapRegion).filter(MapRegion.id == region_id).first()
    if not r or not _verify_project(db, r.project_id, user_id):
        return False
    db.delete(r)
    db.commit()
    return True


# ============================================
# Lore Pins
# ============================================

def list_lore_pins(db: Session, project_id: int, user_id: int, era: Optional[int] = None) -> List[LorePin]:
    if not _verify_project(db, project_id, user_id):
        return []
    q = db.query(LorePin).filter(LorePin.project_id == project_id)
    if era is not None:
        q = q.filter((LorePin.era.is_(None)) | (LorePin.era == era))
    return q.all()


def create_lore_pin(db: Session, project_id: int, user_id: int, data: LorePinCreate) -> Optional[LorePin]:
    if not _verify_project(db, project_id, user_id):
        return None
    pin = LorePin(project_id=project_id, **data.model_dump())
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return pin


def update_lore_pin(db: Session, pin_id: int, user_id: int, data: LorePinUpdate) -> Optional[LorePin]:
    pin = db.query(LorePin).filter(LorePin.id == pin_id).first()
    if not pin or not _verify_project(db, pin.project_id, user_id):
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pin, field, value)
    db.commit()
    db.refresh(pin)
    return pin


def delete_lore_pin(db: Session, pin_id: int, user_id: int) -> bool:
    pin = db.query(LorePin).filter(LorePin.id == pin_id).first()
    if not pin or not _verify_project(db, pin.project_id, user_id):
        return False
    db.delete(pin)
    db.commit()
    return True


# ============================================
# Character Knowledge
# ============================================

def list_character_knowledge(
    db: Session, project_id: int, user_id: int, entity_id: Optional[int] = None
) -> List[CharacterKnowledge]:
    if not _verify_project(db, project_id, user_id):
        return []
    entity_ids = db.query(LoreEntity.id).filter(LoreEntity.project_id == project_id).subquery()
    q = db.query(CharacterKnowledge).filter(CharacterKnowledge.entity_id.in_(entity_ids))
    if entity_id:
        q = q.filter(CharacterKnowledge.entity_id == entity_id)
    return q.all()


def create_character_knowledge(
    db: Session, project_id: int, user_id: int, data: CharacterKnowledgeCreate
) -> Optional[CharacterKnowledge]:
    if not _verify_project(db, project_id, user_id):
        return None
    # Verify entity belongs to project
    ent = db.query(LoreEntity).filter(
        and_(LoreEntity.id == data.entity_id, LoreEntity.project_id == project_id)
    ).first()
    if not ent:
        return None
    ck = CharacterKnowledge(**data.model_dump())
    db.add(ck)
    db.commit()
    db.refresh(ck)
    return ck


def delete_character_knowledge(db: Session, ck_id: int, user_id: int) -> bool:
    ck = db.query(CharacterKnowledge).filter(CharacterKnowledge.id == ck_id).first()
    if not ck:
        return False
    ent = db.query(LoreEntity).filter(LoreEntity.id == ck.entity_id).first()
    if not ent or not _verify_project(db, ent.project_id, user_id):
        return False
    db.delete(ck)
    db.commit()
    return True


# ============================================
# Journeys
# ============================================

def list_journeys(db: Session, project_id: int, user_id: int) -> List[Journey]:
    if not _verify_project(db, project_id, user_id):
        return []
    return db.query(Journey).filter(Journey.project_id == project_id).all()


def create_journey(db: Session, project_id: int, user_id: int, data: JourneyCreate) -> Optional[Journey]:
    if not _verify_project(db, project_id, user_id):
        return None
    # Verify both nodes belong to this project
    from_node = db.query(MapNode).filter(
        and_(MapNode.id == data.from_id, MapNode.project_id == project_id)
    ).first()
    to_node = db.query(MapNode).filter(
        and_(MapNode.id == data.to_id, MapNode.project_id == project_id)
    ).first()
    if not from_node or not to_node:
        return None
    j = Journey(project_id=project_id, **data.model_dump())
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def delete_journey(db: Session, journey_id: int, user_id: int) -> bool:
    j = db.query(Journey).filter(Journey.id == journey_id).first()
    if not j or not _verify_project(db, j.project_id, user_id):
        return False
    db.delete(j)
    db.commit()
    return True

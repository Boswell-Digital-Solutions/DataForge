#!/usr/bin/env python3
"""Read-only metadata audit for possible legacy AuthorForge records.

The audit reads only table existence, row counts, and primary-key values from a
fixed allow-list.  It never selects, logs, exports, mutates, or deletes content
columns.  Output is intended for human review before any separate remediation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Allow direct invocation (python scripts/audit_authorforge_boundary.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATABASE_URL_IS_DEFAULT  # noqa: E402
from app.database import engine  # noqa: E402


AUTHORFORGE_LEGACY_TABLES = {
    "projects": "projects",
    "project_genres": "project_genres",
    "manuscripts": "manuscripts",
    "characters": "characters",
    "locations": "locations",
    "story_arcs": "story_arcs",
    "brainstorm_sessions": "brainstorm_sessions",
    "chapters": "chapters",
    "scenes": "scenes",
    "lore_entities": "lore_entities",
    "lore_edges": "lore_edges",
    "arcs": "arcs",
    "beats": "beats",
    "style_profiles": "style_profiles",
    "assets": "assets",
    "asset_collections": "asset_collections",
    "collection_assets": "collection_assets",
    "factions": "factions",
    "consistency_alerts": "consistency_alerts",
    "covers": "covers",
    "map_nodes": "map_nodes",
    "map_edges": "map_edges",
    "map_edge_modifiers": "map_edge_modifiers",
    "map_regions": "map_regions",
    "lore_pins": "lore_pins",
    "character_knowledge": "character_knowledge",
    "journeys": "journeys",
    "collab_rooms": "collab_rooms",
    "collab_snapshots": "collab_snapshots",
    "collab_tokens": "collab_tokens",
    "map_settings": "map_settings",
    "map_viewports": "map_viewports",
    "map_exports": "map_exports",
    # PressForge is a separate product surface, but these historical tables
    # contain explicit AuthorForge project links or content-capable fields.
    # Flag their metadata for human ownership review without inspecting rows.
    "pf_journalists": "pressforge_linked/journalists",
    "pf_campaigns": "pressforge_linked/campaigns",
    "pf_match_results": "pressforge_linked/match_results",
    "pf_pitches": "pressforge_linked/pitches",
    "pf_outreach_events": "pressforge_linked/outreach_events",
    "pf_coverage": "pressforge_linked/coverage",
    "pf_domain_reputation": "pressforge_linked/domain_reputation",
    "pf_ai_audit_log": "pressforge_linked/ai_audit_log",
    "pf_evidence_items": "pressforge_linked/evidence_items",
    "pf_retrieval_runs": "pressforge_linked/retrieval_runs",
    "pf_automation_jobs": "pressforge_linked/automation_jobs",
    "pf_automation_runs": "pressforge_linked/automation_runs",
    "pf_automation_alerts": "pressforge_linked/automation_alerts",
    "pf_automation_overrides": "pressforge_linked/automation_overrides",
    "pf_agent_logs": "pressforge_linked/agent_logs",
    "pf_provider_configs": "pressforge_linked/provider_configs",
    "pf_geo_probes": "pressforge_linked/geo_probes",
    "pf_geo_probe_templates": "pressforge_linked/geo_probe_templates",
    "pf_social_draftsets": "pressforge_linked/social_draftsets",
    "pf_prompt_packs": "pressforge_linked/prompt_packs",
    "pf_campaign_outcomes": "pressforge_linked/campaign_outcomes",
}


def _quoted(identifier: str) -> str:
    # All identifiers originate in the fixed map or inspector-confirmed PK list.
    if not identifier.replace("_", "").isalnum():
        raise ValueError("unsafe schema identifier")
    return f'"{identifier}"'


def audit_authorforge_metadata(
    audit_engine: Engine,
    *,
    max_ids_per_table: int = 100,
) -> dict[str, Any]:
    """Return categories/counts/PKs only; content columns are never selected."""
    if not 0 <= max_ids_per_table <= 1000:
        raise ValueError("max_ids_per_table must be between 0 and 1000")

    inspector = inspect(audit_engine)
    existing_tables = set(inspector.get_table_names())
    findings: list[dict[str, Any]] = []

    with audit_engine.connect() as connection:
        for table_name, category in AUTHORFORGE_LEGACY_TABLES.items():
            if table_name not in existing_tables:
                continue
            quoted_table = _quoted(table_name)
            count = int(
                connection.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar_one()
            )
            if count == 0:
                continue

            primary_keys = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
            safe_primary_keys = [key for key in primary_keys if isinstance(key, str)]
            id_rows: list[Any] = []
            if safe_primary_keys and max_ids_per_table:
                quoted_keys = ", ".join(_quoted(key) for key in safe_primary_keys)
                order_by = ", ".join(_quoted(key) for key in safe_primary_keys)
                rows = connection.execute(
                    text(
                        f"SELECT {quoted_keys} FROM {quoted_table} "
                        f"ORDER BY {order_by} LIMIT :limit"
                    ),
                    {"limit": max_ids_per_table},
                ).all()
                id_rows = [
                    str(row[0]) if len(row) == 1 else [str(value) for value in row]
                    for row in rows
                ]

            findings.append(
                {
                    "category": category,
                    "record_count": count,
                    "primary_key_columns": safe_primary_keys,
                    "record_ids": id_rows,
                    "record_ids_truncated": count > len(id_rows),
                }
            )

    return {
        "audit_version": "authorforge-boundary-metadata.v1",
        "read_only": True,
        "content_columns_read": False,
        "potential_legacy_categories": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit legacy AuthorForge table metadata only.")
    parser.add_argument("--max-ids-per-table", type=int, default=100)
    args = parser.parse_args(argv)

    if DATABASE_URL_IS_DEFAULT:
        print(
            json.dumps(
                {
                    "audit_version": "authorforge-boundary-metadata.v1",
                    "status": "failed",
                    "category": "configuration",
                    "code": "database_url_missing",
                }
            )
        )
        return 1
    try:
        report = audit_authorforge_metadata(
            engine, max_ids_per_table=args.max_ids_per_table
        )
    except Exception:
        print(
            json.dumps(
                {
                    "audit_version": "authorforge-boundary-metadata.v1",
                    "status": "failed",
                    "category": "database",
                    "code": "metadata_audit_failed",
                }
            )
        )
        return 1

    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

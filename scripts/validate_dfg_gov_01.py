#!/usr/bin/env python3
"""Side-effect-free validator for the unadmitted DFG-GOV-01 candidate."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
USES = {"RETRIEVAL", "EVALUATION", "TRAINING"}
FORBIDDEN_KEYS = {
    "content", "text", "body", "prompt", "response", "path", "attachment",
    "embedding", "manuscript", "authorforge_project", "authorforge_document",
}


class CandidateValidationError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def fail(code: str, detail: str) -> None:
    raise CandidateValidationError(code, detail)


def walk(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                fail("forbidden_content_field", key)
            if key.endswith("digest") and not (
                isinstance(child, str) and DIGEST.fullmatch(child)
            ):
                fail("digest_invalid", key)
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def unique(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result = {}
    for record in records:
        value = record.get(key)
        if not isinstance(value, str) or not value:
            fail("required_identifier_missing", key)
        if value in result:
            fail("identifier_duplicate", value)
        result[value] = record
    return result


def validate(bundle: dict[str, Any]) -> None:
    if bundle.get("schema_version") != "dataforge.dataset_governance_candidate.v0":
        fail("schema_version_unsupported", str(bundle.get("schema_version")))
    if bundle.get("candidate_status") != "UNADMITTED_OFFLINE_ONLY":
        fail("candidate_status_invalid", str(bundle.get("candidate_status")))
    walk(bundle)

    assets = unique(bundle.get("source_assets", []), "source_asset_id")
    units = unique(bundle.get("source_units", []), "source_unit_id")
    auths = unique(bundle.get("use_authorizations", []), "authorization_id")
    for unit in units.values():
        if unit.get("source_asset_id") not in assets:
            fail("source_asset_unknown", str(unit.get("source_asset_id")))

    seen = {asset_id: set() for asset_id in assets}
    training_status = {}
    for decision in bundle.get("eligibility_decisions", []):
        asset_id, use = decision.get("source_asset_id"), decision.get("use")
        if asset_id not in assets:
            fail("eligibility_source_unknown", str(asset_id))
        if use not in USES:
            fail("eligibility_use_invalid", str(use))
        if use in seen[asset_id]:
            fail("eligibility_duplicate", f"{asset_id}:{use}")
        seen[asset_id].add(use)
        auth = auths.get(decision.get("authorization_ref"))
        if auth is None:
            fail("authorization_missing", str(decision.get("authorization_ref")))
        if decision.get("status") == "ELIGIBLE":
            if auth.get("decision") != "GRANTED":
                fail("authorization_not_granted", str(auth.get("decision")))
            if use not in set(auth.get("permitted_uses", [])):
                fail("use_not_permitted", str(use))
            if auth.get("source_asset_id") != asset_id:
                fail("authorization_scope_mismatch", str(asset_id))
        if use == "TRAINING":
            training_status[asset_id] = decision.get("status")
    for asset_id, uses in seen.items():
        if uses != USES:
            fail("eligibility_set_incomplete", f"{asset_id}:{sorted(uses)}")

    groups = unique(bundle.get("similarity_groups", []), "group_id")
    assignments = unique(bundle.get("split_assignments", []), "source_unit_id")
    if set(assignments) != set(units):
        fail("split_assignment_incomplete", "each unit must be assigned exactly once")
    for group_id, group in groups.items():
        members = set(group.get("member_unit_ids", []))
        if not members or not members.issubset(units):
            fail("similarity_member_unknown", group_id)
        if {assignments[m].get("group_id") for m in members} != {group_id}:
            fail("similarity_assignment_mismatch", group_id)
        if len({assignments[m].get("split") for m in members}) != 1:
            fail("similarity_split_leakage", group_id)

    unit_assets = {key: value["source_asset_id"] for key, value in units.items()}
    for finding in bundle.get("contamination_findings", []):
        unit_id = finding.get("source_unit_id")
        if unit_id not in units:
            fail("contamination_unit_unknown", str(unit_id))
        if finding.get("severity") == "BLOCKING" or finding.get("blocks_training") is True:
            asset_id = unit_assets[unit_id]
            if training_status.get(asset_id) == "ELIGIBLE":
                fail("training_contamination_block", asset_id)

    revoked = False
    for impact in bundle.get("revocation_impacts", []):
        auth = auths.get(impact.get("authorization_ref"))
        if auth is None:
            fail("revocation_authorization_unknown", str(impact.get("authorization_ref")))
        if auth.get("decision") not in {"REVOKED", "EXPIRED"}:
            fail("revocation_state_invalid", str(auth.get("decision")))
        revoked = True
        for asset_id in impact.get("affected_source_asset_ids", []):
            if asset_id not in assets:
                fail("revocation_source_unknown", str(asset_id))
            if training_status.get(asset_id) == "ELIGIBLE":
                fail("authorization_not_granted", str(auth.get("decision")))
    if revoked and bundle.get("snapshot_state") != "INVALIDATED":
        fail("snapshot_not_invalidated", str(bundle.get("snapshot_state")))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_dfg_gov_01.py BUNDLE.json", file=sys.stderr)
        return 2
    try:
        validate(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, CandidateValidationError) as exc:
        print(f"DFG_GOV_01_INVALID {exc}", file=sys.stderr)
        return 1
    print("DFG_GOV_01_VALID candidate_only=true runtime_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

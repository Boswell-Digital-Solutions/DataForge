#!/usr/bin/env python3
"""
Seed deterministic LLM policy envelopes for ForgeAgents Slice 1.

Usage:
    python -m scripts.seed_policy_envelopes
    python scripts/seed_policy_envelopes.py

Idempotent: updates existing records by default.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path for direct invocation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.policy_envelope_models import LLMPolicyEnvelopeModel
from app.models.policy_envelope_schemas import (
    PolicyEnvelopeV1,
    PolicyHardFailThresholdsV1,
    PolicyTimeoutsV1,
)
from scripts.seed_model_catalog import MODEL_CATALOG

LEGACY_FORGEAGENTS_DEFAULT_MODELS = {
    "claude-3-5-sonnet-20241022",
    "gpt-4-turbo-preview",
}


def build_model_whitelist() -> list[str]:
    """Return the explicit set of allowed model identifiers.

    The whitelist is pinned to the DataForge model catalog so policy approval
    and pricing enforcement stay aligned.
    """
    identifiers: set[str] = set()
    for row in MODEL_CATALOG:
        identifiers.add(row["model_key"])
        identifiers.add(row["model_id"])
    return sorted(identifiers)


def build_policy_envelopes() -> dict[str, PolicyEnvelopeV1]:
    """Build canonical policy envelopes for wired ForgeAgents call paths."""
    whitelist = build_model_whitelist()
    strict_thresholds = PolicyHardFailThresholdsV1(
        invariant_violation=True,
        safety_score_min=Decimal("0.80"),
        unit_test_pass_required=True,
    )

    policies: dict[str, PolicyEnvelopeV1] = {
        "forgeagents.assist.v1": PolicyEnvelopeV1(
            policy_version="v1",
            model_whitelist=whitelist,
            max_calls_per_run=1,
            max_tokens_per_run=12000,
            max_cost_usd_per_run=Decimal("1.00"),
            timeouts=PolicyTimeoutsV1(per_call_seconds=90, total_run_seconds=120),
            hard_fail_thresholds=strict_thresholds,
        ),
        "forgeagents.skills.v1": PolicyEnvelopeV1(
            policy_version="v1",
            model_whitelist=whitelist,
            max_calls_per_run=1,
            max_tokens_per_run=16000,
            max_cost_usd_per_run=Decimal("2.50"),
            timeouts=PolicyTimeoutsV1(per_call_seconds=120, total_run_seconds=180),
            hard_fail_thresholds=strict_thresholds,
        ),
    }

    agent_caps = {
        "researcher": (15, 180000, Decimal("15.00"), 120, 1800),
        "analyst": (10, 120000, Decimal("10.00"), 120, 1200),
        "writer": (10, 120000, Decimal("10.00"), 120, 1200),
        "coder": (20, 240000, Decimal("25.00"), 180, 2400),
        "orchestrator": (25, 300000, Decimal("35.00"), 180, 3000),
        "ecosystem": (30, 360000, Decimal("50.00"), 180, 3600),
        "sentinel": (10, 120000, Decimal("10.00"), 120, 1200),
    }

    for agent_type, (
        max_calls,
        max_tokens,
        max_cost,
        per_call_seconds,
        total_run_seconds,
    ) in agent_caps.items():
        policies[f"forgeagents.agent.{agent_type}.v1"] = PolicyEnvelopeV1(
            policy_version="v1",
            model_whitelist=whitelist,
            max_calls_per_run=max_calls,
            max_tokens_per_run=max_tokens,
            max_cost_usd_per_run=max_cost,
            timeouts=PolicyTimeoutsV1(
                per_call_seconds=per_call_seconds,
                total_run_seconds=total_run_seconds,
            ),
            hard_fail_thresholds=strict_thresholds,
        )

    return policies


def seed(
    *,
    update_existing: bool = True,
    db=None,
) -> tuple[int, int, int]:
    """Seed policy envelopes into DataForge.

    Returns:
        Tuple of (created, updated, skipped).
    """
    owns_session = db is None
    db = db or SessionLocal()

    try:
        created = 0
        updated = 0
        skipped = 0

        for policy_key, envelope in build_policy_envelopes().items():
            existing = db.query(LLMPolicyEnvelopeModel).filter(
                LLMPolicyEnvelopeModel.policy_key == policy_key
            ).first()

            if existing is None:
                db.add(
                    LLMPolicyEnvelopeModel(
                        policy_key=policy_key,
                        policy_version=envelope.policy_version,
                        envelope=envelope.model_dump(mode="json"),
                        is_active=True,
                    )
                )
                created += 1
                continue

            if not update_existing:
                skipped += 1
                continue

            existing.policy_version = envelope.policy_version
            existing.envelope = envelope.model_dump(mode="json")
            existing.is_active = True
            updated += 1

        db.commit()
        return created, updated, skipped
    finally:
        if owns_session:
            db.close()


def print_runtime_alignment_warning() -> None:
    """Warn when ForgeAgents defaults are outside the priced model catalog."""
    whitelist = set(build_model_whitelist())
    missing = sorted(LEGACY_FORGEAGENTS_DEFAULT_MODELS - whitelist)
    if not missing:
        return

    print("Warning: ForgeAgents runtime defaults are outside the seeded policy whitelist.")
    print("These model identifiers are not in DataForge's canonical model catalog:")
    for model in missing:
        print(f"  - {model}")
    print("Align provider defaults or pass an explicit catalog-backed model before enabling Slice 1.")


if __name__ == "__main__":
    created, updated, skipped = seed()
    total = len(build_policy_envelopes())
    print(
        "Policy envelope seed complete: "
        f"{created} created, {updated} updated, {skipped} skipped"
    )
    print(f"Total seeded policy envelopes: {total}")
    print_runtime_alignment_warning()

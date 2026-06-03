#!/usr/bin/env python3
"""
Seed the model_catalog table with the canonical 14-model Forge catalog.

Usage:
    python -m scripts.seed_model_catalog          # from DataForge root
    python scripts/seed_model_catalog.py           # direct invocation

Idempotent: skips models that already exist, updates pricing for existing ones.
"""

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path for direct invocation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.multi_provider_models import ModelCatalog

RETIRED_MODEL_IDENTIFIERS = {
    "grok-4",
    "grok-4.1-fast",
}

MODEL_CATALOG = [
    # ── Budget Tier ───────────────────────────────────────────────
    {
        "model_key": "gpt-5-nano",
        "provider": "openai",
        "model_id": "gpt-5-nano",
        "input_cost_per_mtok": Decimal("0.05"),
        "output_cost_per_mtok": Decimal("0.40"),
        "batch_input_cost": Decimal("0.025"),
        "batch_output_cost": Decimal("0.20"),
        "max_context": 128_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "budget",
    },
    {
        "model_key": "gpt-4.1-nano",
        "provider": "openai",
        "model_id": "gpt-4.1-nano",
        "input_cost_per_mtok": Decimal("0.10"),
        "output_cost_per_mtok": Decimal("0.40"),
        "batch_input_cost": Decimal("0.05"),
        "batch_output_cost": Decimal("0.20"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.25"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "budget",
    },
    {
        "model_key": "gemini-2.5-flash-lite",
        "provider": "google",
        "model_id": "gemini-2.5-flash-lite",
        "input_cost_per_mtok": Decimal("0.10"),
        "output_cost_per_mtok": Decimal("0.40"),
        "batch_input_cost": Decimal("0.05"),
        "batch_output_cost": Decimal("0.20"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "budget",
    },
    {
        "model_key": "grok-4-1-fast-non-reasoning",
        "provider": "xai",
        "model_id": "grok-4-1-fast-non-reasoning",
        "input_cost_per_mtok": Decimal("0.20"),
        "output_cost_per_mtok": Decimal("0.50"),
        "batch_input_cost": Decimal("0.10"),
        "batch_output_cost": Decimal("0.25"),
        "max_context": 2_000_000,
        "cache_read_discount": Decimal("0.00"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "budget",
    },

    # ── Workhorse Tier ────────────────────────────────────────────
    {
        "model_key": "gemini-2.5-flash",
        "provider": "google",
        "model_id": "gemini-2.5-flash",
        "input_cost_per_mtok": Decimal("0.30"),
        "output_cost_per_mtok": Decimal("2.50"),
        "batch_input_cost": Decimal("0.15"),
        "batch_output_cost": Decimal("1.25"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "gemini-3-flash",
        "provider": "google",
        "model_id": "gemini-3-flash-preview",
        "input_cost_per_mtok": Decimal("0.50"),
        "output_cost_per_mtok": Decimal("3.00"),
        "batch_input_cost": Decimal("0.25"),
        "batch_output_cost": Decimal("1.50"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "gpt-5-mini",
        "provider": "openai",
        "model_id": "gpt-5-mini",
        "input_cost_per_mtok": Decimal("0.25"),
        "output_cost_per_mtok": Decimal("2.00"),
        "batch_input_cost": Decimal("0.125"),
        "batch_output_cost": Decimal("1.00"),
        "max_context": 128_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "grok-4-1-fast-reasoning",
        "provider": "xai",
        "model_id": "grok-4-1-fast-reasoning",
        "input_cost_per_mtok": Decimal("0.20"),
        "output_cost_per_mtok": Decimal("0.50"),
        "batch_input_cost": Decimal("0.10"),
        "batch_output_cost": Decimal("0.25"),
        "max_context": 2_000_000,
        "cache_read_discount": Decimal("0.00"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "claude-haiku-4.5",
        "provider": "anthropic",
        "model_id": "claude-haiku-4-5-20251001",
        "input_cost_per_mtok": Decimal("1.00"),
        "output_cost_per_mtok": Decimal("5.00"),
        "batch_input_cost": Decimal("0.50"),
        "batch_output_cost": Decimal("2.50"),
        "max_context": 200_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },

    # ── Flagship Tier ─────────────────────────────────────────────
    {
        "model_key": "gemini-2.5-pro",
        "provider": "google",
        "model_id": "gemini-2.5-pro",
        "input_cost_per_mtok": Decimal("1.25"),
        "output_cost_per_mtok": Decimal("10.00"),
        "batch_input_cost": Decimal("0.625"),
        "batch_output_cost": Decimal("5.00"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "flagship",
    },
    {
        "model_key": "gemini-3-pro",
        "provider": "google",
        "model_id": "gemini-3-pro-preview",
        "input_cost_per_mtok": Decimal("2.00"),
        "output_cost_per_mtok": Decimal("12.00"),
        "batch_input_cost": Decimal("1.00"),
        "batch_output_cost": Decimal("6.00"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "flagship",
    },
    {
        "model_key": "claude-sonnet-4.5",
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5-20250929",
        "input_cost_per_mtok": Decimal("3.00"),
        "output_cost_per_mtok": Decimal("15.00"),
        "batch_input_cost": Decimal("1.50"),
        "batch_output_cost": Decimal("7.50"),
        "max_context": 200_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "flagship",
    },
    # ── Additional Models (14-model canonical catalog) ─────────────
    {
        "model_key": "gpt-4.1-mini",
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "input_cost_per_mtok": Decimal("0.40"),
        "output_cost_per_mtok": Decimal("1.60"),
        "batch_input_cost": Decimal("0.20"),
        "batch_output_cost": Decimal("0.80"),
        "max_context": 1_000_000,
        "cache_read_discount": Decimal("0.25"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "claude-opus-4.5",
        "provider": "anthropic",
        "model_id": "claude-opus-4-5-20250514",
        "input_cost_per_mtok": Decimal("15.00"),
        "output_cost_per_mtok": Decimal("75.00"),
        "batch_input_cost": Decimal("7.50"),
        "batch_output_cost": Decimal("37.50"),
        "max_context": 200_000,
        "cache_read_discount": Decimal("0.10"),
        "supports_batch": True,
        "supports_structured_output": True,
        "tier": "flagship",
    },
    # DeepSeek — official API pricing
    # (https://api-docs.deepseek.com/quick_start/pricing-details-usd, the source already
    # approved in llm_intel_source_trust). input_cost_per_mtok is the cache-MISS price;
    # cache_read_discount is the cache-hit ratio. DeepSeek has no batch API.
    {
        "model_key": "deepseek-chat",
        "provider": "deepseek",
        "model_id": "deepseek-chat",
        "input_cost_per_mtok": Decimal("0.27"),
        "output_cost_per_mtok": Decimal("1.10"),
        "batch_input_cost": None,
        "batch_output_cost": None,
        "max_context": 64_000,
        "cache_read_discount": Decimal("0.26"),
        "supports_batch": False,
        "supports_structured_output": True,
        "tier": "workhorse",
    },
    {
        "model_key": "deepseek-reasoner",
        "provider": "deepseek",
        "model_id": "deepseek-reasoner",
        "input_cost_per_mtok": Decimal("0.55"),
        "output_cost_per_mtok": Decimal("2.19"),
        "batch_input_cost": None,
        "batch_output_cost": None,
        "max_context": 64_000,
        "cache_read_discount": Decimal("0.25"),
        "supports_batch": False,
        "supports_structured_output": False,
        "tier": "workhorse",
    },
]


def _retire_replaced_models(db) -> int:
    retired = 0
    for row in (
        db.query(ModelCatalog)
        .filter(ModelCatalog.provider == "xai", ModelCatalog.is_active.is_(True))
        .all()
    ):
        if (
            row.model_key not in RETIRED_MODEL_IDENTIFIERS
            and row.model_id not in RETIRED_MODEL_IDENTIFIERS
        ):
            continue
        row.is_active = False
        row.updated_by = "seed_script_retired"
        retired += 1
    return retired


def seed(update_existing: bool = True, db=None) -> tuple[int, int, int, int]:
    """Seed model catalog. If update_existing=True, refreshes pricing for existing models."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        created = 0
        updated = 0
        skipped = 0
        retired = 0

        for model_data in MODEL_CATALOG:
            existing = db.query(ModelCatalog).filter(
                ModelCatalog.model_key == model_data["model_key"]
            ).first()

            if existing:
                if update_existing:
                    for field, value in model_data.items():
                        setattr(existing, field, value)
                    existing.updated_by = "seed_script"
                    updated += 1
                else:
                    skipped += 1
            else:
                row = ModelCatalog(**model_data, updated_by="seed_script")
                db.add(row)
                created += 1

        if update_existing:
            retired = _retire_replaced_models(db)

        db.commit()
        print(
            "Model catalog seed complete: "
            f"{created} created, {updated} updated, {skipped} skipped, {retired} retired"
        )
        print(f"Total models in catalog: {db.query(ModelCatalog).count()}")
        return created, updated, skipped, retired

    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    seed()

from decimal import Decimal

from scripts.seed_model_catalog import MODEL_CATALOG, RETIRED_MODEL_IDENTIFIERS, seed
from app.models.multi_provider_models import ModelCatalog


def test_model_catalog_uses_explicit_grok_4_1_fast_variants():
    model_keys = {row["model_key"] for row in MODEL_CATALOG}
    model_ids = {row["model_id"] for row in MODEL_CATALOG}

    assert "grok-4-1-fast-non-reasoning" in model_keys
    assert "grok-4-1-fast-reasoning" in model_keys
    assert "grok-4-1-fast-non-reasoning" in model_ids
    assert "grok-4-1-fast-reasoning" in model_ids
    assert "grok-4.1-fast" not in model_keys
    assert "grok-4" not in model_keys


def test_seed_retires_legacy_xai_aliases(db):
    db.add(
        ModelCatalog(
            model_key="grok-4",
            provider="xai",
            model_id="grok-4",
            input_cost_per_mtok=Decimal("3.00"),
            output_cost_per_mtok=Decimal("15.00"),
            batch_input_cost=Decimal("1.50"),
            batch_output_cost=Decimal("7.50"),
            max_context=256_000,
            cache_read_discount=Decimal("0.00"),
            supports_batch=True,
            supports_structured_output=True,
            tier="flagship",
            is_active=True,
            updated_by="test",
        )
    )
    db.add(
        ModelCatalog(
            model_key="grok-4.1-fast",
            provider="xai",
            model_id="grok-4.1-fast",
            input_cost_per_mtok=Decimal("0.20"),
            output_cost_per_mtok=Decimal("0.50"),
            batch_input_cost=Decimal("0.10"),
            batch_output_cost=Decimal("0.25"),
            max_context=2_000_000,
            cache_read_discount=Decimal("0.00"),
            supports_batch=True,
            supports_structured_output=True,
            tier="budget",
            is_active=True,
            updated_by="test",
        )
    )
    db.commit()

    created, updated, skipped, retired = seed(db=db)

    assert created == len(MODEL_CATALOG)
    assert updated == 0
    assert skipped == 0
    assert retired == len(RETIRED_MODEL_IDENTIFIERS)

    legacy_rows = {
        row.model_key: row
        for row in db.query(ModelCatalog)
        .filter(ModelCatalog.model_key.in_(RETIRED_MODEL_IDENTIFIERS))
        .all()
    }
    assert legacy_rows["grok-4"].is_active is False
    assert legacy_rows["grok-4.1-fast"].is_active is False

    new_keys = {
        row.model_key
        for row in db.query(ModelCatalog).filter(ModelCatalog.provider == "xai").all()
    }
    assert "grok-4-1-fast-non-reasoning" in new_keys
    assert "grok-4-1-fast-reasoning" in new_keys

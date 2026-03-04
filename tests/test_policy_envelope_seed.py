"""Tests for policy envelope seed data."""

from __future__ import annotations

from app.models.policy_envelope_models import LLMPolicyEnvelopeModel
from scripts.seed_policy_envelopes import (
    LEGACY_FORGEAGENTS_DEFAULT_MODELS,
    build_model_whitelist,
    build_policy_envelopes,
    seed,
)


def test_build_policy_envelopes_covers_wired_keys():
    envelopes = build_policy_envelopes()

    assert "forgeagents.assist.v1" in envelopes
    assert "forgeagents.skills.v1" in envelopes
    assert "forgeagents.agent.researcher.v1" in envelopes
    assert "forgeagents.agent.analyst.v1" in envelopes
    assert "forgeagents.agent.writer.v1" in envelopes
    assert "forgeagents.agent.coder.v1" in envelopes
    assert "forgeagents.agent.orchestrator.v1" in envelopes
    assert "forgeagents.agent.ecosystem.v1" in envelopes
    assert "forgeagents.agent.sentinel.v1" in envelopes

    whitelist = set(build_model_whitelist())
    assert LEGACY_FORGEAGENTS_DEFAULT_MODELS.isdisjoint(whitelist)
    assert "claude-sonnet-4.5" in whitelist
    assert "claude-sonnet-4-5-20250929" in whitelist
    assert "gpt-5-mini" in whitelist


def test_seed_policy_envelopes_is_idempotent(db):
    created, updated, skipped = seed(db=db)
    assert created == len(build_policy_envelopes())
    assert updated == 0
    assert skipped == 0

    rows = db.query(LLMPolicyEnvelopeModel).all()
    assert len(rows) == len(build_policy_envelopes())

    created_second, updated_second, skipped_second = seed(db=db)
    assert created_second == 0
    assert updated_second == len(build_policy_envelopes())
    assert skipped_second == 0

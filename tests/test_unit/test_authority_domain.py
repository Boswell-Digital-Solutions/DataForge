"""FC-LTA-P006: this service's own self-reported authority_domain.

`load_own_authority_domain()` formalizes what `doc/system/40_governance/
11-scope.md` already states in prose ("DataForge is the durable-truth boundary
for the Forge ecosystem") into a machine-readable self-report, read from this
repo's own `service_contract.v1.json`.
"""

from __future__ import annotations

import json

import pytest

from app.authority import load_own_authority_domain


@pytest.mark.unit
def test_reads_the_declared_value_from_the_real_contract_file():
    # Exercises the actual repo-root service_contract.v1.json, not a fixture —
    # this is the file Forge_Command's evaluator will compare against.
    assert load_own_authority_domain() == "durable-truth"


@pytest.mark.unit
def test_missing_field_yields_none_not_an_error(tmp_path):
    contract = tmp_path / "service_contract.v1.json"
    contract.write_text(json.dumps({"service_id": "dataforge"}))
    assert load_own_authority_domain(contract) is None


@pytest.mark.unit
def test_non_string_field_yields_none_not_an_error(tmp_path):
    contract = tmp_path / "service_contract.v1.json"
    contract.write_text(json.dumps({"authority_domain": 42}))
    assert load_own_authority_domain(contract) is None


@pytest.mark.unit
def test_empty_string_field_yields_none_not_an_error(tmp_path):
    contract = tmp_path / "service_contract.v1.json"
    contract.write_text(json.dumps({"authority_domain": ""}))
    assert load_own_authority_domain(contract) is None


@pytest.mark.unit
def test_malformed_json_yields_none_not_an_error(tmp_path):
    contract = tmp_path / "service_contract.v1.json"
    contract.write_text("{not valid json")
    assert load_own_authority_domain(contract) is None


@pytest.mark.unit
def test_missing_file_yields_none_not_an_error(tmp_path):
    assert load_own_authority_domain(tmp_path / "nope.json") is None

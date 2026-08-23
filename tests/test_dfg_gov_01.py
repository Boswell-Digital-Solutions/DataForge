import copy
import json
import unittest
from pathlib import Path

from scripts.validate_dfg_gov_01 import CandidateValidationError, validate

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "plans" / "DFG_GOV_01"


def load(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def mutate(bundle, operation):
    if operation == "remove_authorizations":
        bundle["use_authorizations"] = []
    elif operation == "remove_evaluation_eligibility":
        bundle["eligibility_decisions"] = [x for x in bundle["eligibility_decisions"] if x["use"] != "EVALUATION"]
    elif operation == "revoke_but_keep_eligible":
        bundle["use_authorizations"][0]["decision"] = "REVOKED"
    elif operation == "move_second_unit_to_test":
        bundle["split_assignments"][1]["split"] = "TEST"
    elif operation == "add_blocking_contamination":
        bundle["contamination_findings"].append({"finding_id": "finding:blocking", "source_unit_id": "unit:001", "severity": "BLOCKING", "blocks_training": True, "evidence_digest": "sha256:" + "4" * 64})
    elif operation == "add_forbidden_content_field":
        bundle["source_assets"][0]["content"] = "synthetic content is still refused"
    else:
        raise AssertionError(operation)


class DfgGov01Tests(unittest.TestCase):
    def test_valid_synthetic_candidate_passes(self):
        validate(load("fixtures/valid.json"))

    def test_invalid_mutations_fail_closed(self):
        for case in load("fixtures/invalid-mutations.json")["cases"]:
            with self.subTest(case=case["id"]):
                bundle = copy.deepcopy(load("fixtures/valid.json"))
                mutate(bundle, case["operation"])
                with self.assertRaises(CandidateValidationError) as raised:
                    validate(bundle)
                self.assertEqual(raised.exception.code, case["expected_code"])

    def test_schema_is_explicitly_unadmitted(self):
        schema = load("candidate-contracts/dataset_governance_candidate.v0.schema.json")
        self.assertTrue(schema["$id"].startswith("dataforge/candidates/"))
        self.assertEqual(schema["properties"]["candidate_status"]["const"], "UNADMITTED_OFFLINE_ONLY")

    def test_collision_matrix_reuses_existing_contracts_and_defers_roles(self):
        items = load("collision-matrix.json")["dispositions"]
        dispositions = {x["concept"]: x["disposition"] for x in items}
        self.assertEqual(dispositions["CorpusSnapshotRef.v1"], "reuse")
        self.assertEqual(dispositions["ModelArtifactManifest.v1"], "reuse")
        self.assertEqual(dispositions["producer consumer signer store roles"], "defer")

    def test_source_lock_pins_hfx_14e2_and_registries(self):
        lock = load("source-lock.json")
        self.assertEqual(lock["repositories"]["forge_contract_core"], "d6a18a1395c97923a295805e21d75ce76d57db75")
        self.assertEqual(lock["hfx_14e2"]["ci_conclusion"], "success")
        self.assertEqual(lock["registries"]["repo_role_matrix"]["version"], "1.12.0")
        self.assertTrue(all(len(value["blob_sha"]) == 40 for value in lock["registries"].values()))


if __name__ == "__main__":
    unittest.main()

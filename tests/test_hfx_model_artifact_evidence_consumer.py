"""Hermetic proof for the unmounted HFX model-artifact evidence consumer."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any

import forge_contract_core
import pytest
from forge_contract_core.identity import compute_idempotency_key

from app.services.hfx_model_artifact_evidence_consumer import (
    HFX_MODEL_ARTIFACT_CONSUMER_FAMILIES,
    HfxModelArtifactEvidenceConsumerError,
    validate_hfx_model_artifact_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = Path(forge_contract_core.__file__).resolve().parent.parent
VALID = CONTRACT_ROOT / "fixtures" / "valid"
INVALID = CONTRACT_ROOT / "fixtures" / "invalid"
VECTOR = json.loads(
    (
        CONTRACT_ROOT
        / "fixtures"
        / "hephaestus_artifacts"
        / "artifact_evidence.v1.ed25519.vector.json"
    ).read_text(encoding="utf-8")
)

CONSUMED_FAMILIES = (
    "model_artifact_manifest",
    "model_artifact_attestation_bundle",
    "model_artifact_admission_receipt",
)

EXPECTED_PRODUCER_BY_FAMILY = {
    "model_artifact_manifest": "NeuroForge",
    "model_artifact_attestation_bundle": "forge-smithy",
    "model_artifact_admission_receipt": "forge-smithy",
}


def _canonicalize_idempotency(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact["idempotency_key"] = compute_idempotency_key(
        artifact["artifact_family"],
        artifact["artifact_id"],
        artifact["artifact_version"],
        artifact["lineage_root_id"],
    )
    return artifact


def _fixture(directory: Path, name: str) -> dict[str, Any]:
    artifact = json.loads((directory / name).read_text(encoding="utf-8"))
    artifact = {
        key: value for key, value in artifact.items() if not key.startswith("_")
    }
    if directory == INVALID:
        artifact["produced_by_system"] = EXPECTED_PRODUCER_BY_FAMILY[
            artifact["artifact_family"]
        ]
    return _canonicalize_idempotency(artifact)


def _valid(family: str) -> dict[str, Any]:
    return _fixture(VALID, f"{family}.v1.valid.json")


def _context(family: str) -> dict[str, Any]:
    payload = _valid(family)["payload"]
    if family == "model_artifact_manifest":
        return {
            "expected_run_id": payload["run_id"],
            "expected_request_digest": payload["request_digest"],
            "expected_attempt_id": payload["attempt_id"],
            "expected_training_receipt_digest": payload["training_receipt_digest"],
        }

    trust = {
        "trusted_signing_keys": {VECTOR["key_id"]: VECTOR["public_key"]},
        "authorized_signer_refs": {payload["signer_authorization_ref"]},
        "consumed_issuer_sequences": set(),
    }
    if family == "model_artifact_attestation_bundle":
        return trust | {
            "expected_manifest_digest": payload["manifest_digest"],
            "expected_artifact_set_digest": payload["artifact_set_digest"],
            "expected_training_receipt_digest": payload["training_receipt_digest"],
            "expected_worker_image_digest": payload["worker_image_digest"],
        }
    return trust | {
        "expected_manifest_digest": payload["manifest_digest"],
        "expected_lifecycle_receipt_digest": payload["lifecycle_receipt_digest"],
        "expected_attestation_digest": payload["attestation_digest"],
        "expected_policy_version": payload["policy_version"],
    }


@pytest.mark.parametrize("family", CONSUMED_FAMILIES)
def test_valid_exact_fixture_passes_with_complete_context(family: str) -> None:
    assert (
        validate_hfx_model_artifact_evidence(
            _valid(family),
            semantic_context=_context(family),
        )
        is None
    )


def _invalid_paths() -> list[Path]:
    paths: list[Path] = []
    for family in CONSUMED_FAMILIES:
        paths.extend(sorted(INVALID.glob(f"{family}.v1.*.invalid.json")))
    return paths


@pytest.mark.parametrize("path", _invalid_paths(), ids=lambda path: path.name)
def test_every_contract_invalid_fixture_fails_with_canonical_identity(
    path: Path,
) -> None:
    family = path.name.split(".v1.", maxsplit=1)[0]
    artifact = _fixture(INVALID, path.name)

    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context(family),
        )

    assert exc.value.reason_code == "contract_validation_failed"


@pytest.mark.parametrize("family", CONSUMED_FAMILIES)
def test_every_required_context_key_is_fail_closed(family: str) -> None:
    artifact = _valid(family)
    complete = _context(family)

    for key in complete:
        incomplete = dict(complete)
        del incomplete[key]
        with pytest.raises(
            HfxModelArtifactEvidenceConsumerError,
            match="missing required semantic context",
        ) as exc:
            validate_hfx_model_artifact_evidence(
                artifact,
                semantic_context=incomplete,
            )
        assert exc.value.reason_code == "missing_semantic_context"


@pytest.mark.parametrize(
    "family",
    ("model_artifact_attestation_bundle", "model_artifact_admission_receipt"),
)
def test_signed_family_requires_typed_trust_and_replay_context(family: str) -> None:
    artifact = _valid(family)
    for key, invalid_value in (
        ("trusted_signing_keys", []),
        ("authorized_signer_refs", "not-a-collection"),
        ("consumed_issuer_sequences", "not-a-collection"),
    ):
        context = _context(family)
        context[key] = invalid_value
        with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
            validate_hfx_model_artifact_evidence(
                artifact,
                semantic_context=context,
            )
        assert exc.value.reason_code == "invalid_trust_context"


@pytest.mark.parametrize(
    "family",
    ("model_artifact_attestation_bundle", "model_artifact_admission_receipt"),
)
def test_unknown_key_unauthorized_signer_and_replay_fail_closed(family: str) -> None:
    artifact = _valid(family)
    payload = artifact["payload"]

    for key, value in (
        ("trusted_signing_keys", {}),
        ("authorized_signer_refs", set()),
        ("consumed_issuer_sequences", {payload["issuer_sequence"]}),
    ):
        context = _context(family)
        context[key] = value
        with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
            validate_hfx_model_artifact_evidence(
                artifact,
                semantic_context=context,
            )
        assert exc.value.reason_code == "contract_validation_failed"


@pytest.mark.parametrize(
    "family",
    ("model_artifact_attestation_bundle", "model_artifact_admission_receipt"),
)
def test_changed_signed_projection_fails_signature_verification(family: str) -> None:
    artifact = _valid(family)
    artifact["payload"]["issuer_sequence"] += 1

    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context(family),
        )

    assert exc.value.reason_code == "contract_validation_failed"


@pytest.mark.parametrize(
    ("family", "wrong_producer"),
    (
        ("model_artifact_manifest", "forge-smithy"),
        ("model_artifact_attestation_bundle", "NeuroForge"),
        ("model_artifact_admission_receipt", "DataForge"),
    ),
)
def test_wrong_producer_fails_before_contract_validation(
    family: str,
    wrong_producer: str,
) -> None:
    artifact = _valid(family)
    artifact["produced_by_system"] = wrong_producer

    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context(family),
        )

    assert exc.value.reason_code == "producer_not_admitted"


@pytest.mark.parametrize(
    "family",
    (
        "model_artifact_lifecycle_receipt",
        "cloud_training_cleanup_receipt",
        "training_run_request",
        "source_drift_finding",
        "unknown_family",
    ),
)
def test_every_unnamed_family_is_rejected_before_validation(family: str) -> None:
    artifact = _valid("model_artifact_manifest")
    artifact["artifact_family"] = family

    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context("model_artifact_manifest"),
        )

    assert exc.value.reason_code == "unsupported_family"


def test_unsupported_major_and_noncanonical_idempotency_fail_closed() -> None:
    artifact = _valid("model_artifact_manifest")
    artifact["artifact_version"] = 2
    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context("model_artifact_manifest"),
        )
    assert exc.value.reason_code == "unsupported_version"

    artifact = _valid("model_artifact_manifest")
    artifact["idempotency_key"] = "0" * 64
    with pytest.raises(HfxModelArtifactEvidenceConsumerError) as exc:
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context("model_artifact_manifest"),
        )
    assert exc.value.reason_code == "contract_validation_failed"


def test_unknown_property_and_authoritative_binding_mismatch_fail_closed() -> None:
    artifact = _valid("model_artifact_manifest")
    artifact["payload"]["unexpected"] = "forbidden"
    with pytest.raises(HfxModelArtifactEvidenceConsumerError):
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=_context("model_artifact_manifest"),
        )

    artifact = _valid("model_artifact_manifest")
    context = _context("model_artifact_manifest")
    context["expected_run_id"] = "00000000-0000-4000-8000-000000000000"
    with pytest.raises(HfxModelArtifactEvidenceConsumerError):
        validate_hfx_model_artifact_evidence(
            artifact,
            semantic_context=context,
        )


def test_consumer_allowlist_is_exact_and_role_matrix_is_exercised() -> None:
    assert HFX_MODEL_ARTIFACT_CONSUMER_FAMILIES == frozenset(CONSUMED_FAMILIES)
    for family in CONSUMED_FAMILIES:
        validate_hfx_model_artifact_evidence(
            _valid(family),
            semantic_context=_context(family),
        )


def test_service_has_only_authorized_imports_and_is_not_mounted() -> None:
    service_path = ROOT / "app" / "services" / "hfx_model_artifact_evidence_consumer.py"
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", maxsplit=1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])
    assert imported_roots <= {
        "__future__",
        "collections",
        "typing",
        "forge_contract_core",
    }

    module_name = "hfx_model_artifact_evidence_consumer"
    assert module_name not in (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    for router in (ROOT / "app" / "api").glob("*.py"):
        assert module_name not in router.read_text(encoding="utf-8")


def test_validation_does_not_mutate_artifact_or_context() -> None:
    artifact = _valid("model_artifact_attestation_bundle")
    context = _context("model_artifact_attestation_bundle")
    artifact_before = copy.deepcopy(artifact)
    context_before = copy.deepcopy(context)

    validate_hfx_model_artifact_evidence(
        artifact,
        semantic_context=context,
    )

    assert artifact == artifact_before
    assert context == context_before

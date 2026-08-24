"""Pure HFX model-artifact evidence validation for DataForge.

This module is deliberately unmounted. It validates three contract envelopes
that DataForge is admitted to consume, without persistence, projection, I/O, or
an operational decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forge_contract_core.validators.artifact import (
    ArtifactValidationError,
    validate_artifact,
)
from forge_contract_core.validators.role_matrix import (
    RoleMatrixViolationError,
    check_consumer_admitted,
    check_producer_admitted,
)

DATAFORGE_CONSUMER = "DataForge"

HFX_MODEL_ARTIFACT_CONSUMER_FAMILIES = frozenset(
    {
        "model_artifact_manifest",
        "model_artifact_attestation_bundle",
        "model_artifact_admission_receipt",
    }
)

_EXPECTED_PRODUCER_BY_FAMILY = {
    "model_artifact_manifest": "NeuroForge",
    "model_artifact_attestation_bundle": "forge-smithy",
    "model_artifact_admission_receipt": "forge-smithy",
}

_REQUIRED_CONTEXT_BY_FAMILY = {
    "model_artifact_manifest": frozenset(
        {
            "expected_run_id",
            "expected_request_digest",
            "expected_attempt_id",
            "expected_training_receipt_digest",
        }
    ),
    "model_artifact_attestation_bundle": frozenset(
        {
            "expected_manifest_digest",
            "expected_artifact_set_digest",
            "expected_training_receipt_digest",
            "expected_worker_image_digest",
            "trusted_signing_keys",
            "authorized_signer_refs",
            "consumed_issuer_sequences",
        }
    ),
    "model_artifact_admission_receipt": frozenset(
        {
            "expected_manifest_digest",
            "expected_lifecycle_receipt_digest",
            "expected_attestation_digest",
            "expected_policy_version",
            "trusted_signing_keys",
            "authorized_signer_refs",
            "consumed_issuer_sequences",
        }
    ),
}

_SIGNED_CONTEXT_COLLECTIONS = (
    "authorized_signer_refs",
    "consumed_issuer_sequences",
)


class HfxModelArtifactEvidenceConsumerError(ValueError):
    """Stable fail-closed error raised by the DataForge consumer boundary."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _require_semantic_context(
    family: str,
    semantic_context: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if not isinstance(semantic_context, Mapping):
        raise HfxModelArtifactEvidenceConsumerError(
            "missing_semantic_context",
            f"{family}: semantic_context must be a mapping",
        )

    missing = sorted(_REQUIRED_CONTEXT_BY_FAMILY[family] - semantic_context.keys())
    if missing:
        raise HfxModelArtifactEvidenceConsumerError(
            "missing_semantic_context",
            f"{family}: missing required semantic context: {', '.join(missing)}",
        )

    if family != "model_artifact_manifest":
        if not isinstance(semantic_context["trusted_signing_keys"], Mapping):
            raise HfxModelArtifactEvidenceConsumerError(
                "invalid_trust_context",
                f"{family}: trusted_signing_keys must be a mapping",
            )
        for key in _SIGNED_CONTEXT_COLLECTIONS:
            if not isinstance(
                semantic_context[key],
                (set, frozenset, list, tuple),
            ):
                raise HfxModelArtifactEvidenceConsumerError(
                    "invalid_trust_context",
                    f"{family}: {key} must be a bounded collection",
                )

    return semantic_context


def validate_hfx_model_artifact_evidence(
    artifact: Mapping[str, Any],
    *,
    semantic_context: Mapping[str, Any] | None,
) -> None:
    """Validate one HFX evidence envelope without producing a decision or side effect."""

    if not isinstance(artifact, Mapping):
        raise HfxModelArtifactEvidenceConsumerError(
            "invalid_artifact",
            "artifact must be a mapping",
        )

    family = artifact.get("artifact_family")
    if family not in HFX_MODEL_ARTIFACT_CONSUMER_FAMILIES:
        raise HfxModelArtifactEvidenceConsumerError(
            "unsupported_family",
            f"DataForge is not admitted to consume family {family!r} at this boundary",
        )
    assert isinstance(family, str)

    if artifact.get("artifact_version") != 1:
        raise HfxModelArtifactEvidenceConsumerError(
            "unsupported_version",
            f"DataForge admits only {family}.v1 at this boundary",
        )

    context = _require_semantic_context(family, semantic_context)
    producer = artifact.get("produced_by_system")
    expected_producer = _EXPECTED_PRODUCER_BY_FAMILY[family]
    if producer != expected_producer:
        raise HfxModelArtifactEvidenceConsumerError(
            "producer_not_admitted",
            f"{family}: expected producer {expected_producer!r}, got {producer!r}",
        )

    try:
        check_consumer_admitted(DATAFORGE_CONSUMER, family)
        check_producer_admitted(producer, family)
    except RoleMatrixViolationError as exc:
        raise HfxModelArtifactEvidenceConsumerError(
            "role_matrix_violation",
            str(exc),
        ) from exc

    try:
        validate_artifact(
            dict(artifact),
            strict_idempotency=True,
            semantic_context=context,
        )
    except ArtifactValidationError as exc:
        raise HfxModelArtifactEvidenceConsumerError(
            "contract_validation_failed",
            f"{family}: {exc}",
        ) from exc

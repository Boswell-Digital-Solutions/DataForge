"""Sink-side enforcement of ForgeEvent.v1 semantic profiles.

RFC-FT-04 reserves the ``ai.`` namespace in ``attributes`` and ``metrics`` for
declared semantic profiles. This module applies that reservation at the
canonical ingest boundary, after authentication and subject binding and before
persistence:

- an event with no ``ai.`` key and no ``ai.profile`` is unchanged;
- an ``ai.`` key without ``ai.profile`` is rejected;
- a declared profile that is not admitted is rejected;
- an admitted profile is validated by its authority-pinned validator, and a
  violation is rejected;
- an admitted profile whose validator is missing or fails its pin is rejected
  with 503. It never falls back to base-only validation.

No profile is admitted today. ``ForgeAIInferenceSemantics.v1`` is a candidate
(forge_contract_core registry status ``candidate_rfc_ft_04``), so ordinary
runtime rejects every event that declares it. The only way to accept it is to
override the :func:`admitted_event_profiles` FastAPI dependency, which the
isolated RFC-FT-04 proof harness does in its own process. There is no
environment switch.

The validator is forge_contract_core's own module, vendored byte-for-byte and
SHA-256 pinned. DataForge adds no semantic rule of its own and never rewrites
an event to make it valid.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

PROFILE_ATTRIBUTE = "ai.profile"
NAMESPACE_PREFIX = "ai."
AI_INFERENCE_PROFILE = "ForgeAIInferenceSemantics.v1"

# forge_contract_core candidate commit and the exact validator bytes vendored
# from it (forge_contract_core/validators/ai_inference_profile.py).
AI_INFERENCE_PROFILE_AUTHORITY_COMMIT = "f4bf3a5986160954a1cafa69457f3e45859b8135"
AI_INFERENCE_PROFILE_VALIDATOR_SHA256 = (
    "eeb957e1749be909477c3d6c9f629886b328bdc1f788ff5f39d9b93a4eaa6982"
)
_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "contracts"
    / "rfc_ft_04"
    / "ai_inference_profile.candidate.py"
)

# Admitted profiles. Empty until RFC-FT-04 is admitted by the operator.
ADMITTED_EVENT_PROFILES: frozenset[str] = frozenset()

PROFILE_UNDECLARED = "event_profile_undeclared"
PROFILE_UNADMITTED = "event_profile_unadmitted"
PROFILE_VIOLATION = "event_profile_violation"
PROFILE_VALIDATOR_UNAVAILABLE = "event_profile_validator_unavailable"

ProfileValidator = Callable[[Mapping[str, Any]], list[str]]


def _load_pinned_validator(path: Path, expected_sha256: str) -> ProfileValidator | None:
    """Load a vendored validator only if its bytes match the pin.

    The hash is checked before the module is executed, so drifted bytes never
    run. Any failure returns ``None``; callers fail closed.
    """

    try:
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            logger.error("Profile validator pin mismatch", extra={"path": path.name})
            return None
        spec = importlib.util.spec_from_loader(
            "dataforge_vendored_ai_inference_profile", loader=None
        )
        if spec is None:
            return None
        module = importlib.util.module_from_spec(spec)
        # Execute the exact bytes that were hashed, never a second read.
        exec(compile(content, str(path), "exec"), module.__dict__)  # noqa: S102  # nosec B102
        validator = module.__dict__.get("profile_errors")
        return validator if callable(validator) else None
    except Exception:  # noqa: BLE001 - any load failure fails closed
        logger.error("Profile validator failed to load", extra={"path": path.name})
        return None


PROFILE_VALIDATORS: dict[str, ProfileValidator | None] = {
    AI_INFERENCE_PROFILE: _load_pinned_validator(
        _VALIDATOR_PATH, AI_INFERENCE_PROFILE_VALIDATOR_SHA256
    ),
}


def admitted_event_profiles() -> frozenset[str]:
    """FastAPI dependency: the profiles this sink accepts."""

    return ADMITTED_EVENT_PROFILES


def _reject(status_code: int, code: str, profile_error: str | None = None) -> HTTPException:
    detail: dict[str, str] = {"code": code}
    if profile_error is not None:
        detail["profile_error"] = profile_error
    return HTTPException(status_code=status_code, detail=detail)


def _namespaced(section: Any) -> bool:
    return isinstance(section, Mapping) and any(
        isinstance(key, str) and key.startswith(NAMESPACE_PREFIX) for key in section
    )


def enforce_event_profile(
    event: Mapping[str, Any],
    admitted: frozenset[str],
    validators: Mapping[str, ProfileValidator | None] | None = None,
) -> None:
    """Raise a value-free HTTPException unless the event may be persisted."""

    validators = PROFILE_VALIDATORS if validators is None else validators
    attributes = event.get("attributes")
    metrics = event.get("metrics")
    if not isinstance(attributes, Mapping) or PROFILE_ATTRIBUTE not in attributes:
        if _namespaced(attributes) or _namespaced(metrics):
            raise _reject(status.HTTP_422_UNPROCESSABLE_ENTITY, PROFILE_UNDECLARED)
        return

    declared = attributes[PROFILE_ATTRIBUTE]
    if not isinstance(declared, str) or declared not in admitted:
        raise _reject(status.HTTP_422_UNPROCESSABLE_ENTITY, PROFILE_UNADMITTED)

    validator = validators.get(declared)
    if validator is None:
        raise _reject(status.HTTP_503_SERVICE_UNAVAILABLE, PROFILE_VALIDATOR_UNAVAILABLE)
    try:
        errors = validator(event)
    except Exception:  # noqa: BLE001 - a validator fault is not an acceptance
        raise _reject(
            status.HTTP_503_SERVICE_UNAVAILABLE, PROFILE_VALIDATOR_UNAVAILABLE
        ) from None
    if errors:
        raise _reject(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            PROFILE_VIOLATION,
            str(errors[0]).split(":")[0],
        )

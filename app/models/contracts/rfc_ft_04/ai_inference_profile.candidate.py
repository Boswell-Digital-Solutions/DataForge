"""Semantic validation for the ForgeAIInferenceSemantics.v1 profile (CANDIDATE).

RFC-FT-04 defines the profile as rules over the admitted ForgeEvent.v1 fields.
It is not admitted. The operator authorized this module on 2026-09-29 only as
admission-proof preparation. JSON Schema checks the shape of a profile event.
This module owns the rules that the schema cannot express, and it also applies
to events that do not declare the profile (an ``ai.`` key without the
declaration fails). It performs no I/O and never raises on malformed input: every rejection is a
value-free error code.

A producer or sink must call this in addition to ForgeEvent.v1 validation,
never instead of it.

Corrective pass (2026-09-29): a derived token class is available only when
every operand is known. An unknown operand never counts as zero.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

PROFILE_NAME = "ForgeAIInferenceSemantics.v1"
PROFILE_ATTRIBUTE = "ai.profile"
MEASUREMENT_CLASS_ATTRIBUTE = "ai.token_measurement_class"
UNAVAILABLE_ATTRIBUTE = "ai.unavailable_metrics"
NAMESPACE_PREFIX = "ai."

# run_cost_event.v1 measurement_class, reused by D-2.
MEASUREMENT_CLASSES = frozenset({"exact", "provider_reported", "metered", "estimated"})

# The five disjoint run_cost_event.v1 token classes, reused by D-2.
TOKEN_CLASSES = (
    "uncached_input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "output_tokens",
)
TOKEN_METRICS = tuple(f"ai.{name}" for name in TOKEN_CLASSES)
LATENCY_METRIC = "ai.model_latency_ms"
PROFILE_METRICS = (*TOKEN_METRICS, LATENCY_METRIC)
PROFILE_ATTRIBUTES = (PROFILE_ATTRIBUTE, MEASUREMENT_CLASS_ATTRIBUTE, UNAVAILABLE_ATTRIBUTE)

# Operator ruling 2 (2026-09-29): a profile event carries no legacy aggregate.
RETIRED_METRICS = frozenset({"tokens_in", "tokens_out", "tokens_total"})

# D-1 / RFC-FT-01: identity and cost stay out of event bytes. This is a guard
# on known key names. It does not claim to detect every way to leak identity.
FORBIDDEN_KEYS = frozenset(
    {
        "provider",
        "provider_id",
        "provider_tier",
        "model",
        "model_id",
        "model_name",
        "model_version",
        "served_model_id",
        "tier",
        "domain",
        "task_type",
        "request_id",
        "prompt",
        "response",
        "cost_usd",
        "amount_micros",
        "currency",
        "rate_card_snapshot_id",
        "execution_lane",
        "routing_reason",
    }
)

ERR_EVENT_INVALID = "AI_PROFILE_EVENT_INVALID"
ERR_UNDECLARED = "AI_PROFILE_UNDECLARED"
ERR_DECLARATION_INVALID = "AI_PROFILE_DECLARATION_INVALID"
ERR_UNKNOWN_KEY = "AI_PROFILE_UNKNOWN_KEY"
ERR_FORBIDDEN_KEY = "AI_PROFILE_FORBIDDEN_KEY"
ERR_RETIRED_METRIC = "AI_PROFILE_RETIRED_METRIC"
ERR_UNAVAILABLE_NOT_CANONICAL = "AI_PROFILE_UNAVAILABLE_NOT_CANONICAL"
ERR_METRIC_DUPLICATED = "AI_PROFILE_METRIC_PRESENT_AND_UNAVAILABLE"
ERR_METRIC_UNACCOUNTED = "AI_PROFILE_METRIC_UNACCOUNTED"
ERR_MEASUREMENT_CLASS = "AI_PROFILE_MEASUREMENT_CLASS_INVALID"
ERR_TOKEN_COUNT = "AI_PROFILE_TOKEN_COUNT_INVALID"
ERR_LATENCY = "AI_PROFILE_LATENCY_INVALID"
ERR_USAGE_INVALID = "AI_PROFILE_USAGE_INVALID"

USAGE_KEYS = frozenset(
    {
        "total_input_tokens",
        "total_output_tokens",
        "cached_input_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
    }
)


class ProfileInputError(ValueError):
    """Value-free rejection of malformed normalizer input."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _is_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _is_latency(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _namespaced(keys: Mapping[Any, Any]) -> list[str]:
    return sorted(key for key in keys if isinstance(key, str) and key.startswith(NAMESPACE_PREFIX))


def profile_errors(event: Any) -> list[str]:
    """Return value-free profile errors for one ForgeEvent.v1 object.

    An event without ``ai.`` keys and without the declaration returns ``[]``.
    The caller validates the ForgeEvent.v1 envelope separately. Malformed
    input yields an error code; this function does not raise.
    """

    if not isinstance(event, Mapping):
        return [f"{ERR_EVENT_INVALID}: event"]
    attributes = event.get("attributes")
    metrics = event.get("metrics")
    if not isinstance(attributes, Mapping) or not isinstance(metrics, Mapping):
        return [f"{ERR_EVENT_INVALID}: attributes/metrics"]

    namespaced = _namespaced(attributes) + _namespaced(metrics)
    if PROFILE_ATTRIBUTE not in attributes:
        return [f"{ERR_UNDECLARED}: {key}" for key in namespaced]
    declaration = attributes[PROFILE_ATTRIBUTE]
    if not isinstance(declaration, str) or declaration != PROFILE_NAME:
        return [f"{ERR_DECLARATION_INVALID}: {PROFILE_ATTRIBUTE}"]

    errors: list[str] = []
    errors += [
        f"{ERR_UNKNOWN_KEY}: attributes.{key}"
        for key in _namespaced(attributes)
        if key not in PROFILE_ATTRIBUTES
    ]
    errors += [
        f"{ERR_UNKNOWN_KEY}: metrics.{key}"
        for key in _namespaced(metrics)
        if key not in PROFILE_METRICS
    ]
    for section, keys in (("attributes", attributes), ("metrics", metrics)):
        errors += [
            f"{ERR_FORBIDDEN_KEY}: {section}.{key}"
            for key in sorted(k for k in keys if isinstance(k, str))
            if key in FORBIDDEN_KEYS
        ]
    errors += [
        f"{ERR_RETIRED_METRIC}: metrics.{key}"
        for key in sorted(k for k in metrics if isinstance(k, str))
        if key in RETIRED_METRICS
    ]

    unavailable = attributes.get(UNAVAILABLE_ATTRIBUTE)
    listed = list(unavailable) if isinstance(unavailable, list) else []
    # Account for every known name even when the list is not canonical, so one
    # ordering fault is reported once and does not cascade.
    listed_set = {name for name in listed if isinstance(name, str) and name in PROFILE_METRICS}
    if (
        not isinstance(unavailable, list)
        or len(listed_set) != len(listed)
        or listed != sorted(listed_set)
    ):
        errors.append(f"{ERR_UNAVAILABLE_NOT_CANONICAL}: {UNAVAILABLE_ATTRIBUTE}")

    # Exactly-once accounting is meaningful only when the list is a list.
    for name in PROFILE_METRICS if isinstance(unavailable, list) else ():
        present = name in metrics
        if present and name in listed_set:
            errors.append(f"{ERR_METRIC_DUPLICATED}: {name}")
        elif not present and name not in listed_set:
            errors.append(f"{ERR_METRIC_UNACCOUNTED}: {name}")

    errors += [
        f"{ERR_TOKEN_COUNT}: {name}"
        for name in TOKEN_METRICS
        if name in metrics and not _is_count(metrics[name])
    ]
    if LATENCY_METRIC in metrics and not _is_latency(metrics[LATENCY_METRIC]):
        errors.append(f"{ERR_LATENCY}: {LATENCY_METRIC}")

    if MEASUREMENT_CLASS_ATTRIBUTE in attributes:
        measurement_class = attributes[MEASUREMENT_CLASS_ATTRIBUTE]
        # Type-check before the set lookup: an unhashable value must be a
        # controlled rejection, not a TypeError.
        if not isinstance(measurement_class, str) or measurement_class not in MEASUREMENT_CLASSES:
            errors.append(f"{ERR_MEASUREMENT_CLASS}: {MEASUREMENT_CLASS_ATTRIBUTE}")
    elif any(name in metrics for name in TOKEN_METRICS):
        errors.append(f"{ERR_MEASUREMENT_CLASS}: {MEASUREMENT_CLASS_ATTRIBUTE}")

    return errors


def normalize_token_usage(usage: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map a producer's usage totals to the five disjoint profile classes.

    Input keys, each a non-negative integer or ``None`` (not measured):
    ``total_input_tokens`` (includes both cache classes),
    ``total_output_tokens`` (includes reasoning), ``cached_input_tokens``,
    ``cache_write_tokens``, ``reasoning_tokens``. ``None`` for the whole
    usage means nothing was measured.

    Derived classes need every operand:

    - ``uncached = total_input - cached - cache_write``, only when all three
      are known;
    - ``output = total_output - reasoning``, only when both are known.

    An unknown operand never counts as zero. A known zero is kept. A negative
    remainder (an inconsistent report) makes the derived class unknown. An
    unknown class is listed as unavailable, never zero. Malformed input raises
    :class:`ProfileInputError` with a value-free code.
    """

    if usage is None:
        usage = {}
    if not isinstance(usage, Mapping):
        raise ProfileInputError(ERR_USAGE_INVALID)
    if any(not isinstance(key, str) or key not in USAGE_KEYS for key in usage):
        raise ProfileInputError(ERR_USAGE_INVALID)

    def count(key: str) -> int | None:
        value = usage.get(key)
        if value is None:
            return None
        if not _is_count(value):
            raise ProfileInputError(ERR_TOKEN_COUNT)
        return value

    total_input = count("total_input_tokens")
    total_output = count("total_output_tokens")
    cached = count("cached_input_tokens")
    cache_write = count("cache_write_tokens")
    reasoning = count("reasoning_tokens")

    uncached: int | None = None
    if total_input is not None and cached is not None and cache_write is not None:
        remainder = total_input - cached - cache_write
        uncached = remainder if remainder >= 0 else None

    output: int | None = None
    if total_output is not None and reasoning is not None:
        remainder = total_output - reasoning
        output = remainder if remainder >= 0 else None

    classes = {
        "ai.uncached_input_tokens": uncached,
        "ai.cached_input_tokens": cached,
        "ai.cache_write_tokens": cache_write,
        "ai.reasoning_tokens": reasoning,
        "ai.output_tokens": output,
    }
    return {
        "metrics": {name: value for name, value in classes.items() if value is not None},
        "unavailable_metrics": sorted(name for name, value in classes.items() if value is None),
    }

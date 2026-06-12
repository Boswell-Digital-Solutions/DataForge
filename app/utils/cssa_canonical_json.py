"""Canonical JSON serialization (RFC 8785 JCS-compatible) — CSSA ledger copy.

This MUST stay byte-identical in behavior to ForgeAgents
app/contracts/canonical_json.py: the ledger recomputes record hashes that
the ForgeAgents CSSA recorder produced with that implementation.

Provides deterministic JSON serialization for hash computation.
This MUST match the TypeScript implementation in contracts/canonical_json.ts.

Rules:
- UTF-8 encoding
- Objects: keys sorted lexicographically by Unicode codepoint
- Arrays: preserve order
- Numbers: minimal representation (no trailing zeros)
- No whitespace between tokens
- Output as bytes
"""

import json
from decimal import Decimal
from typing import Any


def canonicalize_json(value: Any) -> bytes:
    """Serialize a value to canonical JSON bytes (RFC 8785 JCS).

    Args:
        value: Any JSON-serializable value

    Returns:
        UTF-8 encoded canonical JSON bytes

    Raises:
        TypeError: If value contains non-JSON-serializable types
    """
    canonical_str = _serialize(value)
    return canonical_str.encode("utf-8")


def _serialize(value: Any) -> str:
    """Recursively serialize value to canonical JSON string.

    Handles:
    - None -> null
    - bool -> true/false
    - int/float -> number (canonical form)
    - str -> quoted string with escapes
    - list -> array (preserve order)
    - dict -> object (sorted keys)
    """
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return _serialize_number(value)

    if isinstance(value, Decimal):
        return _serialize_decimal(value)

    if isinstance(value, str):
        return _serialize_string(value)

    if isinstance(value, (list, tuple)):
        items = [_serialize(item) for item in value]
        return "[" + ",".join(items) + "]"

    if isinstance(value, dict):
        # Sort keys lexicographically by Unicode codepoint
        sorted_keys = sorted(value.keys(), key=lambda k: k.encode("utf-8"))
        pairs = [_serialize_string(k) + ":" + _serialize(value[k]) for k in sorted_keys]
        return "{" + ",".join(pairs) + "}"

    raise TypeError(f"Cannot serialize type {type(value).__name__} to canonical JSON")


def _serialize_number(value: float) -> str:
    """Serialize float to canonical form.

    RFC 8785 rules:
    - No exponential notation for numbers that fit in normal range
    - No unnecessary trailing zeros
    - Use exponential notation for very large/small numbers
    """
    if value != value:  # NaN check
        raise ValueError("NaN is not allowed in canonical JSON")
    if value == float("inf") or value == float("-inf"):
        raise ValueError("Infinity is not allowed in canonical JSON")

    # Check if it's actually an integer
    if value == int(value) and abs(value) < 2**53:
        return str(int(value))

    # Use Python's repr for floats, but clean up
    # json.dumps produces valid canonical output for most floats
    result = json.dumps(value)
    return result


def _serialize_decimal(value: Decimal) -> str:
    """Serialize Decimal to canonical form."""
    if value.is_nan():
        raise ValueError("NaN is not allowed in canonical JSON")
    if value.is_infinite():
        raise ValueError("Infinity is not allowed in canonical JSON")

    # Check if integer
    if value == value.to_integral_value():
        return str(int(value))

    # Normalize and convert
    normalized = value.normalize()
    return str(normalized)


def _serialize_string(value: str) -> str:
    """Serialize string with proper escaping.

    RFC 8785 requires:
    - Control characters U+0000-U+001F must be escaped
    - Backslash and quote must be escaped
    - Other characters passed through as-is (UTF-8)
    """
    result = ['"']
    for char in value:
        code = ord(char)
        if char == '"':
            result.append('\\"')
        elif char == "\\":
            result.append("\\\\")
        elif char == "\b":
            result.append("\\b")
        elif char == "\f":
            result.append("\\f")
        elif char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        elif code < 0x20:
            # Other control characters as \uXXXX
            result.append(f"\\u{code:04x}")
        else:
            result.append(char)
    result.append('"')
    return "".join(result)

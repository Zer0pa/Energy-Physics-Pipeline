"""Canonical JSON serialisation + content-addressable IDs.

Canonical JSON: sorted keys, no whitespace, ASCII-safe, stable float representation. Used
for envelope_id and dro_id.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

import orjson


def _normalise(obj: Any) -> Any:
    """Coerce floats and tuples; reject NaN/inf for content-addressable hashing."""
    if isinstance(obj, dict):
        return {str(k): _normalise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalise(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("Canonical JSON forbids NaN/inf in payload (boundary on hash stability)")
        return obj
    return obj


def canonical_json(obj: Any) -> bytes:
    """Return canonical JSON (UTF-8 bytes, sorted keys, no whitespace, ASCII-safe)."""
    norm = _normalise(obj)
    return orjson.dumps(
        norm,
        option=orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS,
    )


def sha256_of(obj: Any) -> str:
    """Return sha256 hex digest of `obj` rendered as canonical JSON."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def content_id(obj: Any) -> str:
    """Return 'sha256:<hex>' content-addressable identifier."""
    return f"sha256:{sha256_of(obj)}"

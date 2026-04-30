"""Contract tests for canonical JSON serialisation."""
from __future__ import annotations

import math

import pytest

from energy_pipeline.schemas import canonical_json, content_id, sha256_of


def test_canonical_json_sorts_keys():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b == b'{"a":2,"b":1}'


def test_canonical_json_no_whitespace():
    a = canonical_json({"x": [1, 2, {"y": 3}]})
    assert b" " not in a


def test_content_id_starts_with_sha256_prefix():
    cid = content_id({"a": 1})
    assert cid.startswith("sha256:")
    assert len(cid) == len("sha256:") + 64


def test_content_id_stable_under_key_reorder():
    assert content_id({"a": 1, "b": 2, "c": 3}) == content_id({"c": 3, "a": 1, "b": 2})


def test_canonical_json_rejects_nan():
    with pytest.raises(ValueError):
        canonical_json({"x": math.nan})


def test_canonical_json_rejects_inf():
    with pytest.raises(ValueError):
        canonical_json({"x": math.inf})


def test_sha256_deterministic():
    s1 = sha256_of({"a": 1, "b": [1, 2, 3]})
    s2 = sha256_of({"b": [1, 2, 3], "a": 1})
    assert s1 == s2
    assert len(s1) == 64

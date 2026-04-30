"""Integration tests for the real OMAS-backed L4 path validator.

All tests must complete within 30 seconds total.

Test matrix
-----------
test_omas_real_path_validates_all_4_paths
    Populates an ODS with the 4 canonical paths (q_axis, q profile,
    electron density, electron temperature) and asserts all 4 validate.
    This exercises the real OMAS Data Dictionary path on CPU.

test_omas_invalid_path_fails
    Adds a deliberately misspelled path ``equilibrium.time_slice.0.bad_typo``
    to the validated set.  Asserts it appears in falsification failures and
    that gate_status is ``fail``.

test_omas_forbidden_intent_raises
    Verifies that an intent string containing "weapon yield" raises
    BoundaryViolation before any OMAS work is attempted.

test_omas_envelope_carries_boundary
    Confirms the returned envelope's ``boundary`` field is byte-identical to
    ``BOUNDARY_BLOCK`` and that ``envelope_id`` starts with ``sha256:``.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from energy_pipeline.boundary import BOUNDARY_BLOCK, BoundaryViolation
from energy_pipeline.schemas.envelope import GateStatus
from energy_pipeline.adapters.fusion.l4_omas import OmasRealValidatorAdapter, OmasValidateSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter() -> OmasRealValidatorAdapter:
    return OmasRealValidatorAdapter(agent_id="test.fusion.l4.omas", git_sha="test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_omas_real_path_validates_all_4_paths(tmp_path: Path) -> None:
    """Real OMAS path: all 4 canonical paths must validate (n_valid==4, n_invalid==0)."""
    start = time.monotonic()

    adapter = _make_adapter()
    spec = OmasValidateSpec(
        intent="OMAS path validation against research-bound fixture",
        ods_paths=[
            "equilibrium.time_slice.0.global_quantities.q_axis",
            "equilibrium.time_slice.0.profiles_1d.q",
            "core_profiles.profiles_1d.0.electrons.density",
            "core_profiles.profiles_1d.0.electrons.temperature",
        ],
        data_dictionary_version="3.41.0",
        campaign_id="fusion-l4-omas",
    )

    env = adapter.run(spec)
    payload = env.outputs.payload

    # Functional assertions
    assert payload["total_paths_checked"] == 4, f"Expected 4 paths checked, got {payload['total_paths_checked']}"
    assert payload["n_valid"] == 4, (
        f"Expected n_valid=4, got {payload['n_valid']}. "
        f"Per-path results: {payload['per_path_results']}"
    )
    assert payload["n_invalid"] == 0, (
        f"Expected n_invalid=0, got {payload['n_invalid']}. "
        f"Failures: {env.falsification.failures}"
    )

    # Gate and scientific validity
    assert env.falsification.gate_status == GateStatus.pass_, (
        f"Expected gate_status=pass, got {env.falsification.gate_status}. "
        f"Failures: {env.falsification.failures}"
    )
    assert env.falsification.scientific_valid is True, (
        "Expected scientific_valid=True on the real OMAS path. "
        "OMAS may not be available — check installation."
    )

    # OMAS metadata present
    assert payload["omas_available"] is True, "OMAS must be importable for the real-path test"
    assert payload["omas_version"] != "unavailable"
    assert payload["dd_version"] == "3.41.0"

    # quantities block
    assert payload["quantities"]["n_paths_valid"]["value"] == 4
    assert payload["quantities"]["n_paths_valid"]["unit"] == "1"

    elapsed = time.monotonic() - start
    assert elapsed < 30, f"Test took {elapsed:.1f}s, must be < 30s"


@pytest.mark.integration
def test_omas_invalid_path_fails(tmp_path: Path) -> None:
    """A misspelled path must appear in failures and set gate_status=fail."""
    adapter = _make_adapter()
    spec = OmasValidateSpec(
        intent="OMAS path validation against research-bound fixture",
        ods_paths=[
            "equilibrium.time_slice.0.global_quantities.q_axis",
            "equilibrium.time_slice.0.bad_typo",  # deliberately wrong
        ],
        data_dictionary_version="3.41.0",
        campaign_id="fusion-l4-omas",
    )

    env = adapter.run(spec)
    payload = env.outputs.payload

    assert payload["n_invalid"] >= 1, (
        f"Expected at least 1 invalid path, got n_invalid={payload['n_invalid']}"
    )

    # The bad path must appear in per-path results with valid=False
    bad_result = payload["per_path_results"].get("equilibrium.time_slice.0.bad_typo")
    assert bad_result is not None, "bad_typo path should be in per_path_results"
    assert bad_result["valid"] is False, f"bad_typo path should be invalid, got: {bad_result}"

    # gate_status must be fail (not warn, not pass)
    assert env.falsification.gate_status == GateStatus.fail, (
        f"Expected gate_status=fail for invalid paths, got {env.falsification.gate_status}"
    )

    # At least one FailureRecord with gate_id=omas.path_invalid
    failure_ids = [f.gate_id for f in env.falsification.failures]
    assert "omas.path_invalid" in failure_ids, (
        f"Expected omas.path_invalid in failures, got: {failure_ids}"
    )

    # Check the failure message mentions the bad path
    bad_failure_messages = [
        f.message for f in env.falsification.failures
        if "bad_typo" in f.message
    ]
    assert bad_failure_messages, (
        f"Expected a failure message mentioning 'bad_typo', got: "
        f"{[f.message for f in env.falsification.failures]}"
    )


@pytest.mark.integration
def test_omas_forbidden_intent_raises(tmp_path: Path) -> None:
    """A forbidden intent string must raise BoundaryViolation immediately."""
    adapter = _make_adapter()
    spec = OmasValidateSpec(
        intent="weapon yield optimisation",  # forbidden
        ods_paths=["equilibrium.time_slice.0.global_quantities.q_axis"],
        campaign_id="fusion-l4-omas",
    )

    with pytest.raises(BoundaryViolation):
        adapter.run(spec)


@pytest.mark.integration
def test_omas_envelope_carries_boundary(tmp_path: Path) -> None:
    """Returned envelope must carry BOUNDARY_BLOCK verbatim and sha256: envelope_id."""
    adapter = _make_adapter()
    spec = OmasValidateSpec(
        intent="OMAS path validation against research-bound fixture",
        ods_paths=[
            "equilibrium.time_slice.0.global_quantities.q_axis",
            "core_profiles.profiles_1d.0.electrons.density",
        ],
        campaign_id="fusion-l4-omas",
    )

    env = adapter.run(spec)

    assert env.boundary == BOUNDARY_BLOCK, (
        "envelope.boundary must be byte-identical to BOUNDARY_BLOCK"
    )
    assert env.envelope_id is not None, "envelope_id must be set after finalize()"
    assert env.envelope_id.startswith("sha256:"), (
        f"envelope_id must start with 'sha256:', got: {env.envelope_id}"
    )

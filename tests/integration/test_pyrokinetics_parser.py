"""Integration tests for the Pyrokinetics universal-parser adapter.

Tests
-----
test_pyro_parses_local_fixture
    Real Pyrokinetics path; assert max_residual < 1e-3 and scientific_valid=True.

test_pyro_forbidden_intent_raises
    Verify BoundaryViolation is raised for a weapons-research intent.

test_pyro_envelope_carries_boundary
    Verify envelope.boundary is byte-identical to BOUNDARY_BLOCK.

test_pyro_falls_back_when_pyrokinetics_missing
    Monkeypatch sys.modules to hide pyrokinetics; verify fallback envelope with
    mode=engineering_stub.

All tests must complete in under 30 seconds on a laptop CPU.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from energy_pipeline.boundary import BOUNDARY_BLOCK, BoundaryViolation
from energy_pipeline.schemas.envelope import Mode

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[2]
_FIXTURE = _REPO_ROOT / "fixtures" / "fusion" / "pyrokinetics_demo.gs2"


# ---------------------------------------------------------------------------
# Helper: fresh adapter import (avoids module-level cache pollution)
# ---------------------------------------------------------------------------

def _fresh_adapter():
    """Re-import the adapter module and return a new adapter instance."""
    import energy_pipeline.adapters.fusion.l2_pyrokinetics as mod
    importlib.reload(mod)
    return mod.PyrokineticsParserAdapter(), mod.PyroParseSpec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pyro_parses_local_fixture():
    """Real Pyrokinetics path: load fixture GS2 -> CGYRO round-trip.

    Assertions
    ----------
    - max_residual < 1e-3  (tight acceptance gate)
    - scientific_valid == True
    - mode == Mode.scientific
    - outputs contain expected keys
    - envelope_id is set (sha256:… content-address)
    """
    from energy_pipeline.adapters.fusion.l2_pyrokinetics import (
        PyroParseSpec,
        PyrokineticsParserAdapter,
    )

    assert _FIXTURE.is_file(), f"Fixture not found: {_FIXTURE}"

    spec = PyroParseSpec(
        intent="gyrokinetic input parsing for research",
        input_path=_FIXTURE,
        input_kind="GS2",
        target_kind="CGYRO",
        campaign_id="fusion-l2-pyro",
    )
    adapter = PyrokineticsParserAdapter()
    env = adapter.run(spec)

    # Round-trip quality
    max_residual = env.outputs.payload["max_residual"]
    assert max_residual < 1e-3, (
        f"Round-trip residual {max_residual:.3e} exceeds 1e-3 acceptance gate; "
        f"residuals per parameter: {env.outputs.payload.get('round_trip_residuals')}"
    )

    # Envelope mode & validity
    assert env.falsification.scientific_valid is True, (
        "scientific_valid must be True when max_residual < 1e-3 and Pyrokinetics is available"
    )
    assert env.mode == Mode.scientific

    # Payload structure
    payload = env.outputs.payload
    for key in ("input_kind", "target_kind", "round_trip_residuals", "max_residual",
                "n_parameters_compared", "quantities"):
        assert key in payload, f"Missing key in outputs.payload: {key}"

    assert payload["n_parameters_compared"] == 4, (
        "Expected 4 parameters compared: q, shat, beta, ti_te"
    )
    assert "max_round_trip_residual" in payload["quantities"]
    assert payload["quantities"]["max_round_trip_residual"]["unit"] == "1"

    # Envelope identity
    assert env.envelope_id is not None
    assert env.envelope_id.startswith("sha256:")


def test_pyro_forbidden_intent_raises():
    """Boundary gate: weapons-related intent must raise BoundaryViolation."""
    from energy_pipeline.adapters.fusion.l2_pyrokinetics import (
        PyroParseSpec,
        PyrokineticsParserAdapter,
    )

    spec = PyroParseSpec(
        intent="weapon yield study",
        input_path=_FIXTURE,
        input_kind="GS2",
        target_kind="CGYRO",
    )
    adapter = PyrokineticsParserAdapter()
    with pytest.raises(BoundaryViolation):
        adapter.run(spec)


def test_pyro_envelope_carries_boundary():
    """Envelope boundary field must be byte-identical to BOUNDARY_BLOCK."""
    from energy_pipeline.adapters.fusion.l2_pyrokinetics import (
        PyroParseSpec,
        PyrokineticsParserAdapter,
    )

    spec = PyroParseSpec(input_path=_FIXTURE)
    adapter = PyrokineticsParserAdapter()
    env = adapter.run(spec)

    assert env.boundary == BOUNDARY_BLOCK, (
        "Envelope boundary field is mutated or missing; boundary check failed"
    )


def test_pyro_falls_back_when_pyrokinetics_missing(monkeypatch):
    """When pyrokinetics is absent, the adapter emits an engineering_stub envelope.

    Uses monkeypatch to hide pyrokinetics from sys.modules, then reloads the
    adapter module so the import attempt fails.

    Assertions
    ----------
    - mode == Mode.engineering_stub
    - scientific_valid == False
    - At least one FailureRecord with gate_id 'pyrokinetics.import'
    - envelope_id is set (content-addressed even for stub)
    - boundary == BOUNDARY_BLOCK
    """
    # Stub pyrokinetics out of sys.modules before reloading.
    monkeypatch.setitem(sys.modules, "pyrokinetics", None)

    # Reload the adapter so its module-level state picks up the monkeypatched import.
    import energy_pipeline.adapters.fusion.l2_pyrokinetics as mod
    importlib.reload(mod)

    spec = mod.PyroParseSpec(input_path=_FIXTURE)
    adapter = mod.PyrokineticsParserAdapter()
    env = adapter.run(spec)

    assert env.mode == Mode.engineering_stub, (
        f"Expected engineering_stub when Pyrokinetics is absent, got {env.mode}"
    )
    assert env.falsification.scientific_valid is False

    gate_ids = [f.gate_id for f in env.falsification.failures]
    assert "pyrokinetics.import" in gate_ids, (
        f"Expected 'pyrokinetics.import' FailureRecord; got gate_ids={gate_ids}"
    )

    assert env.envelope_id is not None
    assert env.envelope_id.startswith("sha256:")
    assert env.boundary == BOUNDARY_BLOCK

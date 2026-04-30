"""Integration tests for VQE H2 smoke fixture.

Tests guard:
  1. VQE convergence: |delta_E| < 50 mHa from FCI reference
  2. Envelope boundary discipline
  3. No quantum advantage claims in the output payload
  4. Fallback to engineering_stub when qiskit is absent

All tests run CPU-only and complete within 60s wall time.
"""
from __future__ import annotations

import json
import sys

import pytest

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.adapters.electrochem.l1_quantum import VqeH2Adapter, VqeH2Spec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def default_env():
    """Run VQE once for the module; reused across tests that need the result."""
    adapter = VqeH2Adapter()
    spec = VqeH2Spec()
    return adapter.run(spec)


# ---------------------------------------------------------------------------
# Test 1: convergence
# ---------------------------------------------------------------------------

def test_vqe_h2_converges(default_env):
    """VQE must converge to FCI within 50 mHa for H2 STO-3G at 0.74 Ang.

    PRD acceptance gate: |E_VQE - E_FCI| < convergence_threshold_ha = 0.05 Ha.
    This is deliberately loose (50 mHa) to accommodate the noise-free CPU smoke
    running within max_iterations=120.
    """
    env = default_env
    payload = env.outputs.payload

    assert "E_VQE_hartree" in payload, "E_VQE_hartree missing from payload"
    assert "E_FCI_hartree" in payload, "E_FCI_hartree missing from payload"
    assert "delta_E_hartree" in payload, "delta_E_hartree missing from payload"

    e_vqe = payload["E_VQE_hartree"]
    e_fci = payload["E_FCI_hartree"]
    delta = abs(e_vqe - e_fci)

    assert e_vqe is not None, "E_VQE_hartree is None (fallback?)"
    assert e_fci is not None, "E_FCI_hartree is None (fallback?)"

    # FCI reference sanity: H2 STO-3G at 0.74 Ang is approximately -1.137 Ha
    assert -1.20 < e_fci < -1.10, (
        f"E_FCI={e_fci:.6f} Ha outside expected range [-1.20, -1.10] Ha "
        f"for H2 STO-3G at 0.74 Ang"
    )

    assert delta < 0.05, (
        f"|E_VQE - E_FCI| = {delta * 1000:.2f} mHa "
        f"(limit: 50 mHa); VQE did not converge within threshold. "
        f"E_VQE={e_vqe:.6f}, E_FCI={e_fci:.6f}"
    )

    # Mode must be scientific iff converged
    from energy_pipeline.schemas.envelope import Mode
    assert env.mode == Mode.scientific, (
        f"mode={env.mode!r} but delta_E={delta*1000:.2f} mHa < 50 mHa — "
        f"should be Mode.scientific"
    )

    # Falsification block must reflect convergence
    assert env.falsification.scientific_valid is True, (
        "scientific_valid=False despite converging within threshold"
    )

    # quantities sub-dict
    quantities = payload.get("quantities", {})
    assert "E_VQE" in quantities
    assert "E_FCI" in quantities
    assert "delta_E" in quantities
    assert quantities["E_VQE"]["unit"] == "hartree"
    assert quantities["E_FCI"]["unit"] == "hartree"
    assert quantities["delta_E"]["unit"] == "hartree"


# ---------------------------------------------------------------------------
# Test 2: boundary discipline
# ---------------------------------------------------------------------------

def test_vqe_h2_envelope_carries_boundary(default_env):
    """Every envelope must carry the verbatim BOUNDARY_BLOCK string."""
    env = default_env
    assert env.boundary == BOUNDARY_BLOCK, (
        f"boundary string mutated. Got:\n{env.boundary!r}\nExpected:\n{BOUNDARY_BLOCK!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: no quantum advantage claims
# ---------------------------------------------------------------------------

def test_vqe_h2_no_quantum_advantage_claim(default_env):
    """The output payload must NOT contain quantum-advantage or quantum-supremacy claims.

    This is a boundary discipline test per PRD: 'No quantum advantage claims.'
    The test searches the full JSON-serialised payload (case-insensitive).
    """
    env = default_env
    payload_json = json.dumps(env.outputs.payload).lower()

    forbidden_phrases = [
        "quantum advantage",
        "quantum supremacy",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in payload_json, (
            f"Forbidden phrase {phrase!r} found in output payload. "
            f"This violates the PRD boundary: 'No quantum advantage claims.'"
        )


# ---------------------------------------------------------------------------
# Test 4: fallback when qiskit missing
# ---------------------------------------------------------------------------

def test_vqe_h2_falls_back_when_qiskit_missing(monkeypatch):
    """When qiskit is monkeypatched out, adapter must return engineering_stub.

    This guards the fallback discipline: the adapter must not crash and must
    emit a valid envelope even in degraded environments.
    """
    from energy_pipeline.schemas.envelope import Mode

    # Block qiskit imports
    monkeypatch.setitem(sys.modules, "qiskit", None)

    # Re-instantiate adapter so __init__ sees the blocked import
    adapter = VqeH2Adapter()
    assert not adapter._has_qiskit, "Adapter should detect qiskit as unavailable"

    spec = VqeH2Spec()
    env = adapter.run(spec)

    assert env.mode == Mode.engineering_stub, (
        f"Expected engineering_stub fallback, got mode={env.mode!r}"
    )
    assert env.falsification.scientific_valid is False, (
        "engineering_stub must not claim scientific_valid=True"
    )
    assert env.boundary == BOUNDARY_BLOCK, "Fallback envelope missing BOUNDARY_BLOCK"

    # Payload must be structurally valid (no crash)
    payload = env.outputs.payload
    assert "E_VQE_hartree" in payload
    assert "n_qubits" in payload
    assert payload["n_qubits"] == 4

    # Fallback must mention the missing dependency
    assert "fallback_reason" in payload or any(
        "qiskit" in (f.message or "").lower()
        for f in env.falsification.failures
    ), "Fallback should mention missing qiskit"


# ---------------------------------------------------------------------------
# Additional structural guard: n_qubits = 4
# ---------------------------------------------------------------------------

def test_vqe_h2_reports_four_qubits(default_env):
    """Payload must declare n_qubits=4 (H2 STO-3G 4 spin-orbitals)."""
    assert default_env.outputs.payload.get("n_qubits") == 4


# ---------------------------------------------------------------------------
# Additional structural guard: layer and sub_vertical
# ---------------------------------------------------------------------------

def test_vqe_h2_layer_and_subvertical(default_env):
    """Envelope must be L1 in electrochemistry sub-vertical."""
    from energy_pipeline.schemas.envelope import LayerLevel, SubVertical

    assert default_env.layer == LayerLevel.L1
    assert default_env.sub_vertical == SubVertical.electrochemistry

"""Integration test: PyBOP parameter inference adapter end-to-end.

Tests the PyBOPParameterInferenceAdapter on the Chen2020 SPM.  If pybop and
pybamm are available the real inference path is exercised; otherwise the
deterministic fixture path is verified.

Wall-time budget: < 120 s (enforced by the test via pytest-timeout if
installed; also a manual time guard inside the test body).
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Detect whether pybop + pybamm are available (used for conditional asserts)
# ---------------------------------------------------------------------------
try:
    import pybop as _pybop          # noqa: F401
    import pybamm as _pybamm        # noqa: F401
    _REAL_PATH_AVAILABLE = True
except (ImportError, AttributeError):
    _REAL_PATH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Imports from the pipeline
# ---------------------------------------------------------------------------
from energy_pipeline.adapters.electrochem.l4_pybop import (
    PyBOPInferenceSpec,
    PyBOPParameterInferenceAdapter,
)
from energy_pipeline.audit import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.kg import KGStore
from energy_pipeline.schemas.dro import DeviceFamily, DeviceResponseObject
from energy_pipeline.schemas.envelope import GateStatus, Mode


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    kg_dir = tmp_path / "kg"
    audit_dir.mkdir()
    kg_dir.mkdir()
    return audit_dir, kg_dir


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def test_pybop_inference_end_to_end(tmp_dirs):
    """Run PyBOP inference adapter end-to-end; verify envelope, DRO, KG, audit.

    Uses n_iterations=50 to keep CPU wall time well under 60 s.
    """
    audit_dir, kg_dir = tmp_dirs
    t_wall_start = time.monotonic()

    spec = PyBOPInferenceSpec(n_iterations=50)
    adapter = PyBOPParameterInferenceAdapter()

    audit = AuditWriter(jsonl_dir=audit_dir, db_path=audit_dir / "audit.duckdb")
    kg = KGStore(kg_dir=kg_dir)
    try:
        envelope, dro = adapter.run(spec, audit_writer=audit, kg_store=kg)
    finally:
        # Keep audit open until all assertions are done; close at end of test.
        pass

    elapsed = time.monotonic() - t_wall_start

    # ------------------------------------------------------------------
    # 1. Wall-time guard
    # ------------------------------------------------------------------
    assert elapsed < 120.0, f"Inference took {elapsed:.1f}s, expected < 120s"

    # ------------------------------------------------------------------
    # 2. Envelope — mode and boundary
    # ------------------------------------------------------------------
    assert envelope.mode in (Mode.scientific, Mode.engineering_stub), (
        f"Unexpected mode: {envelope.mode}"
    )
    assert envelope.boundary == BOUNDARY_BLOCK, "Boundary block mutated in envelope"
    assert envelope.envelope_id is not None
    assert envelope.envelope_id.startswith("sha256:")

    # ------------------------------------------------------------------
    # 3. Conditional assertions depending on path
    # ------------------------------------------------------------------
    payload = envelope.outputs.payload

    if envelope.mode == Mode.scientific:
        # Real PyBOP path
        assert envelope.falsification.scientific_valid is True

        recovered = payload["recovered_mean"]
        gt_val = payload["ground_truth"]
        rel_err = payload["relative_error"]

        assert math.isfinite(recovered), "Recovered parameter is not finite"
        assert math.isfinite(gt_val), "Ground truth value is not finite"
        assert math.isfinite(rel_err), "Relative error is not finite"

        # Relative error < 50% (adapter constraint: warn at 50%, fail at 100%)
        assert rel_err < 0.50, (
            f"Relative error {rel_err:.3f} exceeds 50%; "
            "SPM may not be sensitive enough to D_neg over this window — "
            "increase duration_s or C-rate in the spec for better identifiability"
        )

        # Gate status must be pass or warn (not fail)
        assert envelope.falsification.gate_status in (GateStatus.pass_, GateStatus.warn), (
            f"Unexpected gate_status: {envelope.falsification.gate_status}"
        )

        # Quantities block present
        assert "quantities" in payload
        recovered_qty = payload["quantities"]["recovered_value"]
        assert math.isfinite(recovered_qty["value"])
        assert recovered_qty["unit"] != ""

    else:
        # Fixture / engineering_stub path
        assert envelope.falsification.scientific_valid is False
        assert envelope.falsification.gate_status == GateStatus.pass_, (
            "Fixture path should always pass falsification gate"
        )

    # ------------------------------------------------------------------
    # 4. DRO
    # ------------------------------------------------------------------
    assert isinstance(dro, DeviceResponseObject)
    assert dro.device_family == DeviceFamily.battery
    assert dro.dro_id is not None
    assert dro.dro_id.startswith("sha256:")
    assert dro.boundary == BOUNDARY_BLOCK, "Boundary block mutated in DRO"
    assert dro.handoff.l5_targets == ["pypsa", "pysam"]
    assert dro.response.scalar_metrics.capacity_Ah is not None
    assert dro.response.scalar_metrics.capacity_Ah > 0.0

    # ------------------------------------------------------------------
    # 5. KG: SimulationRun + DeviceResponseObject nodes + PRODUCED edge
    # ------------------------------------------------------------------
    stats = kg.stats()
    assert stats["nodes"] >= 2, "Expected at least 2 KG nodes (SimulationRun + DRO)"
    assert stats["edges"] >= 1, "Expected at least 1 KG edge (PRODUCED)"

    # Verify SimulationRun node carries boundary
    node_ids_found = set(kg._g.nodes())
    sim_run_id = envelope.envelope_id
    dro_node_id = dro.dro_id
    assert sim_run_id in node_ids_found, (
        f"SimulationRun node {sim_run_id!r} not in KG"
    )
    assert dro_node_id in node_ids_found, (
        f"DRO node {dro_node_id!r} not in KG"
    )

    # Verify PRODUCED edge src=SimulationRun -> dst=DRO
    edges = list(kg._g.out_edges(sim_run_id, data=True))
    assert any(
        d.get("kind") == "PRODUCED" for _, _, d in edges
    ), f"Expected a PRODUCED edge from {sim_run_id!r}"

    # Verify boundary is present in SimulationRun node attributes
    sim_node_data = kg._g.nodes[sim_run_id]
    assert sim_node_data["attrs"]["boundary"] == BOUNDARY_BLOCK

    # ------------------------------------------------------------------
    # 6. AuditWriter — events written without raising
    # ------------------------------------------------------------------
    count = audit.count()
    audit.close()
    # At least 2 events: envelope + DRO
    assert count >= 2, f"Expected at least 2 audit events, got {count}"

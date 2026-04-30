"""End-to-end integration test: L1 marcus -> L2 mlip-manifest -> L3 phasefield-stub
-> L4 PyBaMM -> DRO -> L5 PyPSA LCOE.

Each step writes envelope to AuditWriter and KG nodes/edges.
Must complete in < 60 seconds.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from energy_pipeline.adapters.electrochem import (
    ElectronicStructureAdapter,
    MLIPManifestAdapter,
    PyBaMMBatteryAdapter,
    PyPSALcoeAdapter,
    phasefield_stub,
    trajectory_msd,
)
from energy_pipeline.audit import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.kg import KGStore
from energy_pipeline.schemas.dro import DeviceResponseObject
from energy_pipeline.schemas.envelope import (
    LayerLevel,
    SubVertical,
)


@pytest.fixture
def tmp_dirs(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    kg_dir = tmp_path / "kg"
    audit_dir.mkdir()
    kg_dir.mkdir()
    return audit_dir, kg_dir


def test_full_pipeline_e2e(tmp_dirs):
    """L1 -> L2 -> L3 -> L4 -> DRO -> L5 end-to-end pipeline."""
    audit_dir, kg_dir = tmp_dirs

    with AuditWriter(jsonl_dir=audit_dir, db_path=audit_dir / "audit.duckdb") as audit:
        kg = KGStore(kg_dir=kg_dir)

        # ------------------------------------------------------------------
        # L1: Marcus electron transfer
        # ------------------------------------------------------------------
        l1 = ElectronicStructureAdapter()
        env_l1 = l1.marcus({"temperature_K": 298.15})
        assert env_l1.sub_vertical == SubVertical.electrochemistry
        assert env_l1.layer == LayerLevel.L1
        assert env_l1.boundary == BOUNDARY_BLOCK
        assert env_l1.envelope_id is not None

        from energy_pipeline.audit import write_envelope_event
        write_envelope_event(audit, env_l1)

        # KG: L1 SimulationRun + USED_TOOL
        kg.add_node(
            "SimulationRun",
            node_id=env_l1.envelope_id,
            attrs={"boundary": BOUNDARY_BLOCK, "layer": "L1", "tool": "marcus_fixture"},
            boundary_required=True,
        )
        kg.add_node(
            "ToolAdapter",
            node_id="tool:marcus_classical",
            attrs={"tool": "marcus_classical", "layer": "L1"},
            boundary_required=False,
        )
        kg.add_edge("USED_TOOL", src=env_l1.envelope_id, dst="tool:marcus_classical")

        # Falsifier: lambda_eV positive
        outputs = env_l1.outputs.payload
        assert outputs["lambda_eV"]["value"] > 0, "Marcus lambda must be positive"

        # ------------------------------------------------------------------
        # L2: MLIP manifest check
        # ------------------------------------------------------------------
        l2 = MLIPManifestAdapter()
        env_l2 = l2.manifest_envelope("mace-mp-0", kg_store=kg)
        assert env_l2.layer == LayerLevel.L2
        write_envelope_event(audit, env_l2)

        kg.add_node(
            "SimulationRun",
            node_id=env_l2.envelope_id,
            attrs={"boundary": BOUNDARY_BLOCK, "layer": "L2", "tool": "mlip_manifest"},
            boundary_required=True,
        )
        kg.add_edge("DERIVED_FROM", src=env_l2.envelope_id, dst=env_l1.envelope_id)

        # ------------------------------------------------------------------
        # L3: Phase-field stub
        # ------------------------------------------------------------------
        env_l3 = phasefield_stub({"porosity": 0.3})
        assert env_l3.layer == LayerLevel.L3
        write_envelope_event(audit, env_l3)

        kg.add_node(
            "SimulationRun",
            node_id=env_l3.envelope_id,
            attrs={"boundary": BOUNDARY_BLOCK, "layer": "L3", "tool": "phasefield_stub"},
            boundary_required=True,
        )
        kg.add_edge("DERIVED_FROM", src=env_l3.envelope_id, dst=env_l2.envelope_id)

        # ------------------------------------------------------------------
        # L4: PyBaMM battery
        # ------------------------------------------------------------------
        l4_battery = PyBaMMBatteryAdapter()
        env_l4, dro = l4_battery.run(
            spec={"c_rate": 1.0, "t_end_s": 600},
            audit_writer=audit,
            kg_store=kg,
        )

        assert env_l4.layer == LayerLevel.L4
        assert isinstance(dro, DeviceResponseObject)
        assert dro.dro_id is not None

        # DRO assertions
        curves = dro.response.curves
        assert len(curves) >= 1
        assert curves[0].x.unit == "s"
        assert curves[0].y.unit == "V"

        scalar = dro.response.scalar_metrics
        assert scalar.ocv_V is not None and scalar.ocv_V > 0
        assert scalar.capacity_Ah is not None and scalar.capacity_Ah > 0

        # L4 -> L3 edge
        kg.add_edge("FEEDS_L4", src=env_l3.envelope_id, dst=env_l4.envelope_id)

        # ------------------------------------------------------------------
        # L5: PyPSA LCOE
        # ------------------------------------------------------------------
        l5_lcoe = PyPSALcoeAdapter()
        env_l5 = l5_lcoe.run(
            spec={},
            audit_writer=audit,
            kg_store=kg,
            dro_node_id=dro.dro_id,
        )

        assert env_l5.layer == LayerLevel.L5
        assert env_l5.boundary == BOUNDARY_BLOCK

        # L5 LCOE p50 in [0.01, 0.50] USD/kWh
        lcoe_p50 = env_l5.outputs.payload["lcoe_p50_USD_kWh"]["value"]
        assert 0.01 <= lcoe_p50 <= 0.50, (
            f"LCOE p50 {lcoe_p50:.4f} USD/kWh outside [0.01, 0.50]"
        )

        lcoe_p05 = env_l5.outputs.payload["lcoe_p05_USD_kWh"]["value"]
        lcoe_p95 = env_l5.outputs.payload["lcoe_p95_USD_kWh"]["value"]
        assert lcoe_p05 <= lcoe_p50 <= lcoe_p95, "P5 <= P50 <= P95 ordering violated"

        # ------------------------------------------------------------------
        # KG assertions
        # ------------------------------------------------------------------
        stats = kg.stats()
        assert stats["nodes"] >= 5, f"Expected >=5 KG nodes, got {stats['nodes']}"
        assert stats["edges"] >= 3, f"Expected >=3 KG edges, got {stats['edges']}"

        # Neighbour traversal
        neighbours = kg.neighbours(env_l1.envelope_id)
        assert len(neighbours) > 0, "KG neighbour traversal returned no results for L1 node"

        # DRO -> L5 edge: FEEDS_L5
        feeds_l5_found = any(
            kind == "FEEDS_L5"
            for _, kind in kg.neighbours(dro.dro_id)
        )
        assert feeds_l5_found, "FEEDS_L5 edge from DRO to L5 not found in KG"

        # ------------------------------------------------------------------
        # Audit log assertions
        # ------------------------------------------------------------------
        count = audit.count()
        assert count >= 5, f"Expected >=5 audit events, got {count}"


def test_dro_emitted_and_valid(tmp_dirs):
    """Standalone: verify DRO is emitted and validates from L4 PyBaMM adapter."""
    audit_dir, kg_dir = tmp_dirs
    with AuditWriter(jsonl_dir=audit_dir, db_path=audit_dir / "audit.duckdb") as audit:
        kg = KGStore(kg_dir=kg_dir)
        l4 = PyBaMMBatteryAdapter()
        env, dro = l4.run(spec={}, audit_writer=audit, kg_store=kg)

    assert isinstance(dro, DeviceResponseObject)
    assert dro.dro_id is not None
    assert dro.dro_id.startswith("sha256:")
    assert dro.boundary == BOUNDARY_BLOCK

    # Re-finalize: dro_id should be stable under same data
    dro2 = dro.finalize()
    assert dro2.dro_id == dro.dro_id, "DRO finalize not idempotent"


def test_trajectory_msd_l2(tmp_dirs):
    """L2 MSD fixture: R^2 >= 0.95 and alpha in [0.8, 1.2]."""
    env = trajectory_msd({"n_steps": 200, "dt_ps": 1.0})
    payload = env.outputs.payload
    r2 = payload["msd_r2"]["value"]
    alpha = payload["diffusion_exponent_alpha"]["value"]
    assert r2 >= 0.95, f"MSD R^2 {r2:.4f} < 0.95"
    assert 0.8 <= alpha <= 1.2, f"Diffusion exponent alpha={alpha:.3f} outside [0.8, 1.2]"

"""End-to-end Phase-0 integration test for the fusion stack.

Path:
    L1 OpenMC tiny  ->  L2 TGLF reduced  ->  L3 FreeGS4E (or fixture)
    ->  L4 IMAS netCDF  ->  ReducedTransport (DRO)  ->  Reasoning bench (smoke 5)

Writes envelopes to AuditWriter and KG nodes (FusionScenario, PulseWindow,
SimulationRun, ReasonerTuple) with edges. Must complete in <90s.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from energy_pipeline.audit.writer import AuditWriter
from energy_pipeline.kg.graph import KGStore
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.adapters.fusion import (
    OpenMcManifestAdapter,
    TglfReducedAdapter,
    CgyroNonlinearAdapter,
    cross_model_disagreement,
    FreeGS4eAdapter,
    ImasPythonAdapter,
    ReducedTransportCpuAdapter,
    ParamakGeometryAdapter,
    OpenmcCsgFixedSourceAdapter,
    FusionReasoningBench,
    write_imas_fixture,
)
from energy_pipeline.adapters.fusion.l1 import OpenMcSpec
from energy_pipeline.adapters.fusion.l2 import GyroSpec
from energy_pipeline.adapters.fusion.l3 import EquilibriumSpec
from energy_pipeline.adapters.fusion.l4 import ImasReadSpec, TokamakScenarioSpec
from energy_pipeline.adapters.fusion.l5 import BlanketGeomSpec


@pytest.fixture()
def tmp_audit_kg(tmp_path: Path):
    aw = AuditWriter(jsonl_dir=tmp_path / "audit", db_path=tmp_path / "audit.duckdb")
    kg = KGStore(kg_dir=tmp_path / "kg")
    yield aw, kg
    aw.close()


def _write_envelope(writer: AuditWriter, env) -> str:
    payload = env.model_dump(mode="json")
    assert payload["boundary"] == BOUNDARY_BLOCK
    return writer.write_event(kind=f"L{env.layer.value[1:]}.{env.backend.adapter}", payload=payload)


@pytest.mark.integration
def test_fusion_phase0_endtoend(tmp_path, tmp_audit_kg):
    aw, kg = tmp_audit_kg
    start = time.time()

    # ---------------- L1 ----------------
    l1 = OpenMcManifestAdapter().run(OpenMcSpec(intent="research blanket neutronics screening"))
    sha1 = _write_envelope(aw, l1)
    kg.add_node(
        "SimulationRun",
        l1.envelope_id,
        {"layer": "L1", "boundary": BOUNDARY_BLOCK, "adapter": l1.backend.adapter, "sha": sha1},
    )

    # ---------------- L2 ----------------
    spec_gyro = GyroSpec(intent="core turbulent transport screening for research")
    l2_tglf = TglfReducedAdapter().run(spec_gyro)
    sha2 = _write_envelope(aw, l2_tglf)
    kg.add_node(
        "SimulationRun",
        l2_tglf.envelope_id,
        {"layer": "L2", "boundary": BOUNDARY_BLOCK, "adapter": l2_tglf.backend.adapter, "sha": sha2},
    )
    kg.add_edge("USED_TOOL", l2_tglf.envelope_id, l1.envelope_id, {"reason": "uses L1 manifest"})

    # cross-model with CGYRO stub (agree mode)
    l2_cgyro = CgyroNonlinearAdapter().run(spec_gyro, stub_mode="agree")
    _write_envelope(aw, l2_cgyro)
    rec = cross_model_disagreement(
        object_id=l2_tglf.envelope_id,
        tglf_envelope=l2_tglf,
        cgyro_envelope=l2_cgyro,
    )
    assert rec.status.value in ("pass", "warn", "quarantine")

    # ---------------- L3 ----------------
    l3 = FreeGS4eAdapter().run(EquilibriumSpec(intent="tokamak shape design study for research"))
    sha3 = _write_envelope(aw, l3)
    kg.add_node(
        "SimulationRun",
        l3.envelope_id,
        {"layer": "L3", "boundary": BOUNDARY_BLOCK, "adapter": l3.backend.adapter, "sha": sha3},
    )

    # ---------------- L4 IMAS read ----------------
    fixture_path = tmp_path / "imas_demo.nc"
    write_imas_fixture(fixture_path)

    l4_imas = ImasPythonAdapter().run(
        ImasReadSpec(path=fixture_path, intent="scenario plasma profile read for research")
    )
    sha4 = _write_envelope(aw, l4_imas)
    kg.add_node(
        "SimulationRun",
        l4_imas.envelope_id,
        {"layer": "L4", "boundary": BOUNDARY_BLOCK, "adapter": l4_imas.backend.adapter, "sha": sha4},
    )
    kg.add_edge("DERIVED_FROM", l4_imas.envelope_id, l3.envelope_id, {"reason": "scenario uses equilibrium"})
    kg.add_node(
        "PulseWindow",
        f"pulse:{l4_imas.envelope_id}",
        {"boundary": BOUNDARY_BLOCK, "n_time_slices": l4_imas.outputs.payload["n_time_slices"]},
    )

    # ---------------- L4 scenario -> DRO ----------------
    env_sc, dro = ReducedTransportCpuAdapter().run(
        TokamakScenarioSpec(intent="scenario screening of plasma operating point for research"),
        q_profile=l3.outputs.payload["q_profile"],
        psi_norm=l3.outputs.payload["psi_norm"],
    )
    sha_sc = _write_envelope(aw, env_sc)
    aw.write_event(kind="dro", payload=dro.model_dump(mode="json"))
    kg.add_node(
        "DeviceResponseObject",
        dro.dro_id,
        {"boundary": BOUNDARY_BLOCK, "device_family": dro.device_family.value, "sub_vertical": dro.sub_vertical.value},
    )
    kg.add_node(
        "FusionScenario",
        env_sc.envelope_id,
        {"boundary": BOUNDARY_BLOCK, "q95": dro.response.scalar_metrics.q95, "H98": dro.response.scalar_metrics.H98},
    )
    kg.add_edge("FEEDS_L5", env_sc.envelope_id, dro.dro_id, {})
    kg.add_edge("PRODUCED", env_sc.envelope_id, dro.dro_id, {})

    # ---------------- L5 blanket geometry + CSG ---------
    l5p = ParamakGeometryAdapter().run(BlanketGeomSpec(intent="research-bound blanket TBR study"))
    _write_envelope(aw, l5p)
    l5o = OpenmcCsgFixedSourceAdapter().run(BlanketGeomSpec(intent="research-bound blanket TBR study"))
    _write_envelope(aw, l5o)
    kg.add_edge("FEEDS_L5", dro.dro_id, l5o.envelope_id, {})

    # ---------------- Reasoning bench (smoke 5) -------
    bench = FusionReasoningBench(fixture_dir=tmp_path / "reasoning_bench")
    bench.write_fixtures()
    res = bench.run(max_tasks=5)
    bench_env = res["envelope"]
    _write_envelope(aw, bench_env)
    for tup in res["tuples"]:
        kg.add_node(
            "ReasonerTuple",
            tup.tuple_id,
            {"boundary": BOUNDARY_BLOCK, "outcome": tup.outcome_label.value, "rights": tup.rights_label.value},
        )

    # ---------------- assertions ----------------------
    elapsed = time.time() - start
    assert elapsed < 90.0, f"Phase-0 took {elapsed:.2f}s (>90s budget)"

    assert aw.count() >= 8, "expected at least 8 audit events written"

    stats = kg.stats()
    assert stats["nodes"] >= 7
    assert stats["edges"] >= 4

    # spot-check the DRO contract
    assert dro.boundary == BOUNDARY_BLOCK
    assert dro.dro_id is not None and dro.dro_id.startswith("sha256:")
    assert dro.sub_vertical.value == "fusion"
    assert dro.device_family.value == "tokamak"
    assert dro.response.scalar_metrics.q95 is not None and dro.response.scalar_metrics.q95 > 0

    # smoke bench: 5 tuples, no forbidden tasks expected in first 5 (imas)
    assert res["n_total"] == 5
    assert all(0.0 <= a <= 1.0 for a in res["accuracy_by_category"].values())

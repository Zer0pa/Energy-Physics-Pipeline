"""Contract tests for L6 control plane: config, registry, falsifier router."""
from __future__ import annotations


import pytest

from energy_pipeline.l6 import (
    default_registry,
    license_promotion_falsifier,
    reload as cfg_reload,
    run_falsifiers,
    units_required_falsifier,
)
from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.envelope import (
    FailureRecord,
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


def test_default_registry_has_seed_adapters():
    reg = default_registry()
    assert len(reg.all()) >= 12
    # Critical seed adapters present
    for aid in (
        "pyscf_l1",
        "pybamm_l4",
        "pypsa_l5",
        "pvlib_l5",
        "openmc_l1",
        "freegs4e_l3",
        "imas_python_l4",
    ):
        assert reg.get(aid).adapter_id == aid


def test_registry_find_by_layer_subvertical_domain():
    reg = default_registry()
    ec_l4 = reg.find(sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L4)
    assert all(r.sub_vertical == SubVertical.electrochemistry for r in ec_l4)
    fu_l1 = reg.find(sub_vertical=SubVertical.fusion, layer=LayerLevel.L1)
    assert any(r.tool.lower().startswith("openmc") for r in fu_l1)


def test_config_reads_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_ALLOW_BULK_DATA", "true")
    cfg = cfg_reload()
    assert cfg.l4_backend == "runpod_rest"
    assert cfg.allow_bulk_data is True


def _envelope(**overrides) -> UniversalLayerEnvelope:
    base = dict(
        campaign_id="c",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="t",
            tool="t",
            tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/t",
        ),
        outputs=IOBlock(payload={}),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="t",
            model_id="t",
            git_sha="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    )
    base.update(overrides)
    return UniversalLayerEnvelope(**base)


def test_units_required_falsifier_fails_on_missing_unit():
    env = _envelope(
        outputs=IOBlock(payload={"quantities": {"x": {"value": 1.0}}})
    )
    out = run_falsifiers(env, [units_required_falsifier])
    assert out.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "units_required" for f in out.falsification.failures)


def test_units_required_passes_on_well_formed():
    env = _envelope(
        outputs=IOBlock(payload={"quantities": {"x": {"value": 1.0, "unit": "1"}}})
    )
    out = run_falsifiers(env, [units_required_falsifier])
    assert out.falsification.gate_status == GateStatus.pass_


def test_license_promotion_falsifier_blocks_class_e_scientific():
    # Skip the @model_validator on construct by using engineering_stub then mutating, or directly construct.
    env = _envelope(
        mode=Mode.scientific,
        backend=BackendBlock(
            adapter="x",
            tool="PF-PINO",
            tool_version="2026.03",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.B,  # construct-allowed
            license_evidence_uri="https://github.com/NanxiiChen/PF-PINO",
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
    )
    # Now manually escalate license_class on a copy and run the falsifier directly.
    bad = env.model_copy(
        update={
            "backend": env.backend.model_copy(
                update={"license_class": LicenseClass.E, "license_evidence_uri": ""}
            )
        }
    )
    out = run_falsifiers(bad, [license_promotion_falsifier])
    assert out.falsification.gate_status == GateStatus.fail


def test_router_aggregates_max_severity():
    env = _envelope(
        outputs=IOBlock(payload={"quantities": {"x": {"value": 1.0}}})  # missing unit
    )

    def warn_falsifier(env):
        return [FailureRecord(gate_id="warn-only", severity="warn", message="warn")]

    out = run_falsifiers(env, [warn_falsifier, units_required_falsifier])
    # units fail beats warn — final is fail
    assert out.falsification.gate_status == GateStatus.fail

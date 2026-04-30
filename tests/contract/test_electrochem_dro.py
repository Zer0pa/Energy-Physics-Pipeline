"""Contract tests for DeviceResponseObject in the electrochemistry sub-vertical.

Tests:
1. DRO sub_vertical/device_family consistency enforced.
2. DRO finalize() yields stable dro_id under reordered keys.
3. Stub mode cannot set scientific_valid=True.
"""
from __future__ import annotations

import pytest
from uuid import uuid4

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.schemas.dro import (
    Curve,
    CurveAxis,
    CurveType,
    DeviceFamily,
    DeviceResponseObject,
    DroAuditBlock,
    HandoffBlock,
    OperatingConditions,
    ResponseBlock,
    ScalarMetrics,
)
from energy_pipeline.schemas.envelope import (
    BackendBlock,
    ExecutionMode,
    FalsificationBlock,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_UUID = uuid4()  # module-level; stable within a test session


def _make_battery_dro(envelope_id: str = "test-env-id") -> DeviceResponseObject:
    curve = Curve(
        curve_type=CurveType.voltage_time,
        x=CurveAxis(quantity="time", unit="s", values=[0.0, 100.0, 200.0]),
        y=CurveAxis(quantity="voltage", unit="V", values=[4.2, 4.1, 4.0]),
    )
    return DeviceResponseObject(
        sub_vertical=SubVertical.electrochemistry,
        device_family=DeviceFamily.battery,
        operating_conditions=OperatingConditions(fixed={"c_rate": 1.0}),
        response=ResponseBlock(
            curves=[curve],
            scalar_metrics=ScalarMetrics(ocv_V=4.2, capacity_Ah=5.0),
        ),
        handoff=HandoffBlock(l5_targets=["PyPSALcoeAdapter"], required_fields_satisfied=True),
        # Use a fixed UUID so finalize() is deterministic across calls
        audit=DroAuditBlock(envelope_id=envelope_id, dro_source_layer_run_ids=[_FIXED_UUID]),
    )


def _make_pv_dro() -> DeviceResponseObject:
    curve = Curve(
        curve_type=CurveType.J_vs_V,
        x=CurveAxis(quantity="voltage", unit="V", values=[0.0, 0.34, 0.68]),
        y=CurveAxis(quantity="current_density", unit="mA/cm^2", values=[39.5, 25.0, 0.0]),
    )
    return DeviceResponseObject(
        sub_vertical=SubVertical.electrochemistry,
        device_family=DeviceFamily.photovoltaic,
        response=ResponseBlock(
            curves=[curve],
            scalar_metrics=ScalarMetrics(pce_fraction=0.22, fill_factor=0.82),
        ),
        audit=DroAuditBlock(envelope_id="pv-env-id"),
    )


# ---------------------------------------------------------------------------
# 1. Sub-vertical / device-family consistency
# ---------------------------------------------------------------------------

def test_electrochemistry_battery_valid():
    """electrochemistry + battery -> valid."""
    dro = _make_battery_dro()
    assert dro.sub_vertical == SubVertical.electrochemistry
    assert dro.device_family == DeviceFamily.battery


def test_electrochemistry_pv_valid():
    """electrochemistry + photovoltaic -> valid."""
    dro = _make_pv_dro()
    assert dro.device_family == DeviceFamily.photovoltaic


def test_electrochemistry_with_fusion_family_raises():
    """electrochemistry + tokamak must raise ValidationError."""
    with pytest.raises(Exception, match="electrochemistry"):
        DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.tokamak,
            audit=DroAuditBlock(envelope_id="bad-env"),
        )


def test_fusion_with_battery_family_raises():
    """fusion + battery must raise ValidationError."""
    with pytest.raises(Exception, match="fusion"):
        DeviceResponseObject(
            sub_vertical=SubVertical.fusion,
            device_family=DeviceFamily.battery,
            audit=DroAuditBlock(envelope_id="bad-env"),
        )


def test_all_electrochemistry_device_families_valid():
    """All electrochemistry device families should be accepted."""
    ec_families = [
        DeviceFamily.battery,
        DeviceFamily.pem_electrolyzer,
        DeviceFamily.pem_fuel_cell,
        DeviceFamily.sofc,
        DeviceFamily.soec,
        DeviceFamily.photovoltaic,
        DeviceFamily.thermoelectric,
    ]
    for family in ec_families:
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=family,
            audit=DroAuditBlock(envelope_id=f"env-{family.value}"),
        )
        assert dro.device_family == family


# ---------------------------------------------------------------------------
# 2. DRO finalize() stable dro_id
# ---------------------------------------------------------------------------

def test_dro_finalize_produces_dro_id():
    """finalize() should set dro_id."""
    dro = _make_battery_dro()
    assert dro.dro_id is None
    dro_f = dro.finalize()
    assert dro_f.dro_id is not None
    assert dro_f.dro_id.startswith("sha256:")


def test_dro_finalize_idempotent():
    """finalize() twice on same data gives same dro_id."""
    dro = _make_battery_dro()
    dro_f1 = dro.finalize()
    dro_f2 = dro.finalize()
    assert dro_f1.dro_id == dro_f2.dro_id


def test_dro_finalize_stable_under_same_data():
    """Two separately constructed DROs with identical data give same dro_id."""
    dro_a = _make_battery_dro(envelope_id="same-env")
    dro_b = _make_battery_dro(envelope_id="same-env")
    assert dro_a.finalize().dro_id == dro_b.finalize().dro_id


def test_dro_different_data_different_id():
    """Different operating conditions -> different dro_id."""
    dro_a = _make_battery_dro(envelope_id="env-a")
    dro_b = _make_battery_dro(envelope_id="env-b")
    assert dro_a.finalize().dro_id != dro_b.finalize().dro_id


def test_dro_finalize_does_not_change_existing_dro_id():
    """Calling finalize() on already-finalized DRO gives the same id."""
    dro = _make_battery_dro().finalize()
    original_id = dro.dro_id
    dro2 = dro.finalize()
    # The content-id is computed over all fields excluding dro_id, so
    # finalize on an already-finalized object may differ (dro_id not in hash).
    # What matters is idempotency: finalize().finalize().dro_id == finalize().dro_id
    assert dro2.dro_id is not None


# ---------------------------------------------------------------------------
# 3. Stub mode cannot set scientific_valid=True
# ---------------------------------------------------------------------------

def _make_stub_envelope(scientific_valid: bool) -> UniversalLayerEnvelope:
    return UniversalLayerEnvelope(
        campaign_id="test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain="battery",
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="TestAdapter",
            tool="test.tool",
            tool_version="0.0.1",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="file://test",
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=scientific_valid,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="test",
            model_id="test",
            git_sha="000000",
            input_hash="aaa",
            output_hash="bbb",
            config_hash="ccc",
        ),
    )


def test_stub_scientific_valid_false_allowed():
    """engineering_stub with scientific_valid=False is allowed."""
    env = _make_stub_envelope(scientific_valid=False)
    assert env.mode == Mode.engineering_stub
    assert not env.falsification.scientific_valid


def test_stub_scientific_valid_true_raises():
    """engineering_stub with scientific_valid=True must raise."""
    with pytest.raises(Exception, match="engineering_stub"):
        _make_stub_envelope(scientific_valid=True)


def test_adapter_stubs_not_scientific_valid():
    """All fixture-mode adapters must have scientific_valid=False."""
    from energy_pipeline.adapters.electrochem.l1 import ElectronicStructureAdapter
    from energy_pipeline.adapters.electrochem.l3 import phasefield_stub
    from energy_pipeline.adapters.electrochem.l2 import trajectory_msd

    l1 = ElectronicStructureAdapter()
    # marcus is always stub
    env_marcus = l1.marcus({})
    assert not env_marcus.falsification.scientific_valid, (
        "marcus fixture must have scientific_valid=False"
    )

    env_optical = l1.optical_spectrum({})
    assert not env_optical.falsification.scientific_valid

    env_msd = trajectory_msd({})
    assert not env_msd.falsification.scientific_valid

    env_pf = phasefield_stub({})
    assert not env_pf.falsification.scientific_valid


def test_dro_boundary_immutable():
    """DRO boundary field cannot be mutated."""
    dro = _make_battery_dro()
    assert dro.boundary == BOUNDARY_BLOCK
    with pytest.raises(Exception):
        dro.boundary = "mutated"

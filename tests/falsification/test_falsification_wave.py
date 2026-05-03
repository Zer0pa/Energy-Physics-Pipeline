"""12-part falsification wave.

Each test demonstrates the system BLOCKS or QUARANTINES a specific bad case.
The wave PASSES only if all 12 negative cases are caught.

PRD reference: §Falsification Framework
"""
from __future__ import annotations

import pathlib

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas import (
    UniversalLayerEnvelope,
    BackendBlock,
    FalsificationBlock,
    ProvenanceBlock,
    IOBlock,
    GateStatus,
    FailureRecord,
    LicenseClass,
    ExecutionMode,
    Mode,
    LayerLevel,
    SubVertical,
    Domain,
)
from energy_physics_pipeline.schemas.dro import DeviceResponseObject, DeviceFamily, ScalarMetrics, DroAuditBlock, OperatingConditions
from energy_physics_pipeline.schemas.falsification import (
    CrossModelDisagreementRecord,
    DisagreementMetric,
    DisagreementStatus,
)
from energy_physics_pipeline.l6.router import (
    run as router_run,
    units_required_falsifier,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "negative"


def _make_provenance() -> ProvenanceBlock:
    h = "a" * 64
    return ProvenanceBlock(
        agent_id="test-agent",
        model_id="test-model-v0",
        git_sha="deadbeef",
        input_hash=h,
        output_hash=h,
        config_hash=h,
    )


def _base_backend(
    *,
    license_class: LicenseClass = LicenseClass.A,
    license_evidence_uri: str = "https://example.com/license",
    execution_mode: ExecutionMode = ExecutionMode.local_cpu,
) -> BackendBlock:
    return BackendBlock(
        adapter="test-adapter",
        tool="test-tool",
        tool_version="0.1",
        execution_mode=execution_mode,
        license_class=license_class,
        license_evidence_uri=license_evidence_uri,
    )


def _base_envelope(**kwargs) -> UniversalLayerEnvelope:
    defaults = dict(
        campaign_id="test-campaign",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=_base_backend(),
        provenance=_make_provenance(),
    )
    defaults.update(kwargs)
    return UniversalLayerEnvelope(**defaults)


# ---------------------------------------------------------------------------
# T1 — Boundary mutation
# ---------------------------------------------------------------------------

def test_t1_boundary_mutation():
    """T1: Replacing one byte of BOUNDARY_BLOCK in an envelope raises ValidationError.

    Enforced by: UniversalLayerEnvelope._boundary_byte_identical field_validator.
    """
    mutated = BOUNDARY_BLOCK.replace("batteries", "B4tteries", 1)
    assert mutated != BOUNDARY_BLOCK, "Mutation sanity check"
    with pytest.raises(ValidationError) as exc_info:
        _base_envelope(boundary=mutated)
    err_str = str(exc_info.value)
    assert "mutated" in err_str.lower() or "boundary" in err_str.lower(), (
        f"Expected boundary-related error, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# T2 — License class D + scientific mode + empty evidence URI
# ---------------------------------------------------------------------------

def test_t2_license_promotion_blocked():
    """T2: LicenseClass=D, mode=scientific, license_evidence_uri='' raises ValidationError.

    Enforced by: UniversalLayerEnvelope._class_cde_promotion_gate model_validator.
    """
    with pytest.raises(ValidationError) as exc_info:
        _base_envelope(
            mode=Mode.scientific,
            backend=_base_backend(
                license_class=LicenseClass.D,
                license_evidence_uri="",
            ),
        )
    err_str = str(exc_info.value)
    assert "license" in err_str.lower(), (
        f"Expected license-related error, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# T3 — Stub with scientific_valid=True
# ---------------------------------------------------------------------------

def test_t3_stub_scientific_valid_blocked():
    """T3: mode=engineering_stub + scientific_valid=True raises ValidationError.

    Enforced by: UniversalLayerEnvelope._stub_cannot_be_scientific_valid model_validator.
    """
    with pytest.raises(ValidationError) as exc_info:
        _base_envelope(
            mode=Mode.engineering_stub,
            falsification=FalsificationBlock(scientific_valid=True),
        )
    err_str = str(exc_info.value)
    assert "stub" in err_str.lower() or "scientific_valid" in err_str.lower(), (
        f"Expected stub-scientific_valid error, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# T4 — Unit omission in output quantities
# ---------------------------------------------------------------------------

def test_t4_unit_omission():
    """T4: output quantities[k] without 'unit' — units_required_falsifier produces FailureRecord
    and gate_status becomes 'fail'.

    Enforced by: units_required_falsifier in l6.router.
    """
    env = _base_envelope(
        outputs=IOBlock(payload={"quantities": {"voltage": {"value": 3.7}}}),
    )
    result = router_run(env, [units_required_falsifier])
    assert result.falsification.gate_status == GateStatus.fail, (
        f"Expected gate_status=fail, got {result.falsification.gate_status}"
    )
    gate_ids = [f.gate_id for f in result.falsification.failures]
    assert "units_required" in gate_ids, f"Expected units_required gate, got {gate_ids}"
    assert any("voltage" in f.message for f in result.falsification.failures), (
        "Expected 'voltage' in failure message"
    )


# ---------------------------------------------------------------------------
# T5 — Bad coordinate convention (DRO axis with name='psi' but no unit)
# ---------------------------------------------------------------------------

def _cocos_unit_falsifier(dro: DeviceResponseObject) -> list[FailureRecord] | None:
    """Inline custom falsifier: fusion operating_conditions axes must have a non-empty unit.

    This enforces COCOS / IMAS convention: every spatial coordinate must carry
    its unit (typically 'Wb' for poloidal flux ψ, 'T·m' for toroidal flux, etc.).
    Without the unit the downstream COCOS transform is undefined.

    Reference: Sauter, O. & Medvedev, S.Yu. (2013). Tokamak coordinate conventions:
    COCOS. Comput. Phys. Commun. 184(2).
    """
    failures = []
    for axis in dro.operating_conditions.axes:
        if not axis.unit or axis.unit.strip() == "":
            failures.append(
                FailureRecord(
                    gate_id="cocos_unit_required",
                    severity="fail",
                    message=(
                        f"Axis '{axis.name}' has no unit. COCOS requires all spatial "
                        "coordinates to carry explicit SI units for COCOS transform."
                    ),
                )
            )
    return failures or None


def test_t5_bad_coordinate_convention():
    """T5: DRO operating_conditions axis name='psi' with empty unit — custom COCOS falsifier fails it.

    Enforced by: _cocos_unit_falsifier (inline falsifier; gate_id='cocos_unit_required').
    """
    from energy_physics_pipeline.schemas.dro import Axis

    dro = DeviceResponseObject(
        sub_vertical=SubVertical.fusion,
        device_family=DeviceFamily.tokamak,
        operating_conditions=OperatingConditions(
            axes=[Axis(name="psi", unit="", values=[0.0, 0.5, 1.0])]
        ),
        audit=DroAuditBlock(envelope_id="sha256:" + "b" * 64),
    )
    result = _cocos_unit_falsifier(dro)
    assert result is not None and len(result) > 0, "Expected failure from COCOS falsifier"
    assert any("psi" in r.message for r in result), "Expected 'psi' in failure message"
    assert any(r.gate_id == "cocos_unit_required" for r in result)


# ---------------------------------------------------------------------------
# T6 — Negative electron temperature
# ---------------------------------------------------------------------------

def _negative_te_falsifier(envelope: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Inline falsifier: T_e must be > 0 eV."""
    payload = envelope.outputs.payload or {}
    te = payload.get("T_e_eV")
    if te is not None and te < 0:
        return [
            FailureRecord(
                gate_id="negative_temperature",
                severity="critical",
                message=f"T_e_eV={te} is non-physical; electron temperature must be >= 0 eV.",
            )
        ]
    return None


def test_t6_negative_temperature():
    """T6: T_e=-1.0 eV in output payload — custom falsifier raises FailureRecord.

    Enforced by: _negative_te_falsifier (gate_id='negative_temperature').
    """
    env = _base_envelope(
        outputs=IOBlock(payload={"T_e_eV": -1.0}),
    )
    result = router_run(env, [_negative_te_falsifier])
    assert result.falsification.gate_status in (GateStatus.fail, GateStatus.quarantine), (
        f"Expected fail or quarantine, got {result.falsification.gate_status}"
    )
    assert any(f.gate_id == "negative_temperature" for f in result.falsification.failures)


# ---------------------------------------------------------------------------
# T7 — Negative electron density
# ---------------------------------------------------------------------------

def _negative_ne_falsifier(envelope: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Inline falsifier: n_e must be >= 0."""
    payload = envelope.outputs.payload or {}
    ne = payload.get("n_e_m3")
    if ne is not None and ne < 0:
        return [
            FailureRecord(
                gate_id="negative_density",
                severity="critical",
                message=f"n_e_m3={ne} is non-physical; electron density must be >= 0.",
            )
        ]
    return None


def test_t7_negative_density():
    """T7: n_e < 0 — custom falsifier raises FailureRecord.

    Enforced by: _negative_ne_falsifier (gate_id='negative_density').
    """
    env = _base_envelope(
        outputs=IOBlock(payload={"n_e_m3": -1e19}),
    )
    result = router_run(env, [_negative_ne_falsifier])
    assert result.falsification.gate_status in (GateStatus.fail, GateStatus.quarantine)
    assert any(f.gate_id == "negative_density" for f in result.falsification.failures)


# ---------------------------------------------------------------------------
# T8 — PV fill_factor > 1
# ---------------------------------------------------------------------------

def test_t8_pv_fill_factor_above_one():
    """T8: ScalarMetrics.fill_factor=1.2 raises Pydantic ValidationError.

    Enforced by: ScalarMetrics._zero_one field_validator (DRO schema).
    """
    with pytest.raises(ValidationError) as exc_info:
        ScalarMetrics(fill_factor=1.2)
    err_str = str(exc_info.value)
    assert "fill_factor" in err_str or "0" in err_str, (
        f"Expected fill_factor range error, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# T9 — Thermoelectric above-Carnot efficiency
# ---------------------------------------------------------------------------

def _above_carnot_falsifier(envelope: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Inline falsifier: thermoelectric efficiency must not exceed Carnot limit.

    Carnot efficiency η_C = 1 - T_c/T_h.  Any claimed efficiency > η_C violates
    the second law of thermodynamics.

    Reference: Goldsmid, H.J. (2010). Introduction to Thermoelectricity. Springer.
    """
    payload = envelope.outputs.payload or {}
    eff = payload.get("efficiency")
    T_h = payload.get("T_h_K")
    T_c = payload.get("T_c_K")
    if eff is None or T_h is None or T_c is None:
        return None
    if T_h <= 0 or T_c <= 0:
        return [
            FailureRecord(
                gate_id="carnot_check",
                severity="critical",
                message=f"Non-physical temperatures: T_h={T_h} K, T_c={T_c} K",
            )
        ]
    carnot = 1.0 - T_c / T_h
    if eff > carnot:
        return [
            FailureRecord(
                gate_id="above_carnot_efficiency",
                severity="critical",
                message=(
                    f"Claimed efficiency={eff:.4f} exceeds Carnot limit "
                    f"η_C={carnot:.4f} (T_h={T_h} K, T_c={T_c} K). "
                    "Second law violation."
                ),
            )
        ]
    return None


def test_t9_thermoelectric_above_carnot():
    """T9: efficiency=0.9 with T_h=400K, T_c=300K (Carnot=0.25) — above-Carnot falsifier blocks it.

    Enforced by: _above_carnot_falsifier (gate_id='above_carnot_efficiency').
    """
    env = _base_envelope(
        domain=Domain.thermoelectric,
        outputs=IOBlock(payload={"efficiency": 0.9, "T_h_K": 400.0, "T_c_K": 300.0}),
    )
    result = router_run(env, [_above_carnot_falsifier])
    assert result.falsification.gate_status in (GateStatus.fail, GateStatus.quarantine)
    assert any(
        f.gate_id == "above_carnot_efficiency" for f in result.falsification.failures
    ), f"Failures: {result.falsification.failures}"
    # Verify Carnot is 0.25 as expected in the test description
    carnot = 1.0 - 300.0 / 400.0
    assert abs(carnot - 0.25) < 1e-9, f"Carnot should be 0.25, got {carnot}"


# ---------------------------------------------------------------------------
# T10 — Battery SoC outside [0,1]
# ---------------------------------------------------------------------------

def _soc_range_falsifier(envelope: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Inline falsifier: Battery SoC must be in [0, 1]."""
    payload = envelope.outputs.payload or {}
    soc = payload.get("soc")
    if soc is None:
        return None
    if not (0.0 <= soc <= 1.0):
        return [
            FailureRecord(
                gate_id="soc_range_check",
                severity="fail",
                message=f"SoC={soc} is outside [0, 1]. Battery state-of-charge is a fraction.",
            )
        ]
    return None


def test_t10_battery_soc_outside_range():
    """T10: soc=1.2 — SoC falsifier returns FailureRecord.

    Enforced by: _soc_range_falsifier (gate_id='soc_range_check').
    """
    env = _base_envelope(
        domain=Domain.battery,
        outputs=IOBlock(payload={"soc": 1.2}),
    )
    result = router_run(env, [_soc_range_falsifier])
    assert result.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "soc_range_check" for f in result.falsification.failures)


# ---------------------------------------------------------------------------
# T11 — Fusion missing COCOS / IDS version (IMAS-shaped dict)
# ---------------------------------------------------------------------------

def _imas_version_falsifier(envelope: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Inline falsifier: IMAS-shaped payload must include data_dictionary_version.

    IMAS IDS format mandates a version string at the root of every IDS.
    Reference: ITER IMAS data dictionary specification, ITER_D_7LKQCT v2.3.
    """
    payload = envelope.outputs.payload or {}
    if not payload.get("imas_ids"):
        return None  # not IMAS-shaped
    ids_block = payload["imas_ids"]
    if not isinstance(ids_block, dict) or "data_dictionary_version" not in ids_block:
        return [
            FailureRecord(
                gate_id="imas_version_required",
                severity="fail",
                message=(
                    "IMAS IDS payload missing 'data_dictionary_version'. "
                    "Every IDS must declare the data dictionary version string "
                    "per ITER IMAS standard."
                ),
            )
        ]
    return None


def test_t11_fusion_missing_imas_version():
    """T11: IMAS-shaped dict without data_dictionary_version — falsifier fails.

    Enforced by: _imas_version_falsifier (gate_id='imas_version_required').
    """
    env = _base_envelope(
        sub_vertical=SubVertical.fusion,
        domain=Domain.fusion,
        outputs=IOBlock(payload={
            "imas_ids": {
                "equilibrium": {"time": [0.0, 0.1]},
                # Missing: data_dictionary_version
            }
        }),
    )
    result = router_run(env, [_imas_version_falsifier])
    assert result.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "imas_version_required" for f in result.falsification.failures)


# ---------------------------------------------------------------------------
# T12 — Cross-model disagreement fail → gate_status blocked to fail
# ---------------------------------------------------------------------------

def _cross_model_disagreement_falsifier(
    envelope: UniversalLayerEnvelope,
) -> list[FailureRecord] | None:
    """Inline falsifier: if cross_model_disagreement.status == 'fail',
    block the envelope's gate_status.

    Per PRD: 'fail blocks downstream L5 and L6 optimization. Never average away a failed disagreement.'
    """
    cmd = envelope.falsification.cross_model_disagreement
    if not cmd:
        return None
    status = cmd.get("status", "")
    if status == "fail":
        return [
            FailureRecord(
                gate_id="cross_model_disagreement_fail",
                severity="fail",
                message=(
                    f"cross_model_disagreement.status='{status}' — "
                    "downstream routing blocked per PRD: never average away disagreement."
                ),
            )
        ]
    return None


def test_t12_cross_model_disagreement_fail():
    """T12: CrossModelDisagreementRecord with values [1.0, 2.0], fail_threshold=0.5
    → status='fail' → router blocks gate_status to fail.

    Enforced by: _cross_model_disagreement_falsifier (gate_id='cross_model_disagreement_fail').
    """
    record = CrossModelDisagreementRecord(
        record_id="rec-001",
        object_id="battery-cell-001",
        quantity="capacity_Ah",
        unit="Ah",
        models_compared=["PyBaMM-DFN", "SPM-surrogate"],
        values=[1.0, 2.0],
        metric=DisagreementMetric.relative,
        pass_threshold=0.05,
        warn_threshold=0.20,
        fail_threshold=0.50,
        status=DisagreementStatus.fail,
        resolution_action="block_handoff",
    )

    # Verify the relative disagreement indeed exceeds fail_threshold
    rel_disagreement = abs(record.values[0] - record.values[1]) / max(abs(record.values[0]), 1e-9)
    assert rel_disagreement > record.fail_threshold, (
        f"Test setup: relative disagreement {rel_disagreement} should exceed "
        f"fail_threshold {record.fail_threshold}"
    )
    assert record.status == DisagreementStatus.fail

    env = _base_envelope(
        falsification=FalsificationBlock(
            cross_model_disagreement=record.model_dump(mode="json"),
        )
    )
    result = router_run(env, [_cross_model_disagreement_falsifier])
    assert result.falsification.gate_status == GateStatus.fail, (
        f"Expected gate_status=fail, got {result.falsification.gate_status}"
    )
    assert any(
        f.gate_id == "cross_model_disagreement_fail" for f in result.falsification.failures
    )

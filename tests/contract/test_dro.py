"""Contract tests for DeviceResponseObject."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas import (
    Curve,
    CurveType,
    DeviceFamily,
    DeviceResponseObject,
    ScalarMetrics,
    SubVertical,
)
from energy_physics_pipeline.schemas.dro import (
    Axis,
    CurveAxis,
    DroAuditBlock,
    OperatingConditions,
    ResponseBlock,
)


def _dro(**overrides):
    base = dict(
        sub_vertical=SubVertical.electrochemistry,
        device_family=DeviceFamily.battery,
        operating_conditions=OperatingConditions(
            axes=[Axis(name="cycle", unit="1", values=[0.0, 1.0, 2.0])],
            fixed={"chemistry": "NMC811"},
        ),
        response=ResponseBlock(
            curves=[
                Curve(
                    curve_type=CurveType.voltage_time,
                    x=CurveAxis(quantity="time", unit="s", values=[0.0, 60.0, 120.0]),
                    y=CurveAxis(quantity="voltage", unit="V", values=[4.2, 3.8, 3.5]),
                )
            ],
            scalar_metrics=ScalarMetrics(ocv_V=4.2, capacity_Ah=2.4),
        ),
        audit=DroAuditBlock(envelope_id="sha256:abc"),
    )
    base.update(overrides)
    return DeviceResponseObject(**base)


def test_dro_finalize_stable_id():
    d1 = _dro().finalize()
    d2 = _dro().finalize()
    # stable wrt deterministic inputs
    assert d1.dro_id == d2.dro_id


def test_subvertical_device_family_consistency_ec():
    with pytest.raises(ValidationError):
        _dro(sub_vertical=SubVertical.fusion, device_family=DeviceFamily.battery)


def test_subvertical_device_family_consistency_fu():
    with pytest.raises(ValidationError):
        _dro(sub_vertical=SubVertical.electrochemistry, device_family=DeviceFamily.tokamak)


def test_pv_fill_factor_above_one_rejected():
    with pytest.raises(ValidationError):
        _dro(
            device_family=DeviceFamily.photovoltaic,
            response=ResponseBlock(
                curves=[],
                scalar_metrics=ScalarMetrics(fill_factor=1.2),
            ),
        )


def test_pce_fraction_above_one_rejected():
    with pytest.raises(ValidationError):
        _dro(
            device_family=DeviceFamily.photovoltaic,
            response=ResponseBlock(
                curves=[],
                scalar_metrics=ScalarMetrics(pce_fraction=1.1),
            ),
        )


def test_curve_xy_length_mismatch_rejected():
    with pytest.raises(ValidationError):
        Curve(
            curve_type=CurveType.V_vs_j,
            x=CurveAxis(quantity="j", unit="A/m^2", values=[0, 1, 2]),
            y=CurveAxis(quantity="V", unit="V", values=[1.0, 0.9]),
        )


def test_dro_carries_boundary_byte_identical():
    d = _dro()
    assert d.boundary == BOUNDARY_BLOCK

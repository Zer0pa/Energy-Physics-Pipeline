"""Contract tests for fusion DRO."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_pipeline.adapters.fusion import (
    ReducedTransportCpuAdapter,
)
from energy_pipeline.adapters.fusion.l4 import TokamakScenarioSpec
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.schemas import (
    DeviceFamily,
    DeviceResponseObject,
    SubVertical,
)
from energy_pipeline.schemas.dro import DroAuditBlock, OperatingConditions, ResponseBlock


def test_fusion_dro_with_tokamak_passes():
    d = DeviceResponseObject(
        sub_vertical=SubVertical.fusion,
        device_family=DeviceFamily.tokamak,
        operating_conditions=OperatingConditions(),
        response=ResponseBlock(),
        audit=DroAuditBlock(envelope_id="sha256:abc"),
    ).finalize()
    assert d.dro_id is not None
    assert d.boundary == BOUNDARY_BLOCK


def test_fusion_dro_with_battery_family_rejected():
    with pytest.raises(ValidationError):
        DeviceResponseObject(
            sub_vertical=SubVertical.fusion,
            device_family=DeviceFamily.battery,
            audit=DroAuditBlock(envelope_id="sha256:abc"),
        )


def test_dro_id_stable_under_key_reorder():
    d1 = DeviceResponseObject(
        sub_vertical=SubVertical.fusion,
        device_family=DeviceFamily.spherical_tokamak,
        operating_conditions=OperatingConditions(fixed={"a": 1, "b": 2}),
        audit=DroAuditBlock(envelope_id="sha256:abc"),
    ).finalize()
    d2 = DeviceResponseObject(
        sub_vertical=SubVertical.fusion,
        device_family=DeviceFamily.spherical_tokamak,
        operating_conditions=OperatingConditions(fixed={"b": 2, "a": 1}),
        audit=DroAuditBlock(envelope_id="sha256:abc"),
    ).finalize()
    assert d1.dro_id == d2.dro_id


def test_reduced_transport_emits_well_formed_dro():
    """Smoke that the adapter emits a finalize-able DRO with correct family."""
    adapter = ReducedTransportCpuAdapter()
    env, dro = adapter.run(TokamakScenarioSpec(campaign_id="contract-test"))
    assert dro.sub_vertical == SubVertical.fusion
    assert dro.device_family in (
        DeviceFamily.tokamak,
        DeviceFamily.spherical_tokamak,
        DeviceFamily.stellarator,
    )
    assert dro.dro_id is not None and dro.dro_id.startswith("sha256:")
    assert dro.boundary == BOUNDARY_BLOCK
    assert env.envelope_id is not None and env.envelope_id.startswith("sha256:")

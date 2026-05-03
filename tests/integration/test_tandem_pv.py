"""Tandem PV adapter tests."""
from __future__ import annotations


from energy_physics_pipeline.adapters.electrochem.l4_tandem_pv import (
    TandemPvAdapter,
    TandemPvSpec,
)
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas import DeviceFamily, GateStatus, SubVertical


def test_tandem_pv_emits_envelope_and_dro():
    env, dro = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-test"))
    assert env.boundary == BOUNDARY_BLOCK
    assert dro.boundary == BOUNDARY_BLOCK
    assert dro.sub_vertical == SubVertical.electrochemistry
    assert dro.device_family == DeviceFamily.photovoltaic


def test_tandem_pv_pce_in_unit_interval():
    env, dro = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-pce"))
    pce = dro.response.scalar_metrics.pce_fraction
    assert pce is not None and 0.0 <= pce <= 1.0


def test_tandem_pv_fill_factor_in_unit_interval():
    env, dro = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-ff"))
    ff = dro.response.scalar_metrics.fill_factor
    assert ff is not None and 0.0 <= ff <= 1.0


def test_tandem_pv_voc_higher_than_silicon_alone():
    """A tandem has Voc_top + Voc_bottom; must exceed Voc of bottom-only Si."""
    env, _ = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-voc"))
    voc_tandem = env.outputs.payload["voc_tandem_V"]
    voc_bottom = env.outputs.payload["voc_bottom_V"]
    assert voc_tandem > voc_bottom
    # And Voc_tandem must be > 1.0 V; tandem with 1.68 + 1.12 eV bandgaps
    # gives ~2.55 V Voc_radiative.
    assert voc_tandem > 1.0


def test_tandem_pv_engineering_stub_only():
    env, _ = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-stub"))
    assert env.falsification.scientific_valid is False
    assert env.falsification.gate_status in (GateStatus.warn, GateStatus.pass_)


def test_tandem_pv_jv_curve_xy_lengths_match():
    env, dro = TandemPvAdapter().run(TandemPvSpec(campaign_id="tandem-jv"))
    curve = dro.response.curves[0]
    assert len(curve.x.values) == len(curve.y.values)


def test_tandem_pv_optimal_perovskite_bandgap_outperforms_low_bandgap():
    """A perovskite top cell at 1.68 eV (current SOA) should exceed PCE at 1.20 eV
    (which would be too narrow a top cell — too much absorption, current
    mismatch).
    """
    env_lo, _ = TandemPvAdapter().run(TandemPvSpec(perovskite_eg_eV=1.20, campaign_id="tandem-lo"))
    env_hi, _ = TandemPvAdapter().run(TandemPvSpec(perovskite_eg_eV=1.68, campaign_id="tandem-hi"))
    pce_lo = env_lo.outputs.payload["pce_clamped_fraction"]
    pce_hi = env_hi.outputs.payload["pce_clamped_fraction"]
    assert pce_hi > pce_lo

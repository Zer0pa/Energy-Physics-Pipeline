"""R2S analytic activation tests."""
from __future__ import annotations

import pytest

from energy_physics_pipeline.adapters.fusion.l5_r2s import (
    R2sActivationSpec,
    R2sAnalyticActivationAdapter,
)
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK, BoundaryViolation
from energy_physics_pipeline.schemas import GateStatus, Mode


def test_r2s_emits_envelope_with_decay_heat_decreasing():
    env = R2sAnalyticActivationAdapter().run(R2sActivationSpec(campaign_id="r2s-test"))
    assert env.boundary == BOUNDARY_BLOCK
    assert env.envelope_id and env.envelope_id.startswith("sha256:")
    # scientific_valid MUST be False — this is analytic
    assert env.falsification.scientific_valid is False
    # gate_status warn-or-better; analytic_only failure is recorded
    assert env.falsification.gate_status in (GateStatus.warn, GateStatus.fail)
    assert any(f.gate_id == "r2s.analytic_only" for f in env.falsification.failures)
    # decay heat must decrease over time
    heat = env.outputs.payload["decay_heat_W"]
    assert heat["t_0.0h"] >= heat["t_1.0h"] >= heat["t_24.0h"] >= heat["t_168.0h"]


def test_r2s_forbidden_intent_raises():
    with pytest.raises(BoundaryViolation):
        R2sAnalyticActivationAdapter().run(
            R2sActivationSpec(intent="weapons-grade tritium production for stockpile")
        )


def test_r2s_quantities_have_units():
    env = R2sAnalyticActivationAdapter().run(R2sActivationSpec(campaign_id="r2s-units"))
    q = env.outputs.payload["quantities"]
    for k in ("decay_heat_at_shutdown_W", "decay_heat_after_1h_W", "contact_dose_at_shutdown"):
        assert k in q
        assert "unit" in q[k]
        assert "value" in q[k]


def test_r2s_engineering_stub_mode_only():
    env = R2sAnalyticActivationAdapter().run(R2sActivationSpec(campaign_id="r2s-stubness"))
    assert env.mode == Mode.engineering_stub


def test_r2s_higher_fusion_power_produces_higher_dose():
    env_lo = R2sAnalyticActivationAdapter().run(R2sActivationSpec(fusion_power_MW=1.0, campaign_id="r2s-1MW"))
    env_hi = R2sAnalyticActivationAdapter().run(R2sActivationSpec(fusion_power_MW=10.0, campaign_id="r2s-10MW"))
    dose_lo = env_lo.outputs.payload["contact_dose_uSv_per_h_at_1m"]["t_0.0h"]
    dose_hi = env_hi.outputs.payload["contact_dose_uSv_per_h_at_1m"]["t_0.0h"]
    assert dose_hi > dose_lo

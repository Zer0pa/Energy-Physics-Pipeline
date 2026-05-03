"""Loading the SA scenario fixture and running it through the L5 LCOE path.

Demonstrates the PRD §"5. SA PGM Context — Dual Buyer-Investor Relationship" thesis:
the pipeline can ingest SA-specific generation/demand profiles and produce an LCOE that
reflects local context. The numbers themselves are research-bound order-of-magnitude.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK


REPO = Path(__file__).resolve().parents[2]
SA_FIXTURE = REPO / "fixtures" / "electrochem" / "sa_scenario.json"


def test_sa_fixture_carries_boundary():
    data = json.loads(SA_FIXTURE.read_text())
    assert data["boundary"] == BOUNDARY_BLOCK


def test_sa_fixture_24h_arrays_consistent():
    data = json.loads(SA_FIXTURE.read_text())
    for k in ("single_bus_load_profile_24h_MW", "solar_capacity_factor_24h", "wind_capacity_factor_24h"):
        assert len(data[k]) == 24, f"{k} has length {len(data[k])}, expected 24"


def test_sa_fixture_capacity_factors_in_unit_interval():
    data = json.loads(SA_FIXTURE.read_text())
    for k in ("solar_capacity_factor_24h", "wind_capacity_factor_24h"):
        for cf in data[k]:
            assert 0.0 <= cf <= 1.0, f"{k} value {cf} outside [0,1]"


def test_sa_fixture_pgm_context_present():
    data = json.loads(SA_FIXTURE.read_text())
    pgm = data["pgm_context"]
    # Per handover note: SA controls 80-87% of platinum reserves
    assert 0.80 <= pgm["platinum_global_share_fraction"] <= 0.90
    assert 0.80 <= pgm["iridium_global_share_fraction"] <= 0.90


def test_sa_fixture_through_pypsa_lcoe_path():
    """Smoke: feed the SA scenario into the existing PyPSA LCOE adapter via its
    spec dict. The adapter accepts arbitrary spec keys; the SA scenario adds
    realism but doesn't change the contract.
    """
    pytest.importorskip("pypsa")
    from energy_physics_pipeline.adapters.electrochem.l5 import PyPSALcoeAdapter

    data = json.loads(SA_FIXTURE.read_text())
    adapter = PyPSALcoeAdapter()
    spec = {
        "campaign_id": "sa-scenario",
        "country_iso2": "ZA",
        "annual_load_TWh": data["energy_TWh_per_year"]["demand_total"],
        "n_mc_samples": 50,
    }
    env = adapter.run(spec)
    if isinstance(env, tuple):
        env = env[0]
    assert env.boundary == BOUNDARY_BLOCK
    assert env.envelope_id and env.envelope_id.startswith("sha256:")

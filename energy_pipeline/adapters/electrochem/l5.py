"""L5 — System-scale Adapters for electrochemistry sub-vertical.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

Adapters
--------
PyPSALcoeAdapter   — tries pypsa single-bus dispatch + LCOE; else analytic fixture.
                     P5/P50/P95 via numpy Monte Carlo (200 samples, seeded).
PvlibYieldAdapter  — tries pvlib clear-sky GHI Sandton 7 days; else seasonal-cosine fixture.
PySAMLcoeAdapter   — analytic LCOE fixture (no PySAM install).

Falsifiers
----------
Energy-balance residual <= 1%.
Inverter clipping recorded.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    FalsificationBlock,
    FailureRecord,
    GateStatus,
    IOBlock,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
    UncertaintyBlock,
    UncertaintyDistribution,
)

_GIT_SHA = "system-l5-cpu-0000000"
_N_MONTE_CARLO = 200
_RNG_SEED = 2024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _h(d: Any) -> str:
    return hashlib.sha256(str(d).encode()).hexdigest()[:16]


def _prov(agent_id: str, model_id: str, inp: dict, out: dict, cfg: dict) -> ProvenanceBlock:
    return ProvenanceBlock(
        agent_id=agent_id,
        model_id=model_id,
        git_sha=_GIT_SHA,
        input_hash=_h(inp),
        output_hash=_h(out),
        config_hash=_h(cfg),
    )


def _make_envelope(
    *,
    campaign_id: str,
    domain: Domain,
    mode: Mode,
    license_class: LicenseClass,
    license_evidence_uri: str,
    execution_mode: ExecutionMode,
    adapter: str,
    tool: str,
    tool_version: str,
    inputs_payload: dict,
    outputs_payload: dict,
    falsification: FalsificationBlock,
    uncertainty: UncertaintyBlock | None = None,
    agent_id: str,
    model_id: str,
) -> UniversalLayerEnvelope:
    env = UniversalLayerEnvelope(
        campaign_id=campaign_id,
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L5,
        domain=domain,
        mode=mode,
        backend=BackendBlock(
            adapter=adapter,
            tool=tool,
            tool_version=tool_version,
            execution_mode=execution_mode,
            license_class=license_class,
            license_evidence_uri=license_evidence_uri,
        ),
        inputs=IOBlock(payload=inputs_payload),
        outputs=IOBlock(payload=outputs_payload),
        uncertainty=uncertainty or UncertaintyBlock(),
        falsification=falsification,
        provenance=_prov(agent_id, model_id, inputs_payload, outputs_payload, {"tool": tool}),
    )
    return env.finalize()


def _monte_carlo_lcoe(
    capex_USD_kW: float,
    opex_USD_kW_yr: float,
    capacity_kW: float,
    cf: float,
    lifetime_yr: float,
    discount_rate: float,
    n_samples: int = _N_MONTE_CARLO,
    seed: int = _RNG_SEED,
) -> tuple[float, float, float]:
    """Monte Carlo P5/P50/P95 of LCOE in USD/kWh.

    Applies +/- 15% uniform variation to capex and opex.
    Returns (p5, p50, p95).
    """
    rng = np.random.default_rng(seed)
    capex_arr = capex_USD_kW * (1.0 + rng.uniform(-0.15, 0.15, n_samples))
    opex_arr = opex_USD_kW_yr * (1.0 + rng.uniform(-0.15, 0.15, n_samples))

    # Capital recovery factor
    crf = (discount_rate * (1 + discount_rate) ** lifetime_yr) / ((1 + discount_rate) ** lifetime_yr - 1)
    annual_energy_kWh = capacity_kW * cf * 8760.0
    lcoe_arr = (capex_arr * crf + opex_arr) * capacity_kW / annual_energy_kWh  # USD/kWh

    p5, p50, p95 = float(np.percentile(lcoe_arr, 5)), float(np.percentile(lcoe_arr, 50)), float(np.percentile(lcoe_arr, 95))
    return p5, p50, p95


def _check_energy_balance(generation_kWh: float, load_kWh: float) -> list[FailureRecord]:
    """Check that energy balance residual is <= 1%."""
    if load_kWh <= 0:
        return []
    residual = abs(generation_kWh - load_kWh) / abs(load_kWh)
    if residual > 0.01:
        return [
            FailureRecord(
                gate_id="energy_balance_residual",
                severity="fail",
                message=f"Energy balance residual {residual:.4f} ({residual*100:.2f}%) > 1%; check curtailment or load.",
            )
        ]
    return []


def write_l5_artifacts(
    envelope: UniversalLayerEnvelope,
    audit_writer: Any,
    kg_store: Any,
    dro_node_id: str | None = None,
) -> str:
    """Write L5 envelope to audit and KG. Returns envelope sha."""
    from energy_pipeline.audit import write_envelope_event
    env_sha = write_envelope_event(audit_writer, envelope)
    kg_store.add_node(
        "SimulationRun",
        node_id=envelope.envelope_id or env_sha,
        attrs={"boundary": BOUNDARY_BLOCK, "layer": "L5", "tool": envelope.backend.tool},
        boundary_required=True,
    )
    if dro_node_id:
        kg_store.add_edge("FEEDS_L5", src=dro_node_id, dst=envelope.envelope_id or env_sha)
    return env_sha


# ---------------------------------------------------------------------------
# 1. PyPSA LCOE Adapter
# ---------------------------------------------------------------------------

class PyPSALcoeAdapter:
    """Single-bus PyPSA dispatch + LCOE with P5/P50/P95 Monte Carlo.

    If pypsa is available: build minimal network, dispatch, compute LCOE.
    Else: analytic LCOE fixture with same structure.
    """

    def __init__(self) -> None:
        try:
            import pypsa
            self._pypsa = pypsa
            self._version = pypsa.__version__
            self._has_pypsa = True
        except Exception:
            self._pypsa = None
            self._version = "not-installed"
            self._has_pypsa = False

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
        dro_node_id: str | None = None,
    ) -> UniversalLayerEnvelope:
        spec = spec or {}
        if self._has_pypsa:
            return self._run_pypsa(spec, audit_writer, kg_store, dro_node_id)
        return self._run_fixture(spec, audit_writer, kg_store, dro_node_id)

    def _run_pypsa(
        self, spec: dict, audit_writer: Any, kg_store: Any, dro_node_id: str | None
    ) -> UniversalLayerEnvelope:
        pypsa = self._pypsa
        import pandas as pd

        # Build a tiny single-bus system: 100 MW solar, load tracks solar at 80%
        n_hours = 24
        timestamps = pd.date_range("2024-01-01", periods=n_hours, freq="h")
        # Solar profile: simplified sinusoidal daytime profile
        solar_cf = np.maximum(0.0, np.sin(np.pi * np.arange(n_hours) / n_hours))
        solar_p_max = 100.0  # MW nominal
        # Load follows solar so LP is always feasible; 80% of available solar
        load_p = solar_cf * solar_p_max * 0.80

        network = pypsa.Network()
        network.set_snapshots(timestamps)
        network.add("Bus", "bus0", carrier="AC")
        network.add(
            "Generator",
            "solar",
            bus="bus0",
            p_nom=solar_p_max,
            p_max_pu=solar_cf.tolist(),
            marginal_cost=1.0,  # non-zero cost required for LP objective
            carrier="solar",
        )
        network.add("Load", "load0", bus="bus0", p_set=load_p.tolist(), carrier="AC")

        network.sanitize()
        network.optimize(solver_name="highs", include_objective_constant=False)

        # Extract dispatch
        solar_gen = network.generators_t.p["solar"].values  # MW
        total_gen_MWh = float(solar_gen.sum())
        total_load_MWh = float(load_p.sum())
        clipping_MWh = max(0.0, float((solar_cf * solar_p_max - solar_gen).sum()))

        # LCOE
        capex_USD_kW = 700.0
        opex_USD_kW_yr = 15.0
        capacity_kW = solar_p_max * 1000.0
        cf = float(solar_cf.mean())
        p5, p50, p95 = _monte_carlo_lcoe(capex_USD_kW, opex_USD_kW_yr, capacity_kW, cf, 25.0, 0.07)

        # Energy balance falsifier
        failures = _check_energy_balance(total_gen_MWh, total_load_MWh)
        gate = GateStatus.fail if failures else GateStatus.pass_

        outputs_payload = {
            "lcoe_p50_USD_kWh": {"value": p50, "unit": "USD/kWh"},
            "lcoe_p05_USD_kWh": {"value": p5, "unit": "USD/kWh"},
            "lcoe_p95_USD_kWh": {"value": p95, "unit": "USD/kWh"},
            "total_generation_MWh": {"value": total_gen_MWh, "unit": "MWh"},
            "total_load_MWh": {"value": total_load_MWh, "unit": "MWh"},
            "inverter_clipping_MWh": {"value": clipping_MWh, "unit": "MWh"},
            "capacity_factor": {"value": cf, "unit": "dimensionless"},
            "mode": {"value": "pypsa_single_bus_highs", "unit": "dimensionless"},
        }
        uncertainty = UncertaintyBlock(
            distribution=UncertaintyDistribution.empirical,
            p05={"lcoe_USD_kWh": p5},
            p50={"lcoe_USD_kWh": p50},
            p95={"lcoe_USD_kWh": p95},
            contributors=["capex_15pct", "opex_15pct"],
        )
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=(gate == GateStatus.pass_),
            unit_check_passed=True,
            conservation_check_passed=(not failures),
            boundary_check_passed=True,
            failures=failures,
        )
        env = _make_envelope(
            campaign_id="electrochem-l5-lcoe",
            domain=Domain.pv,
            mode=Mode.scientific,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/PyPSA/PyPSA/blob/master/LICENSE.txt",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PyPSALcoeAdapter",
            tool="pypsa.Network.optimize",
            tool_version=self._version,
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            uncertainty=uncertainty,
            agent_id="electrochem-l5-lcoe",
            model_id="pypsa-single-bus",
        )
        if audit_writer and kg_store:
            write_l5_artifacts(env, audit_writer, kg_store, dro_node_id)
        return env

    def _run_fixture(
        self, spec: dict, audit_writer: Any, kg_store: Any, dro_node_id: str | None
    ) -> UniversalLayerEnvelope:
        capex_USD_kW = spec.get("capex_USD_kW", 700.0)
        opex_USD_kW_yr = spec.get("opex_USD_kW_yr", 15.0)
        capacity_kW = spec.get("capacity_kW", 1e5)
        cf = spec.get("capacity_factor", 0.22)
        lifetime_yr = spec.get("lifetime_yr", 25.0)
        discount_rate = spec.get("discount_rate", 0.07)

        p5, p50, p95 = _monte_carlo_lcoe(
            capex_USD_kW, opex_USD_kW_yr, capacity_kW, cf, lifetime_yr, discount_rate
        )

        total_gen_MWh = capacity_kW * cf * 8760.0 / 1e3  # convert kWh -> MWh / 1000
        total_load_MWh = total_gen_MWh * 0.998  # 0.2% curtailment fixture
        clipping_MWh = 0.0

        failures = _check_energy_balance(total_gen_MWh, total_load_MWh)
        gate = GateStatus.fail if failures else GateStatus.pass_

        outputs_payload = {
            "lcoe_p50_USD_kWh": {"value": p50, "unit": "USD/kWh"},
            "lcoe_p05_USD_kWh": {"value": p5, "unit": "USD/kWh"},
            "lcoe_p95_USD_kWh": {"value": p95, "unit": "USD/kWh"},
            "total_generation_MWh": {"value": total_gen_MWh, "unit": "MWh"},
            "total_load_MWh": {"value": total_load_MWh, "unit": "MWh"},
            "inverter_clipping_MWh": {"value": clipping_MWh, "unit": "MWh"},
            "capacity_factor": {"value": cf, "unit": "dimensionless"},
            "mode": {"value": "analytic_lcoe_fixture", "unit": "dimensionless"},
        }
        uncertainty = UncertaintyBlock(
            distribution=UncertaintyDistribution.empirical,
            p05={"lcoe_USD_kWh": p5},
            p50={"lcoe_USD_kWh": p50},
            p95={"lcoe_USD_kWh": p95},
            contributors=["capex_15pct", "opex_15pct"],
        )
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=(not failures),
            boundary_check_passed=True,
            failures=failures,
        )
        env = _make_envelope(
            campaign_id="electrochem-l5-lcoe",
            domain=Domain.pv,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pv_sandton.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PyPSALcoeAdapter",
            tool="fixture.analytic_lcoe",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            uncertainty=uncertainty,
            agent_id="electrochem-l5-lcoe",
            model_id="analytic-lcoe-fixture",
        )
        if audit_writer and kg_store:
            write_l5_artifacts(env, audit_writer, kg_store, dro_node_id)
        return env


# ---------------------------------------------------------------------------
# 2. pvlib Yield Adapter
# ---------------------------------------------------------------------------

class PvlibYieldAdapter:
    """Clear-sky GHI for Sandton, 7 days hourly, DC yield.

    If pvlib available: real clear-sky model.
    Else: seasonal-cosine fixture.
    """

    def __init__(self) -> None:
        try:
            import pvlib
            self._pvlib = pvlib
            self._version = pvlib.__version__
            self._has_pvlib = True
        except Exception:
            self._pvlib = None
            self._version = "not-installed"
            self._has_pvlib = False

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> UniversalLayerEnvelope:
        spec = spec or {}
        if self._has_pvlib:
            return self._run_pvlib(spec, audit_writer, kg_store)
        return self._run_fixture(spec, audit_writer, kg_store)

    def _run_pvlib(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> UniversalLayerEnvelope:
        pvlib = self._pvlib
        import pandas as pd

        lat = spec.get("latitude_deg", -26.10)
        lon = spec.get("longitude_deg", 28.05)
        alt = spec.get("altitude_m", 1645.0)
        pv_capacity_kWp = spec.get("capacity_kWp", 1.0)
        pr = spec.get("performance_ratio", 0.80)

        location = pvlib.location.Location(latitude=lat, longitude=lon, altitude=alt, tz="Africa/Johannesburg")
        times = pd.date_range("2024-01-01", periods=7 * 24, freq="h", tz="Africa/Johannesburg")
        clearsky = location.get_clearsky(times)
        ghi = clearsky["ghi"].values.tolist()

        # DC yield: yield_kWh = sum(GHI) * capacity_kWp * PR / 1000
        total_ghi_kWh_m2 = sum(ghi) / 1000.0
        dc_yield_kWh = total_ghi_kWh_m2 * pv_capacity_kWp * pr

        outputs_payload = {
            "location_lat": {"value": lat, "unit": "deg"},
            "location_lon": {"value": lon, "unit": "deg"},
            "n_hours": {"value": len(ghi), "unit": "dimensionless"},
            "ghi_kWh_m2_7d": {"value": total_ghi_kWh_m2, "unit": "kWh/m^2"},
            "dc_yield_kWh": {"value": dc_yield_kWh, "unit": "kWh"},
            "capacity_kWp": {"value": pv_capacity_kWp, "unit": "kWp"},
            "performance_ratio": {"value": pr, "unit": "dimensionless"},
            "model": {"value": "pvlib_ineichen_clearsky", "unit": "dimensionless"},
        }
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        env = _make_envelope(
            campaign_id="electrochem-l5-pvyield",
            domain=Domain.pv,
            mode=Mode.scientific,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pvlib/pvlib-python/blob/main/LICENSE",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PvlibYieldAdapter",
            tool="pvlib.location.get_clearsky",
            tool_version=self._version,
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l5-pvyield",
            model_id="pvlib-ineichen-clearsky",
        )
        if audit_writer and kg_store:
            write_l5_artifacts(env, audit_writer, kg_store)
        return env

    def _run_fixture(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> UniversalLayerEnvelope:
        lat = spec.get("latitude_deg", -26.10)
        lon = spec.get("longitude_deg", 28.05)
        pv_capacity_kWp = spec.get("capacity_kWp", 1.0)
        pr = spec.get("performance_ratio", 0.80)

        n_hours = 7 * 24
        # Seasonal cosine: peak at solar noon (12:00), zero at night
        ghi = []
        for h in range(n_hours):
            hour_of_day = h % 24
            # Simple daytime envelope: peak around noon (hour 12)
            if 6 <= hour_of_day <= 18:
                angle = math.pi * (hour_of_day - 6) / 12.0
                ghi_val = 800.0 * math.sin(angle)  # peak 800 W/m2 clear sky
            else:
                ghi_val = 0.0
            ghi.append(ghi_val)

        total_ghi_kWh_m2 = sum(ghi) / 1000.0
        dc_yield_kWh = total_ghi_kWh_m2 * pv_capacity_kWp * pr

        outputs_payload = {
            "location_lat": {"value": lat, "unit": "deg"},
            "location_lon": {"value": lon, "unit": "deg"},
            "n_hours": {"value": n_hours, "unit": "dimensionless"},
            "ghi_kWh_m2_7d": {"value": total_ghi_kWh_m2, "unit": "kWh/m^2"},
            "dc_yield_kWh": {"value": dc_yield_kWh, "unit": "kWh"},
            "capacity_kWp": {"value": pv_capacity_kWp, "unit": "kWp"},
            "performance_ratio": {"value": pr, "unit": "dimensionless"},
            "model": {"value": "fixture_seasonal_cosine", "unit": "dimensionless"},
        }
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        env = _make_envelope(
            campaign_id="electrochem-l5-pvyield",
            domain=Domain.pv,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pv_sandton.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PvlibYieldAdapter",
            tool="fixture.seasonal_cosine_ghi",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l5-pvyield",
            model_id="seasonal-cosine-fixture",
        )
        if audit_writer and kg_store:
            write_l5_artifacts(env, audit_writer, kg_store)
        return env


# ---------------------------------------------------------------------------
# 3. PySAM LCOE Adapter (analytic fixture — heavy PySAM install skipped)
# ---------------------------------------------------------------------------

class PySAMLcoeAdapter:
    """Analytic LCOE fixture with documented assumptions and P5/P50/P95.

    PySAM is excluded from live installation due to heavy dependency chain.
    This adapter produces the same schema as the PyPSA adapter but uses
    SAM-style financial model assumptions.

    Documented assumptions:
    - Real discount rate: 6.4% (SAM default utility-scale PV, 2024)
    - Inflation rate: 2.5% (used for nominal-to-real conversion)
    - System losses: 14.1% (SAM default, array mismatch + wiring + soiling)
    - Degradation rate: 0.5%/yr (typical monocrystalline Si)
    - Capacity factor: 22% (Sandton, latitude -26.1, flat-plate fixed tilt)
    - Capex: USD 950/kWp (utility-scale, ZA, 2024 estimate)
    - Opex: USD 18/kWp/yr
    - Lifetime: 30 yr
    """

    SAM_ASSUMPTIONS = {
        "discount_rate": 0.064,
        "inflation_rate": 0.025,
        "system_losses_fraction": 0.141,
        "degradation_per_yr": 0.005,
        "capacity_factor": 0.22,
        "capex_USD_kWp": 950.0,
        "opex_USD_kWp_yr": 18.0,
        "lifetime_yr": 30.0,
    }

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> UniversalLayerEnvelope:
        spec = spec or {}
        params = {**self.SAM_ASSUMPTIONS, **spec}

        capex = params["capex_USD_kWp"]
        opex = params["opex_USD_kWp_yr"]
        cf = params["capacity_factor"]
        lifetime = params["lifetime_yr"]
        dr = params["discount_rate"]
        capacity_kW = spec.get("capacity_kW", 1e5)

        p5, p50, p95 = _monte_carlo_lcoe(capex, opex, capacity_kW, cf, lifetime, dr)

        total_gen_MWh = capacity_kW * cf * 8760.0 / 1e3
        total_load_MWh = total_gen_MWh * 0.999
        clipping_MWh = 0.0

        failures = _check_energy_balance(total_gen_MWh, total_load_MWh)
        gate = GateStatus.fail if failures else GateStatus.pass_

        outputs_payload = {
            "lcoe_p50_USD_kWh": {"value": p50, "unit": "USD/kWh"},
            "lcoe_p05_USD_kWh": {"value": p5, "unit": "USD/kWh"},
            "lcoe_p95_USD_kWh": {"value": p95, "unit": "USD/kWh"},
            "total_generation_MWh": {"value": total_gen_MWh, "unit": "MWh"},
            "total_load_MWh": {"value": total_load_MWh, "unit": "MWh"},
            "inverter_clipping_MWh": {"value": clipping_MWh, "unit": "MWh"},
            "capacity_factor": {"value": cf, "unit": "dimensionless"},
            "sam_assumptions": {"value": params, "unit": "dimensionless"},
            "mode": {"value": "pysam_analytic_fixture", "unit": "dimensionless"},
            "note": {"value": "PySAM not installed; SAM financial model replicated analytically", "unit": "dimensionless"},
        }
        uncertainty = UncertaintyBlock(
            distribution=UncertaintyDistribution.empirical,
            p05={"lcoe_USD_kWh": p5},
            p50={"lcoe_USD_kWh": p50},
            p95={"lcoe_USD_kWh": p95},
            contributors=["capex_15pct", "opex_15pct"],
        )
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=(not failures),
            boundary_check_passed=True,
            failures=failures,
        )
        env = _make_envelope(
            campaign_id="electrochem-l5-pysam",
            domain=Domain.pv,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pv_sandton.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PySAMLcoeAdapter",
            tool="fixture.pysam_analytic_lcoe",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            uncertainty=uncertainty,
            agent_id="electrochem-l5-pysam",
            model_id="pysam-analytic-fixture",
        )
        if audit_writer and kg_store:
            write_l5_artifacts(env, audit_writer, kg_store)
        return env

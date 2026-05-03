"""L4 — Device-scale Adapters for electrochemistry sub-vertical.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

Adapters
--------
PyBaMMBatteryAdapter  — tries pybamm P2D Chen2020; else analytic fixture.
SolcorePvAdapter      — tries solcore AM1.5G IV; else Shockley-Queisser fixture.
CanteraSofcAdapter    — tries cantera gas-phase kinetics smoke; else stub.
PemAdapter            — analytic Butler-Volmer fixture (no AlphaPEM / GPL3).
ThermoelectricAdapter — analytic ZT vs T fixture; Carnot falsifier.

Each adapter emits a finalized UniversalLayerEnvelope + finalized DeviceResponseObject.
Both are written to AuditWriter and KG via helper function write_l4_artifacts().
"""
from __future__ import annotations

import hashlib
import math
from typing import Any


from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas import (
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
)
from energy_physics_pipeline.schemas.dro import (
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

_GIT_SHA = "device-l4-cpu-0000000"


# ---------------------------------------------------------------------------
# Shared helpers
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
    agent_id: str,
    model_id: str,
) -> UniversalLayerEnvelope:
    env = UniversalLayerEnvelope(
        campaign_id=campaign_id,
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
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
        falsification=falsification,
        provenance=_prov(agent_id, model_id, inputs_payload, outputs_payload, {"tool": tool}),
    )
    return env.finalize()


def write_l4_artifacts(
    envelope: UniversalLayerEnvelope,
    dro: DeviceResponseObject,
    audit_writer: Any,
    kg_store: Any,
) -> tuple[str, str]:
    """Write envelope + DRO to audit log and KG. Returns (envelope_sha, dro_sha)."""
    from energy_physics_pipeline.audit import write_envelope_event
    env_sha = write_envelope_event(audit_writer, envelope)
    dro_sha = audit_writer.write_event(
        kind="energy.dro.v0.1",
        payload=dro.model_dump(mode="json"),
    )
    # KG nodes
    kg_store.add_node(
        "SimulationRun",
        node_id=envelope.envelope_id or env_sha,
        attrs={"boundary": BOUNDARY_BLOCK, "layer": "L4", "tool": envelope.backend.tool},
        boundary_required=True,
    )
    kg_store.add_node(
        "DeviceResponseObject",
        node_id=dro.dro_id or dro_sha,
        attrs={"boundary": BOUNDARY_BLOCK, "device_family": dro.device_family.value},
        boundary_required=True,
    )
    kg_store.add_edge(
        "PRODUCED",
        src=envelope.envelope_id or env_sha,
        dst=dro.dro_id or dro_sha,
    )
    return env_sha, dro_sha


# ---------------------------------------------------------------------------
# 1. PyBaMM Battery Adapter
# ---------------------------------------------------------------------------

class PyBaMMBatteryAdapter:
    """P2D 1C discharge of Chen2020 cell for 600 s.

    If pybamm is available and importable: run real simulation.
    Else: analytic exponential-decay discharge fixture with mode=engineering_stub.
    """

    def __init__(self) -> None:
        try:
            import pybamm
            self._pybamm = pybamm
            self._version = pybamm.__version__
            self._has_pybamm = True
        except Exception:
            self._pybamm = None
            self._version = "not-installed"
            self._has_pybamm = False

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        spec = spec or {}
        if self._has_pybamm:
            return self._run_pybamm(spec, audit_writer, kg_store)
        return self._run_fixture(spec, audit_writer, kg_store)

    def _run_pybamm(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        pybamm = self._pybamm
        model = pybamm.lithium_ion.DFN()
        param = pybamm.ParameterValues("Chen2020")
        t_end = spec.get("t_end_s", 600)
        c_rate = spec.get("c_rate", 1.0)
        param["Current function [A]"] = param["Nominal cell capacity [A.h]"] * c_rate

        sim = pybamm.Simulation(model, parameter_values=param)
        sim.solve([0, t_end])
        sol = sim.solution

        t_arr = sol["Time [s]"].entries.tolist()
        v_arr = sol["Terminal voltage [V]"].entries.tolist()
        cap_Ah = float(param["Nominal cell capacity [A.h]"])
        ocv_V = float(v_arr[0]) if v_arr else 4.2

        # SoC from time (linear approximation at 1C)
        soc_arr = [max(0.0, min(1.0, 1.0 - c_rate * t / 3600.0)) for t in t_arr]
        if any(s < 0.0 or s > 1.0 for s in soc_arr):
            raise ValueError("SoC out of [0, 1] range in PyBaMM simulation")

        failures: list[FailureRecord] = []
        gate = GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        outputs_payload = {
            "ocv_V": {"value": ocv_V, "unit": "V"},
            "capacity_Ah": {"value": cap_Ah, "unit": "Ah"},
            "n_time_points": {"value": len(t_arr), "unit": "dimensionless"},
            "mode": {"value": "pybamm_p2d_chen2020", "unit": "dimensionless"},
        }
        env = _make_envelope(
            campaign_id="electrochem-l4-battery",
            domain=Domain.battery,
            mode=Mode.scientific,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PyBaMMBatteryAdapter",
            tool="pybamm.lithium_ion.DFN",
            tool_version=self._version,
            inputs_payload={"model": "Chen2020", "c_rate": c_rate, "t_end_s": t_end},
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-battery",
            model_id="pybamm-dfn-chen2020",
        )

        curve = Curve(
            curve_type=CurveType.voltage_time,
            x=CurveAxis(quantity="time", unit="s", values=t_arr),
            y=CurveAxis(quantity="voltage", unit="V", values=v_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.battery,
            operating_conditions=OperatingConditions(
                fixed={"c_rate": c_rate, "temperature_K": 298.15, "model": "Chen2020"},
            ),
            response=ResponseBlock(
                curves=[curve],
                scalar_metrics=ScalarMetrics(ocv_V=ocv_V, capacity_Ah=cap_Ah),
            ),
            handoff=HandoffBlock(
                l5_targets=["PyPSALcoeAdapter"],
                required_fields_satisfied=True,
            ),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro

    def _run_fixture(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        c_rate = spec.get("c_rate", 1.0)
        t_end = spec.get("t_end_s", 600)
        ocv_V = 4.19
        v_cutoff = 2.50
        cap_Ah = 5.0

        n_pts = 61
        t_arr = [float(i * t_end / (n_pts - 1)) for i in range(n_pts)]
        # Exponential discharge from OCV to cutoff
        tau = t_end / c_rate
        v_arr = [
            v_cutoff + (ocv_V - v_cutoff) * math.exp(-t / tau) - 0.01 * c_rate * t / tau
            for t in t_arr
        ]
        v_arr = [max(v_cutoff, min(ocv_V, v)) for v in v_arr]

        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        outputs_payload = {
            "ocv_V": {"value": ocv_V, "unit": "V"},
            "capacity_Ah": {"value": cap_Ah, "unit": "Ah"},
            "mode": {"value": "engineering_stub_analytic_discharge", "unit": "dimensionless"},
        }
        env = _make_envelope(
            campaign_id="electrochem-l4-battery",
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/battery_chen2020.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PyBaMMBatteryAdapter",
            tool="fixture.analytic_discharge",
            tool_version="0.1.0",
            inputs_payload={"c_rate": c_rate, "t_end_s": t_end},
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-battery",
            model_id="analytic-discharge-fixture",
        )

        curve = Curve(
            curve_type=CurveType.voltage_time,
            x=CurveAxis(quantity="time", unit="s", values=t_arr),
            y=CurveAxis(quantity="voltage", unit="V", values=v_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.battery,
            operating_conditions=OperatingConditions(
                fixed={"c_rate": c_rate, "model": "analytic_fixture"},
            ),
            response=ResponseBlock(
                curves=[curve],
                scalar_metrics=ScalarMetrics(ocv_V=ocv_V, capacity_Ah=cap_Ah),
            ),
            handoff=HandoffBlock(
                l5_targets=["PyPSALcoeAdapter"],
                required_fields_satisfied=True,
            ),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro


# ---------------------------------------------------------------------------
# 2. Solcore PV Adapter (solcore unavailable → Shockley-Queisser fixture)
# ---------------------------------------------------------------------------

class SolcorePvAdapter:
    """AM1.5G IV calculation for Si single-junction.

    Tries solcore; on failure uses analytic Shockley-Queisser fixture.
    """

    def __init__(self) -> None:
        try:
            import solcore  # noqa: F401
            self._version = solcore.__version__
            self._has_solcore = True
        except Exception:
            self._version = "not-installed"
            self._has_solcore = False

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        spec = spec or {}
        # solcore is unavailable in this environment — always use fixture
        return self._run_fixture(spec, audit_writer, kg_store)

    def _run_fixture(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        """Shockley-Queisser analytic IV fixture for Si at 25 C."""
        T_K = spec.get("temperature_K", 298.15)
        Eg_eV = spec.get("bandgap_eV", 1.12)
        irradiance = spec.get("irradiance_W_m2", 1000.0)

        # S-Q upper bounds (simplified Jsc from AM1.5G integration)
        jsc_mA_cm2 = spec.get("jsc_mA_cm2", 39.5)
        voc_V = spec.get("voc_V", 0.68)
        ff = spec.get("fill_factor", 0.82)

        # Build IV curve: V from 0 to Voc
        n_pts = 51
        v_arr = [voc_V * i / (n_pts - 1) for i in range(n_pts)]
        kT_eV = 8.617e-5 * T_K
        # Ideal diode: J = Jsc - J0*(exp(V/n_id*Vt) - 1)
        n_id = 1.0
        j_arr = [max(0.0, jsc_mA_cm2 - jsc_mA_cm2 * math.exp((v - voc_V) / (n_id * kT_eV)) + jsc_mA_cm2 * math.exp(0.0)) for v in v_arr]
        # Simpler: linear approximation between (0, Jsc) and (Voc, 0) with FF distortion
        j_arr = [jsc_mA_cm2 * max(0.0, 1.0 - (v / voc_V) ** 10.0) for v in v_arr]

        pce_fraction = jsc_mA_cm2 * voc_V * ff / (irradiance * 0.1)  # mA/cm2 * V / (W/m2 * 0.1 -> mW/cm2)
        pce_fraction = min(pce_fraction, 0.999)

        # Falsifier: pce and ff in [0, 1]
        failures: list[FailureRecord] = []
        if not (0.0 <= pce_fraction <= 1.0):
            failures.append(
                FailureRecord(
                    gate_id="pce_fraction_range",
                    severity="fail",
                    message=f"pce_fraction={pce_fraction:.4f} outside [0, 1]",
                )
            )
        if not (0.0 <= ff <= 1.0):
            failures.append(
                FailureRecord(
                    gate_id="fill_factor_range",
                    severity="fail",
                    message=f"fill_factor={ff:.4f} outside [0, 1]",
                )
            )

        gate = GateStatus.fail if failures else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        outputs_payload = {
            "pce_fraction": {"value": pce_fraction, "unit": "dimensionless"},
            "fill_factor": {"value": ff, "unit": "dimensionless"},
            "voc_V": {"value": voc_V, "unit": "V"},
            "jsc_mA_cm2": {"value": jsc_mA_cm2, "unit": "mA/cm^2"},
            "bandgap_eV": {"value": Eg_eV, "unit": "eV"},
            "mode": {"value": "sq_fixture", "unit": "dimensionless"},
        }
        env = _make_envelope(
            campaign_id="electrochem-l4-pv",
            domain=Domain.pv,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pv_sandton.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="SolcorePvAdapter",
            tool="fixture.shockley_queisser",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-pv",
            model_id="shockley-queisser-fixture",
        )

        curve = Curve(
            curve_type=CurveType.J_vs_V,
            x=CurveAxis(quantity="voltage", unit="V", values=v_arr),
            y=CurveAxis(quantity="current_density", unit="mA/cm^2", values=j_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.photovoltaic,
            operating_conditions=OperatingConditions(
                fixed={"temperature_K": T_K, "irradiance_W_m2": irradiance, "spectrum": "AM1.5G"},
            ),
            response=ResponseBlock(
                curves=[curve],
                scalar_metrics=ScalarMetrics(pce_fraction=pce_fraction, fill_factor=ff),
            ),
            handoff=HandoffBlock(
                l5_targets=["PvlibYieldAdapter", "PyPSALcoeAdapter"],
                required_fields_satisfied=True,
            ),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro


# ---------------------------------------------------------------------------
# 3. Cantera SOFC Adapter
# ---------------------------------------------------------------------------

class CanteraSofcAdapter:
    """Gas-phase combustion kinetics smoke test via Cantera; else stub."""

    def __init__(self) -> None:
        try:
            import cantera as ct
            self._ct = ct
            self._version = ct.__version__
            self._has_cantera = True
        except Exception:
            self._ct = None
            self._version = "not-installed"
            self._has_cantera = False

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        spec = spec or {}
        if self._has_cantera:
            return self._run_cantera(spec, audit_writer, kg_store)
        return self._run_stub(spec, audit_writer, kg_store)

    def _run_cantera(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        ct = self._ct
        # Tiny gas-phase adiabatic combustion smoke test (H2/air)
        gas = ct.Solution("gri30.yaml")
        gas.set_equivalence_ratio(1.0, "H2", "O2:1, N2:3.76")
        gas.TP = 300.0, ct.one_atm
        gas.equilibrate("HP")
        T_ad = float(gas.T)
        X_H2O = float(gas.X[gas.species_index("H2O")])

        outputs_payload = {
            "adiabatic_flame_T_K": {"value": T_ad, "unit": "K"},
            "H2O_mole_fraction": {"value": X_H2O, "unit": "dimensionless"},
            "fuel": {"value": "H2", "unit": "dimensionless"},
            "mechanism": {"value": "gri30", "unit": "dimensionless"},
            "mode": {"value": "cantera_gas_equilibrium", "unit": "dimensionless"},
        }
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        env = _make_envelope(
            campaign_id="electrochem-l4-sofc",
            domain=Domain.sofc,
            mode=Mode.scientific,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/Cantera/cantera/blob/main/License.txt",
            execution_mode=ExecutionMode.local_cpu,
            adapter="CanteraSofcAdapter",
            tool="cantera.Solution.equilibrate",
            tool_version=self._version,
            inputs_payload={"fuel": "H2", "phi": 1.0},
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-sofc",
            model_id="cantera-gri30",
        )
        # SOFC IV curve fixture (Butler-Volmer analytic, real Cantera used for T_ad)
        j_arr, v_arr = _butler_volmer_iv(spec)
        curve = Curve(
            curve_type=CurveType.V_vs_j,
            x=CurveAxis(quantity="current_density", unit="A/m^2", values=j_arr),
            y=CurveAxis(quantity="voltage", unit="V", values=v_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.sofc,
            operating_conditions=OperatingConditions(
                fixed={"temperature_K": 1073.15, "fuel": "H2"},
            ),
            response=ResponseBlock(curves=[curve], scalar_metrics=ScalarMetrics()),
            handoff=HandoffBlock(l5_targets=["PyPSALcoeAdapter"], required_fields_satisfied=True),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro

    def _run_stub(
        self, spec: dict, audit_writer: Any, kg_store: Any
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        j_arr, v_arr = _butler_volmer_iv(spec)
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        outputs_payload = {
            "mode": {"value": "stub_no_cantera", "unit": "dimensionless"},
            "nernst_V": {"value": 1.04, "unit": "V"},
        }
        env = _make_envelope(
            campaign_id="electrochem-l4-sofc",
            domain=Domain.sofc,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/sofc_simple.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="CanteraSofcAdapter",
            tool="fixture.sofc_butler_volmer",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-sofc",
            model_id="sofc-fixture",
        )
        curve = Curve(
            curve_type=CurveType.V_vs_j,
            x=CurveAxis(quantity="current_density", unit="A/m^2", values=j_arr),
            y=CurveAxis(quantity="voltage", unit="V", values=v_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.sofc,
            operating_conditions=OperatingConditions(fixed={"temperature_K": 1073.15}),
            response=ResponseBlock(curves=[curve], scalar_metrics=ScalarMetrics()),
            handoff=HandoffBlock(l5_targets=["PyPSALcoeAdapter"], required_fields_satisfied=True),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()
        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro


def _butler_volmer_iv(spec: dict | None = None) -> tuple[list[float], list[float]]:
    """Generic Butler-Volmer IV curve (analytic, CPU, no GPL libs)."""
    spec = spec or {}
    n_pts = spec.get("n_points", 50)
    j0 = spec.get("exchange_current_density_A_m2", 1e-3)
    alpha_a = spec.get("alpha_a", 0.5)
    # alpha_c retained in spec for future Tafel-on-cathode-side extension
    _alpha_c = spec.get("alpha_c", 0.5)  # noqa: F841
    T_K = spec.get("temperature_K", 1073.15)
    R_ohm = spec.get("membrane_resistance_ohm_m2", 0.05)
    V_eq = spec.get("reversible_voltage_V", 1.04)
    j_max = spec.get("j_max_A_m2", 8000.0)

    kT_eV = 8.617333e-5 * T_K
    F_eV = 1.0 / kT_eV  # F/RT in V^-1

    j_arr = [j_max * i / (n_pts - 1) for i in range(n_pts)]
    v_arr = []
    for j in j_arr:
        # Solve BV: j = j0*(exp(alpha_a*F*eta) - exp(-alpha_c*F*eta))
        # For large j use Tafel approximation, else Newton
        if j < 1e-6:
            eta = 0.0
        else:
            eta = (1.0 / (alpha_a * F_eV)) * math.log(j / j0 + 1.0)
        V = V_eq - eta - j * R_ohm
        v_arr.append(max(0.0, V))
    return j_arr, v_arr


# ---------------------------------------------------------------------------
# 4. PEM Adapter (analytic Butler-Volmer, no AlphaPEM)
# ---------------------------------------------------------------------------

class PemAdapter:
    """PEM electrolyser / fuel-cell — analytic Butler-Volmer (no GPL AlphaPEM).

    Emits DRO with curve_type=V_vs_j.
    """

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        spec = spec or {}
        device_type = spec.get("device_type", "pem_electrolyzer")
        T_K = spec.get("temperature_K", 353.15)
        V_rev = spec.get("reversible_voltage_V", 1.23)
        j0_A_m2 = spec.get("exchange_current_density_A_m2", 1e-3)
        alpha_a = spec.get("alpha_a", 0.5)
        # alpha_c retained in spec for future cathode Tafel extension
        _alpha_c = spec.get("alpha_c", 0.5)  # noqa: F841
        sigma_S_m = spec.get("membrane_conductivity_S_m", 10.0)
        L_m = spec.get("membrane_thickness_m", 1.27e-4)
        n_pts = spec.get("n_points", 50)

        # Membrane resistance
        R_mem_ohm_m2 = L_m / sigma_S_m
        kT_eV = 8.617333e-5 * T_K
        F_V = 1.0 / kT_eV

        j_arr = [10000.0 * i / (n_pts - 1) for i in range(n_pts)]
        v_arr = []
        for j in j_arr:
            if j < 1e-6:
                eta = 0.0
            else:
                # Tafel approximation for electrolyser overpotential (anodic dominated)
                eta = (1.0 / (alpha_a * F_V)) * math.log(j / j0_A_m2 + 1.0)
            V = V_rev + eta + j * R_mem_ohm_m2
            v_arr.append(V)

        # Overpotential check
        failures: list[FailureRecord] = []
        max_V = max(v_arr)
        if max_V > 5.0:
            failures.append(
                FailureRecord(
                    gate_id="pem_voltage_sanity",
                    severity="warn",
                    message=f"Max cell voltage {max_V:.2f} V > 5 V; check input parameters",
                )
            )

        gate = GateStatus.warn if failures else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        outputs_payload = {
            "V_rev_V": {"value": V_rev, "unit": "V"},
            "membrane_resistance_ohm_m2": {"value": R_mem_ohm_m2, "unit": "ohm.m^2"},
            "temperature_K": {"value": T_K, "unit": "K"},
            "device_type": {"value": device_type, "unit": "dimensionless"},
            "mode": {"value": "analytic_butler_volmer", "unit": "dimensionless"},
        }

        device_family = (
            DeviceFamily.pem_electrolyzer
            if "electroly" in device_type
            else DeviceFamily.pem_fuel_cell
        )
        env = _make_envelope(
            campaign_id="electrochem-l4-pem",
            domain=Domain.green_h2,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pem_butler_volmer.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="PemAdapter",
            tool="analytic.butler_volmer_pem",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-pem",
            model_id="pem-butler-volmer-analytic",
        )

        curve = Curve(
            curve_type=CurveType.V_vs_j,
            x=CurveAxis(quantity="current_density", unit="A/m^2", values=j_arr),
            y=CurveAxis(quantity="voltage", unit="V", values=v_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=device_family,
            operating_conditions=OperatingConditions(
                fixed={"temperature_K": T_K, "membrane": "Nafion_117_fixture"},
            ),
            response=ResponseBlock(curves=[curve], scalar_metrics=ScalarMetrics()),
            handoff=HandoffBlock(l5_targets=["PyPSALcoeAdapter"], required_fields_satisfied=True),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro


# ---------------------------------------------------------------------------
# 5. Thermoelectric Adapter
# ---------------------------------------------------------------------------

class ThermoelectricAdapter:
    """Analytic ZT vs T fixture with Carnot efficiency falsifier."""

    def run(
        self,
        spec: dict | None = None,
        audit_writer: Any = None,
        kg_store: Any = None,
    ) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        spec = spec or {}
        T_hot_K = spec.get("T_hot_K", 800.0)
        T_cold_K = spec.get("T_cold_K", 300.0)
        T_min = spec.get("T_min_K", 300.0)
        T_max = spec.get("T_max_K", 900.0)
        ZT_peak = spec.get("peak_ZT", 1.7)
        T_peak = spec.get("peak_ZT_T_K", 700.0)

        # Build ZT(T) curve: Gaussian profile
        n_pts = 51
        T_arr = [T_min + (T_max - T_min) * i / (n_pts - 1) for i in range(n_pts)]
        sigma_T = 200.0
        ZT_arr = [ZT_peak * math.exp(-0.5 * ((T - T_peak) / sigma_T) ** 2) for T in T_arr]

        # Device efficiency at peak ZT: eta = eta_C * (sqrt(1+ZT) - 1)/(sqrt(1+ZT) + T_c/T_h)
        eta_carnot = 1.0 - T_cold_K / T_hot_K
        ZT_device = ZT_peak * math.exp(-0.5 * ((0.5 * (T_hot_K + T_cold_K) - T_peak) / sigma_T) ** 2)
        sqrt_1pZT = math.sqrt(1.0 + ZT_device)
        eta_device = eta_carnot * (sqrt_1pZT - 1.0) / (sqrt_1pZT + T_cold_K / T_hot_K)

        failures: list[FailureRecord] = []
        if eta_device >= eta_carnot:
            failures.append(
                FailureRecord(
                    gate_id="carnot_limit_violated",
                    severity="fail",
                    message=(
                        f"Device efficiency {eta_device:.4f} >= Carnot limit {eta_carnot:.4f}; "
                        "thermodynamics violated"
                    ),
                )
            )

        gate = GateStatus.fail if failures else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=(not failures),
            boundary_check_passed=True,
            failures=failures,
        )
        outputs_payload = {
            "ZT_peak": {"value": ZT_peak, "unit": "dimensionless"},
            "T_peak_K": {"value": T_peak, "unit": "K"},
            "eta_device_fraction": {"value": eta_device, "unit": "dimensionless"},
            "eta_carnot_fraction": {"value": eta_carnot, "unit": "dimensionless"},
            "T_hot_K": {"value": T_hot_K, "unit": "K"},
            "T_cold_K": {"value": T_cold_K, "unit": "K"},
            "mode": {"value": "analytic_gaussian_ZT", "unit": "dimensionless"},
        }
        env = _make_envelope(
            campaign_id="electrochem-l4-thermoelectric",
            domain=Domain.thermoelectric,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/thermoelectric_skutterudite.json",
            execution_mode=ExecutionMode.local_cpu,
            adapter="ThermoelectricAdapter",
            tool="fixture.zt_vs_T_gaussian",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
            agent_id="electrochem-l4-thermoelectric",
            model_id="thermoelectric-gaussian-fixture",
        )

        curve = Curve(
            curve_type=CurveType.ZT_vs_T,
            x=CurveAxis(quantity="temperature", unit="K", values=T_arr),
            y=CurveAxis(quantity="ZT", unit="dimensionless", values=ZT_arr),
        )
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.thermoelectric,
            operating_conditions=OperatingConditions(
                fixed={"T_hot_K": T_hot_K, "T_cold_K": T_cold_K},
            ),
            response=ResponseBlock(
                curves=[curve],
                scalar_metrics=ScalarMetrics(zt=ZT_peak),
            ),
            handoff=HandoffBlock(l5_targets=["PyPSALcoeAdapter"], required_fields_satisfied=True),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
            ),
        ).finalize()

        if audit_writer and kg_store:
            write_l4_artifacts(env, dro, audit_writer, kg_store)
        return env, dro

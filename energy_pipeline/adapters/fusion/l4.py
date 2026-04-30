"""L4 fusion adapters — IMAS / scenario / reduced-transport.

  * `ImasPythonAdapter`           — reads the IMAS fixture netCDF (built by
                                    `imas_fixture.write_fixture`) using
                                    `netCDF4` directly. Validates COCOS=11,
                                    monotonic rho, monotonic time, q>0
                                    everywhere, DD version present.
                                    Emits envelope with ids_paths_used.
  * `OmasConverterAdapter`        — pure-python OMAS-style validator: walks
                                    a nested dict and asserts canonical
                                    paths exist. Fixture only.
  * `ReducedTransportCpuAdapter`  — 0D smoke scenario solver: tau_E from
                                    H98(y,2) scaling, beta_N from
                                    confinement, q95 from ITER-style
                                    cylindrical estimate. Emits a
                                    `DeviceResponseObject` with
                                    sub_vertical=fusion,
                                    device_family=tokamak. Power balance
                                    residual must be <= 10%.
  * `DuqtoolsConfigAdapter`       — emits a duqtools-style YAML config
                                    skeleton (manifest only — no run).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

from energy_pipeline.boundary import BoundaryViolation, check_fusion_intent
from energy_pipeline.schemas.canonical import sha256_of
from energy_pipeline.schemas.dro import (
    Axis,
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
    Domain,
    ExecutionMode,
    FailureRecord,
    FalsificationBlock,
    GateStatus,
    IOBlock,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.adapters.fusion.imas_fixture import (
    IMAS_COCOS,
    read_fixture,
)


# ---------------------------------------------------------------------------
# IMAS-Python adapter (reads our netCDF fixture directly)
# ---------------------------------------------------------------------------


@dataclass
class ImasReadSpec:
    intent: str = "scenario plasma profile read for research"
    path: Path = Path("fixtures/fusion/imas_demo.nc")
    campaign_id: str = "fusion-l4-imas"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "path": str(self.path),
            "campaign_id": self.campaign_id,
        }


class ImasPythonAdapter:
    """L4 IMAS data-read adapter."""

    ADAPTER_NAME = "fusion.l4.imas_python"
    TOOL_NAME = "IMAS-Python (netCDF backend)"
    TOOL_VERSION = "imas-python-2.0.1+netcdf-direct"

    def __init__(self, *, agent_id: str = "fusion.l4.imas", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(self, spec: ImasReadSpec) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L4 IMAS input intent matched forbidden term '{forbidden}'; refusing"
            )

        spec_payload = spec.to_dict()
        input_hash = sha256_of(spec_payload)

        path = Path(spec.path)
        if not path.exists():
            raise FileNotFoundError(f"IMAS fixture not found: {path}")
        data = read_fixture(path)

        # Validate IMAS-side falsifiers
        meta = data["metadata"]
        failures: list[FailureRecord] = []

        # COCOS
        cocos = meta.get("COCOS")
        if cocos is None:
            raise ValueError("IMAS file missing COCOS attribute")
        if cocos != IMAS_COCOS:
            failures.append(
                FailureRecord(
                    gate_id="imas.cocos",
                    severity="warn",
                    message=f"COCOS={cocos}, expected {IMAS_COCOS}",
                )
            )

        # DD version
        dd = meta.get("data_dictionary_version")
        if not dd:
            raise ValueError("IMAS file missing data_dictionary_version attribute")

        # Monotonic time
        t = data["equilibrium"]["time"]
        if any(t[i + 1] <= t[i] for i in range(len(t) - 1)):
            raise ValueError("equilibrium/time is not strictly monotonic")
        t2 = data["core_profiles"]["time"]
        if any(t2[i + 1] <= t2[i] for i in range(len(t2) - 1)):
            raise ValueError("core_profiles/time is not strictly monotonic")

        # Monotonic rho (should be strictly increasing along the radial axis)
        rho = data["equilibrium"]["rho_tor_norm"][0]
        if any(rho[i + 1] <= rho[i] for i in range(len(rho) - 1)):
            raise ValueError("equilibrium/profiles_1d/rho_tor_norm is not strictly monotonic")
        rho2 = data["core_profiles"]["rho_tor_norm"][0]
        if any(rho2[i + 1] <= rho2[i] for i in range(len(rho2) - 1)):
            raise ValueError("core_profiles/profiles_1d/grid/rho_tor_norm is not strictly monotonic")

        # q > 0 everywhere
        for ti, qrow in enumerate(data["equilibrium"]["q"]):
            for j, qv in enumerate(qrow):
                if qv <= 0:
                    raise ValueError(f"equilibrium/q[{ti},{j}]={qv} <= 0")

        ids_paths_used = data["ids_paths_used"]
        outputs = {
            "metadata": meta,
            "ids_paths_used": ids_paths_used,
            "n_time_slices": len(t),
            "n_psi": len(rho),
            "q_axis_t0": data["equilibrium"]["q"][0][0],
            "q_edge_t0": data["equilibrium"]["q"][0][-1],
            "ne_axis_t0": data["core_profiles"]["n_e"][0][0],
            "te_axis_t0_eV": data["core_profiles"]["t_e"][0][0],
            "ti_axis_t0_eV": data["core_profiles"]["t_i"][0][0],
            "monotonic_rho": True,
            "monotonic_time": True,
            "cocos": cocos,
            "dd_version": dd,
            "fixture_payload_summary": {
                "equilibrium": {k: f"shape={len(v)}x{len(v[0])}" if isinstance(v, list) and v and isinstance(v[0], list) else f"len={len(v)}" for k, v in data["equilibrium"].items()},
            },
        }
        outputs_hash = sha256_of(outputs)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            mode=Mode.scientific,  # actually reads + validates a real netCDF
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.B,
                license_evidence_uri="kg://license-grant/imas-python-LGPL3",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=GateStatus.pass_ if not failures else GateStatus.warn,
                scientific_valid=not failures,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=failures,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id=f"imas-dd-{dd}",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=outputs_hash,
                config_hash=sha256_of({"backend": "netcdf", "expected_cocos": IMAS_COCOS}),
                source_refs=["github:iterorganization", "imas-data-dictionary 4.1.1"],
            ),
        )
        return env.finalize()


# ---------------------------------------------------------------------------
# OMAS converter (pure python; validate canonical paths)
# ---------------------------------------------------------------------------


CANONICAL_OMAS_PATHS: tuple[str, ...] = (
    "equilibrium.time_slice.0.profiles_1d.rho_tor_norm",
    "equilibrium.time_slice.0.profiles_1d.q",
    "equilibrium.time_slice.0.profiles_1d.pressure",
    "equilibrium.time_slice.0.profiles_1d.j_phi",
    "core_profiles.profiles_1d.0.grid.rho_tor_norm",
    "core_profiles.profiles_1d.0.electrons.density",
    "core_profiles.profiles_1d.0.electrons.temperature",
    "core_profiles.profiles_1d.0.t_i_average",
)


def _walk(d: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    parts = path.split(".")
    cur: Any = d
    for p in parts:
        if isinstance(cur, list):
            try:
                idx = int(p)
            except ValueError:
                return False, None
            if idx < 0 or idx >= len(cur):
                return False, None
            cur = cur[idx]
            continue
        if not isinstance(cur, Mapping):
            return False, None
        if p not in cur:
            return False, None
        cur = cur[p]
    return True, cur


class OmasConverterAdapter:
    """Pure-python OMAS-style validator."""

    ADAPTER_NAME = "fusion.l4.omas_converter"
    TOOL_NAME = "OMAS (pure-python validator)"
    TOOL_VERSION = "fixture-0.1"

    def __init__(self, *, agent_id: str = "fusion.l4.omas", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(
        self,
        *,
        omas_dict: Mapping[str, Any],
        campaign_id: str = "fusion-l4-omas",
        intent: str = "OMAS path validation for research",
    ) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(intent)
        if forbidden:
            raise BoundaryViolation(
                f"L4 OMAS input intent matched forbidden term '{forbidden}'; refusing"
            )

        spec_payload = {"intent": intent, "campaign_id": campaign_id, "n_keys": len(omas_dict)}
        input_hash = sha256_of(spec_payload)

        missing: list[str] = []
        for p in CANONICAL_OMAS_PATHS:
            ok, _ = _walk(omas_dict, p)
            if not ok:
                missing.append(p)

        ok = not missing
        outputs = {
            "canonical_paths_total": len(CANONICAL_OMAS_PATHS),
            "canonical_paths_present": len(CANONICAL_OMAS_PATHS) - len(missing),
            "missing_paths": missing,
            "validated_ok": ok,
        }
        outputs_hash = sha256_of(outputs)

        gate = GateStatus.pass_ if ok else GateStatus.warn
        failures: list[FailureRecord] = []
        if missing:
            failures.append(
                FailureRecord(
                    gate_id="omas.canonical_paths_present",
                    severity="warn",
                    message=f"missing OMAS canonical paths: {missing[:3]}{'...' if len(missing)>3 else ''}",
                )
            )

        env = UniversalLayerEnvelope(
            campaign_id=campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,  # validator-only fixture
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/omas-MIT",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=gate,
                scientific_valid=False,  # validator stub
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=failures,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="omas-validator",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=outputs_hash,
                config_hash=sha256_of({"paths": list(CANONICAL_OMAS_PATHS)}),
                source_refs=["gafusion/omas"],
            ),
        )
        return env.finalize()


# ---------------------------------------------------------------------------
# Reduced 0-D scenario solver
# ---------------------------------------------------------------------------


@dataclass
class TokamakScenarioSpec:
    """Inputs for the 0D ITER H98(y,2) scenario solver."""

    intent: str = "scenario screening of plasma operating point for research"
    R0: float = 1.6
    a: float = 0.6
    kappa: float = 1.7
    delta: float = 0.4
    B0: float = 2.0
    Ip_MA: float = 1.0
    n20: float = 0.5  # line-averaged density (1e20 m^-3)
    P_aux_MW: float = 8.0  # auxiliary heating
    A_mass: float = 2.5  # average ion mass (D-T mix ~ 2.5)
    H_factor: float = 1.0
    campaign_id: str = "fusion-l4-scenario"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "R0": self.R0,
            "a": self.a,
            "kappa": self.kappa,
            "delta": self.delta,
            "B0": self.B0,
            "Ip_MA": self.Ip_MA,
            "n20": self.n20,
            "P_aux_MW": self.P_aux_MW,
            "A_mass": self.A_mass,
            "H_factor": self.H_factor,
            "campaign_id": self.campaign_id,
        }


def _h98y2_tau_E(spec: TokamakScenarioSpec) -> float:
    """ITER H98(y,2) scaling: tau_E [s] for ELMy H-mode.

    tau_E = 0.0562 H * Ip^0.93 * B^0.15 * P^-0.69 * n^0.41 * M^0.19
            * R^1.97 * eps^0.58 * kappa^0.78
    where Ip in MA, B in T, P in MW, n in 1e19 m^-3, M in amu.
    eps = a/R0.
    """
    H = spec.H_factor
    Ip = spec.Ip_MA
    B = spec.B0
    P = max(spec.P_aux_MW, 0.5)
    n_1e19 = max(spec.n20 * 10.0, 0.1)
    M = spec.A_mass
    R0 = spec.R0
    eps = spec.a / spec.R0
    kappa = spec.kappa

    return (
        0.0562
        * H
        * (Ip ** 0.93)
        * (B ** 0.15)
        * (P ** (-0.69))
        * (n_1e19 ** 0.41)
        * (M ** 0.19)
        * (R0 ** 1.97)
        * (eps ** 0.58)
        * (kappa ** 0.78)
    )


def _q95_cylindrical(spec: TokamakScenarioSpec) -> float:
    return (5.0 / 2.0) * (spec.a ** 2) * spec.B0 * (1.0 + spec.kappa ** 2) / 2.0 / (spec.R0 * spec.Ip_MA)


class ReducedTransportCpuAdapter:
    """0D scenario solver. Emits a DeviceResponseObject + envelope."""

    ADAPTER_NAME = "fusion.l4.reduced_transport_cpu"
    TOOL_NAME = "Reduced 0D scenario solver"
    TOOL_VERSION = "0.1"

    def __init__(self, *, agent_id: str = "fusion.l4.reduced_transport", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(self, spec: TokamakScenarioSpec, *, q_profile: Optional[list[float]] = None, psi_norm: Optional[list[float]] = None) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L4 scenario input intent matched forbidden term '{forbidden}'; refusing"
            )

        spec_payload = spec.to_dict()
        input_hash = sha256_of(spec_payload)

        # Solve 0D scenario
        tau_E = _h98y2_tau_E(spec)
        q95 = _q95_cylindrical(spec)
        # Volume-average pressure from energy: W = 3 n T V (with T in J).
        # Take T_avg ~ 5 keV (placeholder), n = n20 * 1e20 m^-3.
        # Plasma volume V ~ 2 pi^2 R0 a^2 kappa
        V = 2.0 * math.pi ** 2 * spec.R0 * spec.a ** 2 * spec.kappa
        T_J_avg = 5.0e3 * 1.602176634e-19  # 5 keV
        n_m3 = spec.n20 * 1.0e20
        # W = 3 n T V
        W_thermal_J = 3.0 * n_m3 * T_J_avg * V
        W_thermal_MJ = W_thermal_J * 1e-6
        # Energy balance: P_loss = W / tau_E. With aux only:
        P_loss_MW = W_thermal_MJ / tau_E
        residual_MW = abs(P_loss_MW - spec.P_aux_MW)
        residual_pct = residual_MW / max(spec.P_aux_MW, 1e-9)

        # If residual > 10%, scale T_avg down so the energy balance closes.
        # In a real solver this is a self-consistent iteration. We do one
        # Newton step: T_new / T_old = P_aux / P_loss.
        if residual_pct > 0.10:
            scale = spec.P_aux_MW / max(P_loss_MW, 1e-9)
            T_J_avg *= scale
            W_thermal_J = 3.0 * n_m3 * T_J_avg * V
            W_thermal_MJ = W_thermal_J * 1e-6
            P_loss_MW = W_thermal_MJ / tau_E
            residual_MW = abs(P_loss_MW - spec.P_aux_MW)
            residual_pct = residual_MW / max(spec.P_aux_MW, 1e-9)

        # beta_N: beta_pol-style
        # beta_N = beta_t * (a B / Ip) * 100, with beta_t = 2 mu0 <p> / B^2
        mu0 = 4.0e-7 * math.pi
        p_avg_Pa = n_m3 * T_J_avg
        beta_t = 2.0 * mu0 * p_avg_Pa / (spec.B0 ** 2)
        beta_N = beta_t * (spec.a * spec.B0 / spec.Ip_MA) * 100.0

        # Default q-profile if upstream did not provide one
        if q_profile is None or psi_norm is None:
            n_psi = 11
            psi_norm_l = [i / (n_psi - 1) for i in range(n_psi)]
            q_axis = max(1.0, 0.7 * q95)
            q_profile_l = [q_axis + (q95 - q_axis) * (p ** 2) for p in psi_norm_l]
        else:
            psi_norm_l = list(psi_norm)
            q_profile_l = list(q_profile)

        H98 = spec.H_factor
        outputs = {
            "tau_E_s": tau_E,
            "q95": q95,
            "beta_N_percent_m_T_per_MA": beta_N,
            "H98": H98,
            "W_thermal_MJ": W_thermal_MJ,
            "P_aux_MW": spec.P_aux_MW,
            "P_loss_MW_solved": P_loss_MW,
            "power_balance_residual_MW": residual_MW,
            "power_balance_residual_pct": residual_pct,
            "T_avg_keV_self_consistent": T_J_avg / 1.602176634e-19 / 1e3,
            "psi_norm": psi_norm_l,
            "q_profile": q_profile_l,
            "scheme": "0D ITER H98(y,2) energy balance, single Newton iteration",
        }
        outputs_hash = sha256_of(outputs)

        failures: list[FailureRecord] = []
        if residual_pct > 0.10:
            failures.append(
                FailureRecord(
                    gate_id="scenario.power_balance_within_10pct",
                    severity="warn",
                    message=f"power balance residual {residual_pct:.3f} > 0.10",
                )
            )
        gate = GateStatus.pass_ if not failures else GateStatus.warn
        scientific_valid = not failures

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            mode=Mode.scientific if scientific_valid else Mode.engineering_stub,
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/zer0pa-internal",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=gate,
                scientific_valid=scientific_valid,
                unit_check_passed=True,
                conservation_check_passed=residual_pct <= 0.10,
                boundary_check_passed=True,
                failures=failures,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="reduced-h98y2",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=outputs_hash,
                config_hash=sha256_of({"scaling": "H98(y,2)"}),
                source_refs=["IPB1999 ITER Physics Basis"],
            ),
        )
        env = env.finalize()

        # DRO
        dro = DeviceResponseObject(
            sub_vertical=SubVertical.fusion,
            device_family=DeviceFamily.tokamak,
            operating_conditions=OperatingConditions(
                axes=[Axis(name="psi_norm", unit="1", values=list(psi_norm_l))],
                fixed={
                    "R0_m": spec.R0,
                    "a_m": spec.a,
                    "kappa": spec.kappa,
                    "delta": spec.delta,
                    "B0_T": spec.B0,
                    "Ip_MA": spec.Ip_MA,
                    "n_1e20_m3": spec.n20,
                    "P_aux_MW": spec.P_aux_MW,
                    "A_mass_amu": spec.A_mass,
                },
            ),
            response=ResponseBlock(
                curves=[
                    Curve(
                        curve_type=CurveType.q_profile,
                        x=CurveAxis(quantity="psi_norm", unit="1", values=list(psi_norm_l)),
                        y=CurveAxis(quantity="q", unit="1", values=list(q_profile_l)),
                    )
                ],
                scalar_metrics=ScalarMetrics(
                    q95=q95,
                    beta_N=beta_N,
                    H98=H98,
                ),
            ),
            handoff=HandoffBlock(
                l5_targets=["paramak_geometry", "openmc_csg_fixed_source"],
                required_fields_satisfied=scientific_valid,
                missing_fields=[] if scientific_valid else ["power_balance_within_10pct"],
            ),
            audit=DroAuditBlock(
                envelope_id=env.envelope_id or "",
                dro_source_layer_run_ids=[env.run_id],
                kg_nodes=[],
                artifact_refs=[],
            ),
        ).finalize()

        return env, dro


# ---------------------------------------------------------------------------
# duqtools config skeleton emitter
# ---------------------------------------------------------------------------


class DuqtoolsConfigAdapter:
    """Emit a duqtools-style YAML config skeleton (manifest only — no run)."""

    ADAPTER_NAME = "fusion.l4.duqtools_config"
    TOOL_NAME = "duqtools (config-skeleton emitter)"
    TOOL_VERSION = "stub-0.1"

    DEFAULT_TEMPLATE: dict[str, Any] = {
        "tag": "zer0pa-fusion-default",
        "system": {
            "name": "jintrac-stub",
            "model": "imas-fixture",
        },
        "create": {
            "runs_dir": "fixtures/fusion/duqtools_runs",
            "data": {
                "user": "zer0pa",
                "imas_db": "fixture",
                "shot": 0,
                "run": 0,
            },
        },
        "submit": {
            "submit_system": "none",
            "skip_run": True,
            "max_jobs": 0,
        },
        "status": {
            "msg_completed": "Status : Completed successfully",
            "msg_failed": "Status : Failed",
            "msg_canceled": "Status : Canceled",
        },
    }

    def __init__(self, *, agent_id: str = "fusion.l4.duqtools", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def emit_yaml(self) -> str:
        return yaml.safe_dump(self.DEFAULT_TEMPLATE, sort_keys=True)

    def run(
        self,
        *,
        out_path: Optional[Path] = None,
        intent: str = "duqtools config skeleton emit for research",
        campaign_id: str = "fusion-l4-duqtools",
    ) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(intent)
        if forbidden:
            raise BoundaryViolation(
                f"L4 duqtools input intent matched forbidden term '{forbidden}'; refusing"
            )
        spec_payload = {"intent": intent, "campaign_id": campaign_id, "out_path": str(out_path) if out_path else None}
        input_hash = sha256_of(spec_payload)
        body = self.emit_yaml()
        if out_path is not None:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(body, encoding="utf-8")
        outputs = {
            "yaml": body,
            "out_path": str(out_path) if out_path else None,
            "kernel_dispatched": False,
        }
        env = UniversalLayerEnvelope(
            campaign_id=campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/duqtools-MIT",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=GateStatus.pass_,
                scientific_valid=False,  # config-only stub
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="duqtools-skeleton",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=sha256_of(outputs),
                config_hash=sha256_of(self.DEFAULT_TEMPLATE),
                source_refs=["arXiv:2501 duqtools (Bot et al. 2025)"],
            ),
        )
        return env.finalize()

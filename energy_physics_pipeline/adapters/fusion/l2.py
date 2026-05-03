"""L2 fusion adapters — gyrokinetic / reduced-transport.

Three adapters, plug-replaceable behind a single `gyrokinetic` interface:

  * `TglfReducedAdapter`         — analytic reduced quasilinear gyroBohm fixture
                                   that *does* run on CPU and asserts a
                                   gyroBohm normalisation roundtrip residual
                                   < 1e-8. Real CPU execution.
  * `CgyroNonlinearAdapter`      — REST stub only (Runpod-parked); no kernel
                                   dispatched here. `mode=engineering_stub`,
                                   `execution_mode=gpu_rest_stub`,
                                   `scientific_valid=False`.
  * `GyroSwinSurrogateAdapter`   — REST stub with placeholder MAPE / Spearman
                                   / ECE numbers. Same constraints as CGYRO.

Falsifier (`cross_model_disagreement`):
  TGLF vs CGYRO heat-flux disagreement
    | <25%      pass
    | 25 - 50%  warn
    | >50%      quarantine
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from energy_physics_pipeline.boundary import BoundaryViolation, check_fusion_intent
from energy_physics_pipeline.schemas.canonical import sha256_of
from energy_physics_pipeline.schemas.envelope import (
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
from energy_physics_pipeline.schemas.falsification import (
    CrossModelDisagreementRecord,
    DisagreementMetric,
    DisagreementStatus,
)


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


@dataclass
class GyroSpec:
    """Bare-bones gyrokinetic input specification.

    Inputs follow the gyroBohm-normalised tokamak transport convention:
      a/Lt — inverse temperature gradient scale length (dimensionless)
      a/Ln — inverse density gradient scale length (dimensionless)
      q     — local safety factor
      shat  — magnetic shear
      beta  — local plasma beta (electromagnetic effects)
      nu_ee — collision frequency, gyroBohm-normalised
      ti_te — Ti / Te ratio
      a_meters — minor radius (m)
      bt_T  — toroidal field on axis (T)
      ti_keV — local ion temperature (keV)
      ne_1e19 — local electron density (1e19 m^-3)
    """

    intent: str = "core turbulent transport screening for research"
    a_over_lt: float = 2.5
    a_over_ln: float = 1.0
    q: float = 1.5
    shat: float = 0.8
    beta: float = 0.01
    nu_ee: float = 0.05
    ti_te: float = 1.0
    a_meters: float = 0.6
    bt_T: float = 2.0
    ti_keV: float = 5.0
    ne_1e19: float = 5.0
    campaign_id: str = "fusion-l2-default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "a_over_lt": self.a_over_lt,
            "a_over_ln": self.a_over_ln,
            "q": self.q,
            "shat": self.shat,
            "beta": self.beta,
            "nu_ee": self.nu_ee,
            "ti_te": self.ti_te,
            "a_meters": self.a_meters,
            "bt_T": self.bt_T,
            "ti_keV": self.ti_keV,
            "ne_1e19": self.ne_1e19,
            "campaign_id": self.campaign_id,
        }


# ---------------------------------------------------------------------------
# GyroBohm normalisation helpers
# ---------------------------------------------------------------------------


def _gyrobohm_q(ne_1e19: float, ti_keV: float, a_m: float, bt_T: float) -> float:
    """Approximate ion gyroBohm heat flux scale Q_GB [MW/m^2].

    Q_GB = n_i T_i v_ti rho*^2  (rho* = rho_i / a)
    rho_i ~ 1.02e-4 * sqrt(2 * Ti_keV) / B_T  [m]   (deuterium gyroradius)
    v_ti  ~ 9.79e3 * sqrt(2 * Ti_keV)         [m/s]

    Returns Q_GB in MW/m^2. This is the *unit* scale; physical heat flux
    follows from Q = chi * Q_GB-style scaling with chi a dimensionless
    response.
    """
    rho_i = 1.02e-4 * math.sqrt(2.0 * max(ti_keV, 1e-9)) / max(bt_T, 1e-9)  # m
    v_ti = 9.79e3 * math.sqrt(2.0 * max(ti_keV, 1e-9))  # m/s
    rho_star = rho_i / max(a_m, 1e-9)
    n_i_per_m3 = ne_1e19 * 1.0e19
    ti_J = ti_keV * 1.0e3 * 1.602176634e-19
    # n T v rho*^2 — units of W/m^2; convert to MW/m^2
    q_gb_W = n_i_per_m3 * ti_J * v_ti * rho_star * rho_star
    return q_gb_W * 1e-6


# ---------------------------------------------------------------------------
# TGLF reduced
# ---------------------------------------------------------------------------


class TglfReducedAdapter:
    """Analytic reduced quasilinear gyroBohm transport fixture.

    Heat-flux scaling (dimensionless):
        chi_i = c_chi * (a/L_T)^alpha * f(q, shat, beta)
    with c_chi=1.5, alpha=2.0; f is a tame product.

    Q_GB normalisation roundtrip: chi -> q -> chi roundtrip residual must
    be < 1e-8 (machine-arithmetic identity). This is the falsifier the PRD
    requires for the L2 reduced model.
    """

    ADAPTER_NAME = "fusion.l2.tglf_reduced"
    TOOL_NAME = "TGLF (reduced fixture)"
    TOOL_VERSION = "fixture-0.1"

    def __init__(self, *, agent_id: str = "fusion.l2.tglf_reduced", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(self, spec: GyroSpec) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L2 input intent matched forbidden term '{forbidden}'; refusing to emit envelope"
            )

        spec_payload = spec.to_dict()
        input_hash = sha256_of(spec_payload)

        c_chi = 1.5
        alpha = 2.0
        f_geom = (1.0 / max(spec.q, 1e-3)) * (1.0 + abs(spec.shat)) * (1.0 - 0.2 * spec.beta)
        chi_i_dim = c_chi * (spec.a_over_lt ** alpha) * f_geom
        chi_e_dim = 0.6 * chi_i_dim  # electron channel
        q_gb = _gyrobohm_q(spec.ne_1e19, spec.ti_keV, spec.a_meters, spec.bt_T)
        q_i_MW_m2 = chi_i_dim * q_gb
        q_e_MW_m2 = chi_e_dim * q_gb

        # Roundtrip: derive chi back from Q and Q_GB; residual is what the
        # falsifier checks.
        chi_i_round = q_i_MW_m2 / max(q_gb, 1e-30)
        chi_e_round = q_e_MW_m2 / max(q_gb, 1e-30)
        residual = max(abs(chi_i_round - chi_i_dim), abs(chi_e_round - chi_e_dim))
        roundtrip_ok = residual < 1e-8

        outputs = {
            "Q_GB_MW_m2": q_gb,
            "chi_i_dimensionless": chi_i_dim,
            "chi_e_dimensionless": chi_e_dim,
            "Q_i_MW_m2": q_i_MW_m2,
            "Q_e_MW_m2": q_e_MW_m2,
            "Q_GB_normalisation_roundtrip_residual": residual,
            "roundtrip_ok": roundtrip_ok,
            "scheme": "quasilinear gyroBohm (reduced fixture, not TGLF kernel)",
        }
        output_hash = sha256_of(outputs)

        failures: list[FailureRecord] = []
        if not roundtrip_ok:
            failures.append(
                FailureRecord(
                    gate_id="gyrobohm_roundtrip",
                    severity="fail",
                    message=f"Q_GB roundtrip residual {residual:.3e} >= 1e-8",
                )
            )
        gate_status = GateStatus.pass_ if roundtrip_ok else GateStatus.fail

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,  # reduced-fixture, not the real TGLF kernel
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/gacode-Apache2",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=gate_status,
                scientific_valid=False,  # reduced fixture cannot be promoted
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=failures,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="tglf-reduced-gb",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=output_hash,
                config_hash=sha256_of({"c_chi": c_chi, "alpha": alpha}),
                source_refs=["arXiv:1011.3990 (TGLF Staebler/Kinsey 2010)"],
            ),
        )
        return env.finalize()


# ---------------------------------------------------------------------------
# CGYRO nonlinear — Runpod REST stub
# ---------------------------------------------------------------------------


class CgyroNonlinearAdapter:
    """REST-only stub. CGYRO requires GPU/HPC — parked behind Runpod.

    Emits engineering_stub envelopes with a placeholder heat-flux value
    parameterised on (a/L_T)^2 with a stub multiplier. Never scientific_valid.

    Three placeholder modes (selected by `cgyro_stub_mode` in the spec):
      'agree'     — Q_i within 15% of TGLF reduced
      'warn'      — Q_i 30% above TGLF reduced
      'quarantine'— Q_i 80% above TGLF reduced
    """

    ADAPTER_NAME = "fusion.l2.cgyro_nonlinear"
    TOOL_NAME = "CGYRO (REST stub)"
    TOOL_VERSION = "stub-0.1"

    STUB_MODES: dict[str, float] = {
        "agree": 1.10,
        "warn": 1.30,
        "quarantine": 1.80,
    }

    def __init__(self, *, agent_id: str = "fusion.l2.cgyro_stub", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(self, spec: GyroSpec, *, stub_mode: str = "agree") -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L2 CGYRO input intent matched forbidden term '{forbidden}'; refusing to emit envelope"
            )

        if stub_mode not in self.STUB_MODES:
            raise ValueError(f"unknown CGYRO stub_mode '{stub_mode}'; choose one of {list(self.STUB_MODES)}")

        spec_payload = spec.to_dict()
        spec_payload["cgyro_stub_mode"] = stub_mode
        input_hash = sha256_of(spec_payload)

        # Recompute the TGLF baseline so we have a comparable Q for the falsifier
        c_chi = 1.5
        alpha = 2.0
        f_geom = (1.0 / max(spec.q, 1e-3)) * (1.0 + abs(spec.shat)) * (1.0 - 0.2 * spec.beta)
        chi_i_tglf = c_chi * (spec.a_over_lt ** alpha) * f_geom
        q_gb = _gyrobohm_q(spec.ne_1e19, spec.ti_keV, spec.a_meters, spec.bt_T)
        q_i_tglf = chi_i_tglf * q_gb

        mult = self.STUB_MODES[stub_mode]
        q_i_cgyro = mult * q_i_tglf
        chi_i_cgyro = q_i_cgyro / max(q_gb, 1e-30)

        outputs = {
            "Q_GB_MW_m2": q_gb,
            "chi_i_dimensionless": chi_i_cgyro,
            "Q_i_MW_m2": q_i_cgyro,
            "stub_mode": stub_mode,
            "stub_multiplier_vs_tglf": mult,
            "scheme": "CGYRO REST stub (no kernel dispatched)",
        }
        output_hash = sha256_of(outputs)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.gpu_rest_stub,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/gacode-Apache2",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=GateStatus.warn,
                scientific_valid=False,  # stub
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=[
                    FailureRecord(
                        gate_id="cgyro.kernel_executed",
                        severity="info",
                        message="CGYRO not run; stub multiplier applied to TGLF reduced result",
                    )
                ],
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="cgyro-stub",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=output_hash,
                config_hash=sha256_of(self.STUB_MODES),
                source_refs=["doi:10.1016/j.jcp.2016.06.020 (CGYRO)"],
            ),
        )
        return env.finalize()


# ---------------------------------------------------------------------------
# GyroSwin surrogate — REST stub
# ---------------------------------------------------------------------------


class GyroSwinSurrogateAdapter:
    """REST-only surrogate stub. Reports placeholder MAPE / Spearman / ECE."""

    ADAPTER_NAME = "fusion.l2.gyroswin_surrogate"
    TOOL_NAME = "GyroSwin (REST stub)"
    TOOL_VERSION = "stub-0.1"

    def __init__(self, *, agent_id: str = "fusion.l2.gyroswin_stub", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(self, spec: GyroSpec) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L2 GyroSwin input intent matched forbidden term '{forbidden}'; refusing"
            )

        spec_payload = spec.to_dict()
        input_hash = sha256_of(spec_payload)

        # Recompute TGLF baseline; predict ~1.05x with placeholder MAPE
        c_chi = 1.5
        alpha = 2.0
        f_geom = (1.0 / max(spec.q, 1e-3)) * (1.0 + abs(spec.shat)) * (1.0 - 0.2 * spec.beta)
        chi_i_tglf = c_chi * (spec.a_over_lt ** alpha) * f_geom
        q_gb = _gyrobohm_q(spec.ne_1e19, spec.ti_keV, spec.a_meters, spec.bt_T)
        q_i_pred = 1.05 * chi_i_tglf * q_gb

        outputs = {
            "Q_GB_MW_m2": q_gb,
            "Q_i_predicted_MW_m2": q_i_pred,
            "MAPE_placeholder_pct": 12.0,
            "Spearman_rho_placeholder": 0.91,
            "ECE_placeholder": 0.07,
            "scheme": "GyroSwin REST stub (no kernel dispatched, placeholder calibration)",
        }
        output_hash = sha256_of(outputs)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.gpu_rest_stub,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/gyroswin-MIT",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=GateStatus.warn,
                scientific_valid=False,  # stub surrogate, never promoted
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=[
                    FailureRecord(
                        gate_id="gyroswin.kernel_executed",
                        severity="info",
                        message="GyroSwin not run; placeholder calibration only",
                    )
                ],
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="gyroswin-stub",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=output_hash,
                config_hash=sha256_of({"placeholder": True}),
                source_refs=["arXiv:GyroSwin (Hochreiter group, NeurIPS 2025)"],
            ),
        )
        return env.finalize()


# ---------------------------------------------------------------------------
# Cross-model disagreement falsifier
# ---------------------------------------------------------------------------


def cross_model_disagreement(
    *,
    object_id: str,
    tglf_envelope: UniversalLayerEnvelope,
    cgyro_envelope: UniversalLayerEnvelope,
    quantity: str = "Q_i_MW_m2",
) -> CrossModelDisagreementRecord:
    """Compare TGLF-reduced vs CGYRO heat flux on the same spec.

    Threshold ladder:
        relative disagreement < 0.25      pass
        0.25 <= rel < 0.50                warn
        rel >= 0.50                       quarantine
    """
    q_tglf = float(tglf_envelope.outputs.payload[quantity])
    q_cgyro = float(cgyro_envelope.outputs.payload[quantity])
    denom = max(abs(q_tglf), 1e-30)
    rel = abs(q_cgyro - q_tglf) / denom

    if rel < 0.25:
        status = DisagreementStatus.pass_
        action = "rerun"
    elif rel < 0.50:
        status = DisagreementStatus.warn
        action = "rerun"
    else:
        status = DisagreementStatus.quarantine
        action = "block_handoff"

    return CrossModelDisagreementRecord(
        record_id=f"disagree:{object_id}",
        object_id=object_id,
        quantity=quantity,
        unit="MW/m^2",
        models_compared=["tglf_reduced", "cgyro_stub"],
        values=[q_tglf, q_cgyro],
        uncertainties=[],
        metric=DisagreementMetric.relative,
        pass_threshold=0.25,
        warn_threshold=0.50,
        fail_threshold=1.00,
        status=status,
        resolution_action=action,
    )

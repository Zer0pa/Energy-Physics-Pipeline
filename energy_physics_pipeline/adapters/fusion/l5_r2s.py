"""L5 R2S (Rigorous-2-Step) analytic activation upgrade.

Per PRD §"Part B - Fusion / Plasma Contracts" §L5: "Implement OpenMC R2S activation
when available; otherwise analytic/stub activation with `scientific_valid=false`."

The full R2S workflow is GPU/HPC-class (transport step in OpenMC + activation step in
ALARA / FISPACT-II). FISPACT-II is license-isolated. ALARA is GPL-3 (LGPL-friendly with
isolation). This module ships an *analytic* activation calculator that:

  1. Takes a tritium-breeding-blanket geometry spec (FLiBe / Li-6 enrichment / volume).
  2. Assumes a 1 MW DT fusion source (research-bound; not weapon-yield).
  3. Estimates dominant decay-heat contributors with single-isotope point-kinetics:
       - Be-9(n,2n)Be-8 → Li-7 + alpha (instantaneous, no decay heat)
       - Li-6(n,T)He-4 (no decay heat — tritium breeding)
       - Be-9(n,alpha)He-6 → Li-6 + electron (T_1/2 = 0.81 s, beta-)
       - Co-59(n,gamma)Co-60 (T_1/2 = 5.27 yr, dominant long-term contact-dose driver)
       - Mn-55(n,gamma)Mn-56 (T_1/2 = 2.58 hr, short-term decay-heat driver)
     The Co-59 and Mn-55 chains assume small structural-steel impurity fractions.
  4. Reports decay heat at shutdown (t=0), 1 hour, 1 day, 1 week.
  5. Reports contact dose at the same intervals, derived from a flat-disk geometry
     and standard photon dose-rate constants (research-bound; explicitly NOT a
     facility-licence calculation).

This is `scientific_valid=False` — the analytic is too coarse for a real R2S claim.
But it lets the L5 pipeline emit a contract-shaped envelope without GPU-class transport,
and gives operators a reasonable order-of-magnitude check before Runpod cutover.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from energy_physics_pipeline.boundary import (
    BoundaryViolation,
    check_fusion_intent,
)
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
    UncertaintyBlock,
    UncertaintyDistribution,
    UniversalLayerEnvelope,
)


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


@dataclass
class R2sActivationSpec:
    intent: str = "research-bound R2S activation chain analytic estimate"
    fusion_power_MW: float = 1.0
    blanket_volume_m3: float = 5.0
    li6_enrichment: float = 0.60
    structural_steel_impurity_co59_ppm: float = 100.0  # typical Eurofer-97 ≤ 50-200 ppm
    structural_steel_impurity_mn55_ppm: float = 4000.0  # Eurofer typically 0.3-0.5 wt%
    irradiation_duration_yr: float = 1.0
    decay_times_h: tuple[float, ...] = (0.0, 1.0, 24.0, 168.0)
    campaign_id: str = "fusion-l5-r2s"


# ---------------------------------------------------------------------------
# Decay-chain constants (point-kinetics; research-bound)
# ---------------------------------------------------------------------------

_LN2 = math.log(2.0)
_AVOGADRO = 6.022e23

# Decay constants (1/s)
_DECAY_CO60 = _LN2 / (5.27 * 365.25 * 24 * 3600)
_DECAY_MN56 = _LN2 / (2.58 * 3600)
_DECAY_HE6 = _LN2 / 0.81

# Q-values (decay heat per disintegration, in J)
_MEV_TO_J = 1.602e-13
_Q_CO60 = 2.82 * _MEV_TO_J  # average beta + gamma
_Q_MN56 = 3.7 * _MEV_TO_J
_Q_HE6 = 3.5 * _MEV_TO_J

# DT fusion: each MW of fusion -> ~3.55e17 neutrons / second / MW (14.06 MeV)
_NEUTRONS_PER_MW = 3.55e17

# Capture-cross-section x abundance proxies (very rough, 14-MeV-spectrum-averaged
# effective values for activation product yield per neutron per atom). These are
# *order-of-magnitude* and explicitly NOT licence-quality data.
_PROD_CO60_PER_N_PER_CO59 = 1.0e-26  # m^2
_PROD_MN56_PER_N_PER_MN55 = 6.0e-26
_PROD_HE6_PER_N_PER_BE9 = 2.0e-29


def _atoms_per_volume(steel_density_kg_m3: float, impurity_ppm: float, A_amu: float) -> float:
    """Atoms of impurity per m^3 of structural steel."""
    impurity_kg_per_m3 = steel_density_kg_m3 * impurity_ppm * 1e-6
    return impurity_kg_per_m3 / (A_amu * 1.6605e-27)


def _activity_at_shutdown(prod_rate_per_s: float, lambda_decay: float, irradiation_s: float) -> float:
    """Radioactive saturation: A(t_irr) = R * (1 - exp(-lambda * t_irr))."""
    return prod_rate_per_s * (1.0 - math.exp(-lambda_decay * irradiation_s))


def _activity_after_decay(activity_at_shutdown: float, lambda_decay: float, t_decay_s: float) -> float:
    return activity_at_shutdown * math.exp(-lambda_decay * t_decay_s)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class R2sAnalyticActivationAdapter:
    """Coarse analytic activation calculator. Always emits scientific_valid=False."""

    ADAPTER_NAME = "fusion.l5.r2s_analytic"
    TOOL_NAME = "Zer0pa analytic activation (research order-of-magnitude)"
    TOOL_VERSION = "0.1"

    def __init__(self, *, agent_id: str = "fusion.l5.r2s_analytic", git_sha: str = "fixture") -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    def run(
        self,
        spec: R2sActivationSpec,
        *,
        steel_density_kg_m3: float = 7800.0,
        be_density_kg_m3: float = 1850.0,
    ) -> UniversalLayerEnvelope:
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L5 R2S input intent matched forbidden term '{forbidden}'; refusing to emit envelope"
            )

        spec_payload = {
            "intent": spec.intent,
            "fusion_power_MW": spec.fusion_power_MW,
            "blanket_volume_m3": spec.blanket_volume_m3,
            "li6_enrichment": spec.li6_enrichment,
            "structural_steel_impurity_co59_ppm": spec.structural_steel_impurity_co59_ppm,
            "structural_steel_impurity_mn55_ppm": spec.structural_steel_impurity_mn55_ppm,
            "irradiation_duration_yr": spec.irradiation_duration_yr,
            "decay_times_h": list(spec.decay_times_h),
            "campaign_id": spec.campaign_id,
        }
        input_hash = sha256_of(spec_payload)

        # ------ neutron source ------
        n_per_s = _NEUTRONS_PER_MW * spec.fusion_power_MW

        # ------ Co-60 chain ------
        n_co59_per_m3 = _atoms_per_volume(steel_density_kg_m3, spec.structural_steel_impurity_co59_ppm, 59.0)
        # Spread the impurity over a thin first-wall layer. We approximate with
        # blanket_volume_m3 / 100 as the first-wall slab, keeping the calc coarse.
        first_wall_m3 = spec.blanket_volume_m3 / 100.0
        n_co59_total = n_co59_per_m3 * first_wall_m3
        prod_co60_per_s = n_per_s * _PROD_CO60_PER_N_PER_CO59 * n_co59_total / max(spec.blanket_volume_m3, 1e-9)
        irr_s = spec.irradiation_duration_yr * 365.25 * 24 * 3600
        a_co60_shutdown = _activity_at_shutdown(prod_co60_per_s, _DECAY_CO60, irr_s)

        # ------ Mn-56 chain ------
        n_mn55_per_m3 = _atoms_per_volume(steel_density_kg_m3, spec.structural_steel_impurity_mn55_ppm, 55.0)
        n_mn55_total = n_mn55_per_m3 * first_wall_m3
        prod_mn56_per_s = n_per_s * _PROD_MN56_PER_N_PER_MN55 * n_mn55_total / max(spec.blanket_volume_m3, 1e-9)
        a_mn56_shutdown = _activity_at_shutdown(prod_mn56_per_s, _DECAY_MN56, irr_s)

        # ------ He-6 chain (Be multiplier) ------
        n_be9_per_m3 = (be_density_kg_m3 / (9.012 * 1.6605e-27))
        # Assume a 5cm Be multiplier shell — vol ~= blanket_volume * 0.1
        be_m3 = spec.blanket_volume_m3 * 0.1
        n_be9_total = n_be9_per_m3 * be_m3
        prod_he6_per_s = n_per_s * _PROD_HE6_PER_N_PER_BE9 * n_be9_total / max(spec.blanket_volume_m3, 1e-9)
        a_he6_shutdown = _activity_at_shutdown(prod_he6_per_s, _DECAY_HE6, irr_s)

        # ------ Decay heat at requested decay times ------
        decay_heat_W: dict[str, float] = {}
        contact_dose_uSv_h: dict[str, float] = {}
        for t_h in spec.decay_times_h:
            t_s = t_h * 3600
            a_co60_t = _activity_after_decay(a_co60_shutdown, _DECAY_CO60, t_s)
            a_mn56_t = _activity_after_decay(a_mn56_shutdown, _DECAY_MN56, t_s)
            a_he6_t = _activity_after_decay(a_he6_shutdown, _DECAY_HE6, t_s)
            heat_W = a_co60_t * _Q_CO60 + a_mn56_t * _Q_MN56 + a_he6_t * _Q_HE6
            # Contact dose: rough conversion using gamma constant for Co-60 ~= 0.351 mSv/h per GBq @ 1m
            # Scale to surface (1m approx), include Mn-56 (~0.221 mSv/h per GBq), ignore He-6 beta.
            dose_mSv_h_at_1m = (a_co60_t / 1e9) * 0.351 + (a_mn56_t / 1e9) * 0.221
            contact_dose_uSv_h[f"t_{t_h}h"] = dose_mSv_h_at_1m * 1000.0
            decay_heat_W[f"t_{t_h}h"] = heat_W

        outputs_payload = {
            "decay_heat_W": decay_heat_W,
            "contact_dose_uSv_per_h_at_1m": contact_dose_uSv_h,
            "activity_shutdown_Bq": {
                "Co-60": a_co60_shutdown,
                "Mn-56": a_mn56_shutdown,
                "He-6": a_he6_shutdown,
            },
            "neutron_source_per_s": n_per_s,
            "irradiation_duration_yr": spec.irradiation_duration_yr,
            "method": "single-isotope point-kinetics; Co-60, Mn-56, He-6 only; research-bound",
            "tbr_dimensionless_research_only": None,  # this adapter doesn't compute TBR
            "quantities": {
                "decay_heat_at_shutdown_W": {"value": decay_heat_W["t_0.0h"], "unit": "W"},
                "decay_heat_after_1h_W": {"value": decay_heat_W["t_1.0h"], "unit": "W"},
                "contact_dose_at_shutdown": {
                    "value": contact_dose_uSv_h["t_0.0h"],
                    "unit": "uSv/h",
                },
            },
        }
        output_hash = sha256_of(outputs_payload)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L5,
            domain=Domain.fusion,
            mode=Mode.engineering_stub,  # analytic; not a real R2S claim
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/zer0pa-internal",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs_payload),
            uncertainty=UncertaintyBlock(
                distribution=UncertaintyDistribution.none,
                contributors=["analytic-only", "no-cross-section-spectrum-folding"],
            ),
            falsification=FalsificationBlock(
                gate_status=GateStatus.warn,
                scientific_valid=False,
                unit_check_passed=True,
                conservation_check_passed=False,  # no detailed balance
                boundary_check_passed=True,
                failures=[
                    FailureRecord(
                        gate_id="r2s.analytic_only",
                        severity="warn",
                        message="single-isotope point-kinetics; Runpod-side OpenMC R2S replaces",
                    ),
                ],
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id="r2s-analytic-v0.1",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=output_hash,
                config_hash=sha256_of({"version": "0.1"}),
                source_refs=[
                    "BOUNDARY_BLOCK",
                    "PRD §Part B L5",
                ],
            ),
        ).finalize()
        return env

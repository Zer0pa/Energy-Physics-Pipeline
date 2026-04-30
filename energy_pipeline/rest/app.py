"""FastAPI application — REST stubs for every GPU/HPC layer endpoint.

Stubs return canned outputs that match the real shape contract. They emit envelopes
with `mode=engineering_stub`, `execution_mode=gpu_rest_stub`, and `scientific_valid=False`.

Config-flag cutover: when ENERGY_L?_BACKEND=runpod_rest, the same endpoint shape forwards
to the Runpod backend (not implemented in this CPU-side build — placeholder 503).
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from energy_pipeline.boundary import BOUNDARY_BLOCK, check_fusion_intent
from energy_pipeline.l6.config import get_config
from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    GateStatus,
    IOBlock,
    ProvenanceBlock,
    UncertaintyBlock,
    UncertaintyDistribution,
)


def _stub_envelope(
    *,
    sub_vertical: SubVertical,
    layer: LayerLevel,
    domain: Domain,
    tool: str,
    tool_version: str,
    payload_in: dict[str, Any],
    payload_out: dict[str, Any],
) -> UniversalLayerEnvelope:
    env = UniversalLayerEnvelope(
        campaign_id=str(payload_in.get("campaign_id", "stub")),
        sub_vertical=sub_vertical,
        layer=layer,
        domain=domain,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter=f"rest-stub::{tool}",
            tool=tool,
            tool_version=tool_version,
            execution_mode=ExecutionMode.gpu_rest_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/stub",
        ),
        inputs=IOBlock(payload=payload_in),
        outputs=IOBlock(payload=payload_out),
        uncertainty=UncertaintyBlock(distribution=UncertaintyDistribution.none),
        falsification=FalsificationBlock(
            gate_status=GateStatus.warn,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=False,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="rest-stub",
            model_id="n/a",
            git_sha="local",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
            artifact_hashes=[],
            source_refs=[],
        ),
    ).finalize()
    return env


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zer0pa Energy REST stubs",
        version="0.1.0",
        description=BOUNDARY_BLOCK,
    )

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        cfg = get_config()
        return {
            "ok": True,
            "boundary": BOUNDARY_BLOCK,
            "config": {
                "execution_profile": cfg.execution_profile,
                "l1_backend": cfg.l1_backend,
                "l2_backend": cfg.l2_backend,
                "l3_backend": cfg.l3_backend,
                "l4_backend": cfg.l4_backend,
                "l5_backend": cfg.l5_backend,
                "l6_backend": cfg.l6_backend,
                "fusion_gyroswin_backend": cfg.fusion_gyroswin_backend,
                "reasoner_backend": cfg.reasoner_backend,
            },
        }

    @app.get("/v1/boundary")
    def boundary() -> dict[str, str]:
        return {"boundary": BOUNDARY_BLOCK}

    # --- Electrochemistry L1 ---
    @app.post("/v1/electrochem/l1/singlepoint")
    def ec_l1_singlepoint(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "battery")),
            tool="PySCF-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "quantities": {"E_total_Ha": {"value": -76.241, "unit": "hartree"}},
                "convergence": "stub",
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/electrochem/l1/relax")
    def ec_l1_relax(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "battery")),
            tool="GPAW-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "geometry_relaxed": [],
                "max_force_eVA": 0.05,
                "quantities": {"max_force": {"value": 0.05, "unit": "eV/Å"}},
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/electrochem/l1/adsorption-profile")
    def ec_l1_adsorption(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "green_h2")),
            tool="PySCF-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "ads_energies_eV": [{"site": "top", "value": -0.42, "unit": "eV"}],
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/electrochem/l1/marcus")
    def ec_l1_marcus(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "battery")),
            tool="PySCF-CDFT-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "lambda_eV": {"value": 0.85, "unit": "eV"},  # reorganisation energy
                "delta_G0_eV": {"value": -0.10, "unit": "eV"},
                "k_et_s_inv": {"value": 1.2e6, "unit": "1/s"},
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/electrochem/l1/optical-spectrum")
    def ec_l1_optical(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "pv")),
            tool="GPAW-BSE-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "band_gap_eV": {"value": 1.55, "unit": "eV"},
                "spectrum": {"x_unit": "eV", "y_unit": "arb"},
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/electrochem/l1/topology")
    def ec_l1_topology(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domain=Domain(payload.get("domain", "thermoelectric")),
            tool="Z2Pack-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={"Z2_invariants": [0, 0, 0, 0]},
        )
        return env.model_dump(mode="json")

    # --- Electrochemistry L2 ---
    @app.post("/v1/electrochem/l2/mlip-md")
    def ec_l2_mlip(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L2,
            domain=Domain(payload.get("domain", "battery")),
            tool="MACE-OMol25-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "msd_fit_R2": 0.97,
                "diffusion_exponent": 1.02,
                "D_self": {"value": 1.7e-10, "unit": "m^2/s"},
            },
        )
        return env.model_dump(mode="json")

    # --- Electrochemistry L3 ---
    @app.post("/v1/electrochem/l3/phasefield")
    def ec_l3_phasefield(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L3,
            domain=Domain(payload.get("domain", "battery")),
            tool="MOOSE-RACCOON-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "tortuosity": 1.7,
                "effective_diffusivity": {"value": 5.2e-12, "unit": "m^2/s"},
                "mass_drift": 1e-6,
                "charge_residual": 1e-5,
            },
        )
        return env.model_dump(mode="json")

    # --- Electrochemistry L4 ---
    @app.post("/v1/electrochem/l4/pybamm")
    def ec_l4_pybamm(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domain=Domain.battery,
            tool="PyBaMM-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "curve_voltage_time": {"x_unit": "s", "y_unit": "V"},
                "soc_range": [0.0, 1.0],
            },
        )
        return env.model_dump(mode="json")

    # --- Electrochemistry L5 ---
    @app.post("/v1/electrochem/l5/lcoe")
    def ec_l5_lcoe(payload: dict[str, Any]) -> dict[str, Any]:
        env = _stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L5,
            domain=Domain(payload.get("domain", "pv")),
            tool="PySAM-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "lcoe_p05_USD_per_kWh": 0.034,
                "lcoe_p50_USD_per_kWh": 0.041,
                "lcoe_p95_USD_per_kWh": 0.052,
            },
        )
        return env.model_dump(mode="json")

    # --- Fusion ---
    def _fusion_intent_check(payload: dict[str, Any]) -> None:
        intent_blob = " ".join(
            [
                str(payload.get("intent", "")),
                str(payload.get("description", "")),
                str(payload.get("notes", "")),
            ]
        )
        hit = check_fusion_intent(intent_blob)
        if hit:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"fusion request blocked by boundary: matched forbidden intent '{hit}'. "
                    "Reframe to allowed research scope (blanket / breeding-blanket / equilibrium / disruption)."
                ),
            )

    @app.post("/v1/fusion/l1/transport")
    def fu_l1(payload: dict[str, Any]) -> dict[str, Any]:
        _fusion_intent_check(payload)
        env = _stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L1,
            domain=Domain.fusion,
            tool="OpenMC-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "tally_keff": {"value": 0.0, "unit": "1"},
                "tally_relative_error": 0.05,
                "library_version": "ENDF/B-VIII.1",
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/fusion/l2/gyrokinetic")
    def fu_l2(payload: dict[str, Any]) -> dict[str, Any]:
        _fusion_intent_check(payload)
        env = _stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domain=Domain.fusion,
            tool="GACODE-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "Q_GB_ion": 1.4,
                "Q_GB_electron": 0.9,
                "tglf_cgyro_disagreement_pct": 22.0,
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/fusion/l3/equilibrium")
    def fu_l3(payload: dict[str, Any]) -> dict[str, Any]:
        _fusion_intent_check(payload)
        env = _stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L3,
            domain=Domain.fusion,
            tool="FreeGS4E-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "psi_axis": -0.5,
                "psi_boundary": 0.0,
                "q95": 3.6,
                "x_points": [{"R": 1.6, "Z": -1.1}],
                "topology": "diverted",
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/fusion/l4/scenario")
    def fu_l4(payload: dict[str, Any]) -> dict[str, Any]:
        _fusion_intent_check(payload)
        env = _stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            tool="IMAS-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "ids_version": "3.41.0",
                "ids_paths_used": ["equilibrium", "core_profiles", "summary"],
                "power_balance_residual_pct": 8.0,
            },
        )
        return env.model_dump(mode="json")

    @app.post("/v1/fusion/l5/neutronics")
    def fu_l5(payload: dict[str, Any]) -> dict[str, Any]:
        _fusion_intent_check(payload)
        env = _stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L5,
            domain=Domain.fusion,
            tool="OpenMC-Paramak-stub",
            tool_version="0.0.1",
            payload_in=payload,
            payload_out={
                "tbr_dimensionless_research_only": 1.13,
                "particle_balance_residual": 1e-4,
                "tally_relative_error": 0.07,
            },
        )
        return env.model_dump(mode="json")

    # Runpod cutover placeholder — same shape, returns 503 until backend lands.
    @app.post("/v1/runpod/{layer}/{domain}")
    def runpod_passthrough(layer: str, domain: str, payload: dict[str, Any]) -> dict[str, Any]:
        cfg = get_config()
        # If config selected runpod_rest for this layer, this endpoint should exist; until
        # Runpod is wired, refuse explicitly.
        raise HTTPException(
            status_code=503,
            detail=(
                f"runpod backend for layer={layer} domain={domain} not yet wired. "
                f"current cfg L{layer}_backend={getattr(cfg, f'l{layer}_backend', 'unknown')}"
            ),
        )

    return app


app = create_app()

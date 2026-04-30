"""FastAPI application — public REST surface for every Energy layer endpoint.

Wave 4 §1: every public `/v1/<sub_vertical>/<layer>/<op>` endpoint routes through
`resolve_and_dispatch`, which reads `ENERGY_L?_BACKEND` and chooses one of:

  * `local_cpu`     → real adapter (where wired) or stub fallback
  * `gpu_rest_stub` / `stub` → existing canned stub envelope
  * `runpod_rest`   → forwards through `RunpodRestAdapter`; structured 503
                      envelope when `ENERGY_RUNPOD_BASE_URL` is empty.

Every accepted response passes through `accept_envelope` so audit/KG and the
production falsifier set apply uniformly. Clients never need to call
`/v1/runpod/...` directly — the same public route is the cutover.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from energy_pipeline.boundary import BOUNDARY_BLOCK, check_fusion_intent
from energy_pipeline.l6 import (
    accept_envelope,
    fusion_intent_or_403,
    resolve_and_dispatch,
)
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

    # ------------------------------------------------------------------
    # Stub builder factory — used by every endpoint as the fallback path
    # ------------------------------------------------------------------

    def _stub_for(
        *,
        sub_vertical: SubVertical,
        layer: LayerLevel,
        tool: str,
        tool_version: str,
        payload_out_factory,
    ):
        """Return a `stub_runner(payload)` lambda for resolve_and_dispatch."""

        def runner(payload: dict[str, Any]) -> UniversalLayerEnvelope:
            try:
                domain = Domain(payload.get("domain", "battery" if sub_vertical == SubVertical.electrochemistry else "fusion"))
            except ValueError:
                domain = Domain.battery if sub_vertical == SubVertical.electrochemistry else Domain.fusion
            return _stub_envelope(
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                tool=tool,
                tool_version=tool_version,
                payload_in=payload,
                payload_out=payload_out_factory(payload),
            )
        return runner

    # ------------------------------------------------------------------
    # Electrochem L1
    # ------------------------------------------------------------------

    @app.post("/v1/electrochem/l1/singlepoint")
    def ec_l1_singlepoint(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "battery")), op="singlepoint",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="PySCF-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "quantities": {"E_total_Ha": {"value": -76.241, "unit": "hartree"}},
                    "convergence": "stub",
                },
            ),
        )

    @app.post("/v1/electrochem/l1/relax")
    def ec_l1_relax(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "battery")), op="relax",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="GPAW-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "geometry_relaxed": [],
                    "quantities": {"max_force": {"value": 0.05, "unit": "eV/Å"}},
                },
            ),
        )

    @app.post("/v1/electrochem/l1/adsorption-profile")
    def ec_l1_adsorption(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "green_h2")), op="adsorption-profile",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="PySCF-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "quantities": {"ads_energy_top": {"value": -0.42, "unit": "eV"}},
                },
            ),
        )

    @app.post("/v1/electrochem/l1/marcus")
    def ec_l1_marcus(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "battery")), op="marcus",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="PySCF-CDFT-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "quantities": {
                        "lambda": {"value": 0.85, "unit": "eV"},
                        "delta_G0": {"value": -0.10, "unit": "eV"},
                        "k_et": {"value": 1.2e6, "unit": "1/s"},
                    },
                },
            ),
        )

    @app.post("/v1/electrochem/l1/optical-spectrum")
    def ec_l1_optical(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "pv")), op="optical-spectrum",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="GPAW-BSE-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "quantities": {"band_gap": {"value": 1.55, "unit": "eV"}},
                },
            ),
        )

    @app.post("/v1/electrochem/l1/topology")
    def ec_l1_topology(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "thermoelectric")), op="topology",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L1,
                tool="Z2Pack-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {"Z2_invariants": [0, 0, 0, 0]},
            ),
        )

    # ------------------------------------------------------------------
    # Electrochem L2
    # ------------------------------------------------------------------

    @app.post("/v1/electrochem/l2/mlip-md")
    def ec_l2_mlip(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L2, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "battery")), op="mlip-md",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L2,
                tool="MACE-OMol25-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "msd_fit_R2": 0.97,
                    "diffusion_exponent": 1.02,
                    "quantities": {"D_self": {"value": 1.7e-10, "unit": "m^2/s"}},
                },
            ),
        )

    # ------------------------------------------------------------------
    # Electrochem L3
    # ------------------------------------------------------------------

    @app.post("/v1/electrochem/l3/phasefield")
    def ec_l3_phasefield(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L3, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "battery")), op="phasefield",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L3,
                tool="MOOSE-RACCOON-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "tortuosity": 1.7,
                    "mass_drift": 1e-6,
                    "charge_residual": 1e-5,
                    "quantities": {
                        "effective_diffusivity": {"value": 5.2e-12, "unit": "m^2/s"},
                    },
                },
            ),
        )

    # ------------------------------------------------------------------
    # Electrochem L4 — same-shape Runpod cutover ON THIS ENDPOINT
    # ------------------------------------------------------------------

    @app.post("/v1/electrochem/l4/pybamm")
    def ec_l4_pybamm(payload: dict[str, Any]):
        def _local_cpu(p: dict[str, Any]) -> UniversalLayerEnvelope:
            from energy_pipeline.adapters.electrochem.l4 import PyBaMMBatteryAdapter

            spec = p.get("spec", p) if isinstance(p.get("spec"), dict) else p
            adapter = PyBaMMBatteryAdapter()
            env, _dro = adapter.run(spec=spec)
            return env

        return resolve_and_dispatch(
            layer=LayerLevel.L4, sub_vertical=SubVertical.electrochemistry,
            domain=Domain.battery, op="pybamm", runpod_op="pybamm",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L4,
                tool="PyBaMM-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "curve_voltage_time": {"x_unit": "s", "y_unit": "V"},
                    "soc_range": [0.0, 1.0],
                },
            ),
            local_cpu_runner=_local_cpu,
        )

    # ------------------------------------------------------------------
    # Electrochem L5
    # ------------------------------------------------------------------

    @app.post("/v1/electrochem/l5/lcoe")
    def ec_l5_lcoe(payload: dict[str, Any]):
        return resolve_and_dispatch(
            layer=LayerLevel.L5, sub_vertical=SubVertical.electrochemistry,
            domain=Domain(payload.get("domain", "pv")), op="lcoe",
            payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.electrochemistry, layer=LayerLevel.L5,
                tool="PySAM-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "quantities": {
                        "lcoe_p05": {"value": 0.034, "unit": "USD/kWh"},
                        "lcoe_p50": {"value": 0.041, "unit": "USD/kWh"},
                        "lcoe_p95": {"value": 0.052, "unit": "USD/kWh"},
                    },
                },
            ),
        )

    # ------------------------------------------------------------------
    # Fusion endpoints — boundary intent gate first
    # ------------------------------------------------------------------

    @app.post("/v1/fusion/l1/transport")
    def fu_l1(payload: dict[str, Any]):
        fusion_intent_or_403(payload)
        return resolve_and_dispatch(
            layer=LayerLevel.L1, sub_vertical=SubVertical.fusion,
            domain=Domain.fusion, op="transport", payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.fusion, layer=LayerLevel.L1,
                tool="OpenMC-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "library_version": "ENDF/B-VIII.1",
                    "quantities": {
                        "tally_keff": {"value": 0.0, "unit": "1"},
                        "tally_relative_error": {"value": 0.05, "unit": "1"},
                    },
                },
            ),
        )

    @app.post("/v1/fusion/l2/gyrokinetic")
    def fu_l2(payload: dict[str, Any]):
        fusion_intent_or_403(payload)
        return resolve_and_dispatch(
            layer=LayerLevel.L2, sub_vertical=SubVertical.fusion,
            domain=Domain.fusion, op="gyrokinetic", payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.fusion, layer=LayerLevel.L2,
                tool="GACODE-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "tglf_cgyro_disagreement_pct": 22.0,
                    "quantities": {
                        "Q_GB_ion": {"value": 1.4, "unit": "1"},
                        "Q_GB_electron": {"value": 0.9, "unit": "1"},
                    },
                },
            ),
        )

    @app.post("/v1/fusion/l3/equilibrium")
    def fu_l3(payload: dict[str, Any]):
        fusion_intent_or_403(payload)
        return resolve_and_dispatch(
            layer=LayerLevel.L3, sub_vertical=SubVertical.fusion,
            domain=Domain.fusion, op="equilibrium", payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.fusion, layer=LayerLevel.L3,
                tool="FreeGS4E-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "topology": "diverted",
                    "x_points": [{"R": 1.6, "Z": -1.1}],
                    "quantities": {
                        "psi_axis": {"value": -0.5, "unit": "Wb"},
                        "psi_boundary": {"value": 0.0, "unit": "Wb"},
                        "q95": {"value": 3.6, "unit": "1"},
                    },
                },
            ),
        )

    @app.post("/v1/fusion/l4/scenario")
    def fu_l4(payload: dict[str, Any]):
        fusion_intent_or_403(payload)

        def _local_cpu(p: dict[str, Any]) -> UniversalLayerEnvelope:
            from energy_pipeline.adapters.fusion.l4 import (
                ReducedTransportCpuAdapter,
                TokamakScenarioSpec,
            )

            spec_dict = p.get("spec", {}) if isinstance(p.get("spec"), dict) else {}
            kwargs = {k: v for k, v in spec_dict.items() if k in TokamakScenarioSpec.__dataclass_fields__}
            spec_obj = TokamakScenarioSpec(**kwargs) if kwargs else TokamakScenarioSpec()
            env, _dro = ReducedTransportCpuAdapter().run(spec_obj)
            return env

        return resolve_and_dispatch(
            layer=LayerLevel.L4, sub_vertical=SubVertical.fusion,
            domain=Domain.fusion, op="scenario", runpod_op="scenario", payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.fusion, layer=LayerLevel.L4,
                tool="IMAS-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "ids_paths_used": ["equilibrium", "core_profiles", "summary"],
                    "imas_ids": {
                        "data_dictionary_version": "3.41.0",
                        "equilibrium": {"time": [0.0, 0.1]},
                    },
                    "quantities": {
                        "power_balance_residual_pct": {"value": 8.0, "unit": "%"},
                    },
                },
            ),
            local_cpu_runner=_local_cpu,
        )

    @app.post("/v1/fusion/l5/neutronics")
    def fu_l5(payload: dict[str, Any]):
        fusion_intent_or_403(payload)
        return resolve_and_dispatch(
            layer=LayerLevel.L5, sub_vertical=SubVertical.fusion,
            domain=Domain.fusion, op="neutronics", payload=payload,
            stub_runner=_stub_for(
                sub_vertical=SubVertical.fusion, layer=LayerLevel.L5,
                tool="OpenMC-Paramak-stub", tool_version="0.0.1",
                payload_out_factory=lambda p: {
                    "tbr_dimensionless_research_only": 1.13,
                    "quantities": {
                        "particle_balance_residual": {"value": 1e-4, "unit": "1"},
                        "tally_relative_error": {"value": 0.07, "unit": "1"},
                    },
                },
            ),
        )

    # Runpod cutover surface. Forwards to ENERGY_RUNPOD_BASE_URL when set, else
    # returns a structured failure envelope (audited) for callers to inspect.
    @app.post("/v1/runpod/{layer}/{domain}/{op}")
    @app.post("/v1/runpod/{layer}/{domain}")
    def runpod_dispatch(
        layer: str,
        domain: str,
        payload: dict[str, Any],
        op: str = "default",
    ) -> Any:
        from energy_pipeline.adapters.shared.runpod_dispatch import RunpodRestAdapter

        cfg = get_config()
        try:
            sv = SubVertical(payload.get("sub_vertical", "electrochemistry"))
        except ValueError:
            sv = SubVertical.electrochemistry
        try:
            lv = LayerLevel(layer if layer.startswith("L") else f"L{layer}")
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"unknown layer: {layer}"},
            )
        try:
            dom = Domain(domain)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": f"unknown domain: {domain}"},
            )

        # Pre-flight fusion intent gate even on dispatch
        if sv == SubVertical.fusion:
            intent_blob = " ".join([
                str(payload.get("intent", "")),
                str(payload.get("description", "")),
                str(payload.get("notes", "")),
                str(payload.get("spec", {}).get("intent", "") if isinstance(payload.get("spec"), dict) else ""),
            ])
            hit = check_fusion_intent(intent_blob)
            if hit:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"runpod fusion request blocked by boundary: matched forbidden intent "
                        f"'{hit}'. Reframe to allowed research scope."
                    ),
                )

        env = RunpodRestAdapter().dispatch(
            layer=lv,
            domain=dom,
            sub_vertical=sv,
            op=op,
            spec=payload.get("spec", {}) if isinstance(payload.get("spec"), dict) else payload,
            campaign_id=str(payload.get("campaign_id", "runpod-dispatch")),
        )
        # Run through the production gate so audit/KG sees this and the strict
        # gate refuses unconfigured / failed dispatches.
        try:
            gated = accept_envelope(env, write_audit=cfg.audit_required, write_kg=cfg.audit_required)
        except Exception as e:  # noqa: BLE001 — surface as 503 with audited body
            return JSONResponse(
                status_code=503,
                content={
                    "error": "runpod dispatch refused by strict gate",
                    "detail": str(e)[:300],
                    "envelope": env.model_dump(mode="json"),
                },
            )
        # On unconfigured / dispatch-error fall back to 503 so clients can branch.
        if gated.falsification.gate_status.value in ("fail", "quarantine"):
            return JSONResponse(status_code=503, content=gated.model_dump(mode="json"))
        return gated.model_dump(mode="json")

    return app


app = create_app()

"""Same-shape backend resolver — Wave 4 §1.

Public layer endpoints (e.g. `/v1/electrochem/l4/pybamm`) must honor
`ENERGY_L?_BACKEND` without forcing clients to switch to `/v1/runpod/...`.

The resolver:
  * reads `EnergyConfig.l<n>_backend` for the requested layer
  * dispatches through one of:
      - `local_cpu_runner` (real adapter; emits a typed envelope/DRO)
      - `stub_runner`     (the existing canned-stub envelope)
      - `runpod_rest`     (forwards through `RunpodRestAdapter`; structured 503
                          envelope when unconfigured)
  * routes the result through `accept_envelope` so audit/KG and the
    production falsifier set apply uniformly.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from energy_physics_pipeline.adapters.shared.runpod_dispatch import RunpodRestAdapter
from energy_physics_pipeline.l6.config import get_config
from energy_physics_pipeline.l6.enforcement import EnvelopeRejected, accept_envelope
from energy_physics_pipeline.schemas import (
    Domain,
    LayerLevel,
    SubVertical,
    UniversalLayerEnvelope,
)


LocalCpuRunner = Callable[[dict[str, Any]], UniversalLayerEnvelope]
StubRunner = Callable[[dict[str, Any]], UniversalLayerEnvelope]


def _layer_backend(cfg, layer: LayerLevel) -> str:
    return {
        LayerLevel.L1: cfg.l1_backend,
        LayerLevel.L2: cfg.l2_backend,
        LayerLevel.L3: cfg.l3_backend,
        LayerLevel.L4: cfg.l4_backend,
        LayerLevel.L5: cfg.l5_backend,
        LayerLevel.L6: cfg.l6_backend,
    }[layer]


def resolve_and_dispatch(
    *,
    layer: LayerLevel,
    sub_vertical: SubVertical,
    domain: Domain,
    op: str,
    payload: dict[str, Any],
    stub_runner: StubRunner,
    local_cpu_runner: Optional[LocalCpuRunner] = None,
    runpod_op: Optional[str] = None,
    write_audit: bool = True,
    write_kg: bool = True,
) -> Any:
    """Run the configured backend for `layer`, route through `accept_envelope`,
    and return either the validated envelope dump (200) or a JSONResponse with
    a structured 503 body.

    `local_cpu_runner` is optional: when None and backend == 'local_cpu', we
    fall back to `stub_runner` (the same canned envelope path the REST stubs
    have always served). This keeps existing endpoints functional during the
    progressive wiring of real CPU adapters.
    """
    cfg = get_config()
    chosen = _layer_backend(cfg, layer)
    runpod_op = runpod_op or op

    if chosen == "runpod_rest":
        adapter = RunpodRestAdapter()
        env = adapter.dispatch(
            layer=layer,
            domain=domain,
            sub_vertical=sub_vertical,
            op=runpod_op,
            spec=payload.get("spec", payload) if isinstance(payload, dict) else {},
            campaign_id=str(payload.get("campaign_id", "rest-resolved")),
        )
    elif chosen == "local_cpu" and local_cpu_runner is not None:
        env = local_cpu_runner(payload)
    else:
        # 'stub', 'gpu_rest_stub', or 'local_cpu' without a wired adapter yet
        env = stub_runner(payload)

    try:
        gated = accept_envelope(env, write_audit=write_audit, write_kg=write_kg)
    except EnvelopeRejected as e:
        # Strict-gate refusal: surface as 503 with the envelope's structured body.
        return JSONResponse(
            status_code=503,
            content={
                "error": "envelope refused by strict gate",
                "detail": str(e)[:300],
                "envelope": env.model_dump(mode="json"),
            },
        )

    # If the resolved backend is runpod_rest but no upstream is configured (or any
    # other fail), surface 503 so the client sees the failure in the same shape.
    if gated.falsification.gate_status.value in ("fail", "quarantine"):
        return JSONResponse(status_code=503, content=gated.model_dump(mode="json"))

    return gated.model_dump(mode="json")


def fusion_intent_blob(payload: dict[str, Any]) -> str:
    """Helper: collapse fusion-relevant input fields into one string for
    the boundary intent gate."""
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
    return " ".join(
        [
            str(payload.get("intent", "")),
            str(payload.get("description", "")),
            str(payload.get("notes", "")),
            str(spec.get("intent", "") if isinstance(spec, dict) else ""),
            str(payload.get("ids_path", "")),
        ]
    )


def fusion_intent_or_403(payload: dict[str, Any]) -> None:
    """Pre-flight fusion intent gate; raises HTTPException(403) on forbidden."""
    from energy_physics_pipeline.boundary import check_fusion_intent

    blob = fusion_intent_blob(payload)
    hit = check_fusion_intent(blob)
    if hit:
        raise HTTPException(
            status_code=403,
            detail=(
                f"fusion request blocked by boundary: matched forbidden intent "
                f"'{hit}'. Reframe to allowed research scope (blanket / "
                f"breeding-blanket / equilibrium / disruption)."
            ),
        )

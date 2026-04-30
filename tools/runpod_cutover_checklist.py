"""Generate a Runpod cutover checklist from the current pipeline state.

Reads the L6 config + adapter registry; for each layer flagged for Runpod cutover,
produces a checklist row with the upstream adapter, REST endpoint, license class, and
expected falsifier IDs.
"""
from __future__ import annotations

import sys
from pathlib import Path

from energy_pipeline.l6 import default_registry, get_config
from energy_pipeline.l6.registry import AdapterCapability


PARKED = {
    "CGYRO nonlinear",
    "GyroSwin training + large inference",
    "MACE/eSEN large MD + fine-tune",
    "JOREK / BOUT++ full nonlinear MHD",
    "PF-PINO training",
    "Reasoning agent (70B) inference",
    "Large OpenMC GPU transport",
    "OpenMC R2S full activation",
    "Large GW spectra (GPAW)",
}


def main() -> int:
    cfg = get_config()
    reg = default_registry()
    print("# Runpod Cutover Checklist")
    print()
    print(f"Current execution profile: `{cfg.execution_profile}`")
    print()
    print("Per-layer current backend:")
    for k in ("l1", "l2", "l3", "l4", "l5", "l6"):
        print(f"- {k.upper()}: `{getattr(cfg, k+'_backend')}`")
    print(f"- Fusion GyroSwin: `{cfg.fusion_gyroswin_backend}`")
    print(f"- Reasoner: `{cfg.reasoner_backend}`")
    print()
    print("## Adapters with Runpod-eligible capability")
    print()
    print("| Adapter | Tool | Layer | Sub-vertical | License | Capabilities |")
    print("|---|---|---|---|---|---|")
    for r in reg.all():
        runpod_eligible = (
            AdapterCapability.gpu_rest_stub in r.capabilities
            or AdapterCapability.runpod_rest in r.capabilities
        )
        if not runpod_eligible:
            continue
        caps = ",".join(c.value for c in r.capabilities)
        print(f"| {r.adapter_id} | {r.tool} {r.tool_version} | {r.layer.value} | {r.sub_vertical.value} | {r.license_class.value} | {caps} |")
    print()
    print("## Cutover order recommendation")
    print()
    print("1. **L4 PyBaMM Runpod** — drop-in replacement for CPU PyBaMM only if a Runpod cluster is needed for cycle-life sweeps. Optional; CPU path works.")
    print("2. **L2 GACODE/CGYRO** — replace `gpu_rest_stub` -> `runpod_rest` for nonlinear gyrokinetic sweeps. The TGLF reduced lane stays CPU.")
    print("3. **L2 GyroSwin** — calibration with cross-machine MAPE/Spearman/ECE acceptance gate. Training + large inference is Runpod-only.")
    print("4. **Reasoner backend** — `local_stub` -> `runpod_vllm` for DeepSeek-R1-Distill-Llama-70B serving. Used by IMAS-MCP-driven reasoning pipelines.")
    print("5. **L1 GPAW GW** / **L5 OpenMC GPU** — largest HPC swings; defer until L2 + L4 are stable.")
    print()
    print("## Cutover gates (PRD §Cutover gates)")
    print()
    print("- Same schemas as stubs.")
    print("- Golden fixture passes before AND after backend swap (`output_hash` invariant).")
    print("- Only provenance/runtime fields may change.")
    print("- Budget cap and kill switch configured.")
    print("- Artifact checksums recorded.")
    print("- No Class C/D/E licensed tool enters product path without `kg://license-grant/...` evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

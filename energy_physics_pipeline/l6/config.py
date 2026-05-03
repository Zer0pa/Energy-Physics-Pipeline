"""ENERGY_* environment config — single source of truth for backend selection.

Reading happens once at import; mutations require explicit `reload()`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ExecutionProfile = Literal["local_cpu_first", "runpod_first", "hybrid"]
ArtifactMode = Literal["manifest_only", "full_local", "remote_objstore"]
LayerBackend = Literal["stub", "local_cpu", "gpu_rest_stub", "runpod_rest", "runpod_orchestrator", "stub_fmi", "runpod_batch"]
ReasonerBackend = Literal["hosted_claude", "runpod_vllm", "local_stub"]
GyroSwinBackend = Literal["stub", "runpod_rest"]


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _get_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class EnergyConfig:
    execution_profile: ExecutionProfile = "local_cpu_first"
    artifact_mode: ArtifactMode = "manifest_only"
    allow_bulk_data: bool = False
    audit_required: bool = True
    boundary_gate: Literal["strict", "warn", "off"] = "strict"

    l1_backend: LayerBackend = "local_cpu"
    l2_backend: LayerBackend = "stub"
    l3_backend: LayerBackend = "stub"
    l4_backend: LayerBackend = "local_cpu"
    l5_backend: LayerBackend = "local_cpu"
    l6_backend: LayerBackend = "local_cpu"

    fusion_gyroswin_backend: GyroSwinBackend = "stub"
    reasoner_backend: ReasonerBackend = "local_stub"

    dro_schema_version: str = "energy.dro.v0.1"
    envelope_schema_version: str = "energy.envelope.v0.1"

    # Runpod cutover knobs. When `runpod_base_url` is set, the REST app's
    # `/v1/runpod/{layer}/{domain}` proxies to the upstream; otherwise it
    # returns a structured error envelope (audited).
    runpod_base_url: str = ""
    runpod_request_timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> "EnergyConfig":
        return cls(
            execution_profile=_get("ENERGY_EXECUTION_PROFILE", "local_cpu_first"),  # type: ignore[arg-type]
            artifact_mode=_get("ENERGY_ARTIFACT_MODE", "manifest_only"),  # type: ignore[arg-type]
            allow_bulk_data=_get_bool("ENERGY_ALLOW_BULK_DATA", False),
            audit_required=_get_bool("ENERGY_AUDIT_REQUIRED", True),
            boundary_gate=_get("ENERGY_BOUNDARY_GATE", "strict"),  # type: ignore[arg-type]
            l1_backend=_get("ENERGY_L1_BACKEND", "local_cpu"),  # type: ignore[arg-type]
            l2_backend=_get("ENERGY_L2_BACKEND", "stub"),  # type: ignore[arg-type]
            l3_backend=_get("ENERGY_L3_BACKEND", "stub"),  # type: ignore[arg-type]
            l4_backend=_get("ENERGY_L4_BACKEND", "local_cpu"),  # type: ignore[arg-type]
            l5_backend=_get("ENERGY_L5_BACKEND", "local_cpu"),  # type: ignore[arg-type]
            l6_backend=_get("ENERGY_L6_BACKEND", "local_cpu"),  # type: ignore[arg-type]
            fusion_gyroswin_backend=_get("ENERGY_FUSION_GYROSWIN_BACKEND", "stub"),  # type: ignore[arg-type]
            reasoner_backend=_get("ENERGY_REASONER_BACKEND", "local_stub"),  # type: ignore[arg-type]
            dro_schema_version=_get("ENERGY_DRO_SCHEMA_VERSION", "energy.dro.v0.1"),
            envelope_schema_version=_get("ENERGY_ENVELOPE_SCHEMA_VERSION", "energy.envelope.v0.1"),
            runpod_base_url=_get("ENERGY_RUNPOD_BASE_URL", ""),
            runpod_request_timeout_s=float(os.environ.get("ENERGY_RUNPOD_TIMEOUT_S", "30") or "30"),
        )


_GLOBAL: EnergyConfig | None = None


def get_config() -> EnergyConfig:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = EnergyConfig.from_env()
    return _GLOBAL


def reload() -> EnergyConfig:
    global _GLOBAL
    _GLOBAL = EnergyConfig.from_env()
    return _GLOBAL

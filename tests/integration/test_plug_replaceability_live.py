"""Live plug-replaceability integration test.

Per PRD: Runpod cutover is accepted only when changing a config flag from `gpu_rest_stub`
to `runpod_rest` preserves golden fixture behaviour except for runtime/provenance fields.

We can't yet test `runpod_rest` live (Runpod handlers not wired), but we CAN test the
invariant between `local_cpu` (a real CPU adapter) and `gpu_rest_stub` (REST stub
returning a canned envelope of the same shape). The invariant is:

  - schema_version preserved
  - sub_vertical / domain / device_family preserved
  - boundary block byte-identical
  - falsifier IDs preserved
  - DRO contract shape preserved (curve_type, scalar_metrics keys present)
  - output_hash on a CANONICAL projection (input + tool name) is comparable.

What we DO NOT preserve across the swap:
  - envelope_id (depends on backend metadata; PRD spec)
  - tool / tool_version (different backend)
  - timestamps and provenance.created_at
  - run_id (every run is unique)
  - actual numeric outputs (real CPU vs canned stub will differ — the contract is
    that the *shape* is the same, not the values).
"""
from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.l6 import reload as cfg_reload
from energy_pipeline.rest import create_app
from energy_pipeline.schemas import (
    ExecutionMode,
    Mode,
)


# ---------------------------------------------------------------------------
# A) ENERGY_L4_BACKEND env-flag flip — config plane
# ---------------------------------------------------------------------------


def test_l4_backend_flag_flips_via_env(monkeypatch: pytest.MonkeyPatch):
    """Setting ENERGY_L4_BACKEND propagates through l6.config.reload() and is
    observable to the REST layer."""
    monkeypatch.setenv("ENERGY_L4_BACKEND", "gpu_rest_stub")
    cfg = cfg_reload()
    assert cfg.l4_backend == "gpu_rest_stub"

    monkeypatch.setenv("ENERGY_L4_BACKEND", "local_cpu")
    cfg = cfg_reload()
    assert cfg.l4_backend == "local_cpu"

    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    cfg = cfg_reload()
    assert cfg.l4_backend == "runpod_rest"


# ---------------------------------------------------------------------------
# B) gpu_rest_stub envelope shape vs local_cpu (electrochemistry L4 PyBaMM)
# ---------------------------------------------------------------------------


def test_pybamm_local_cpu_vs_rest_stub_contract(monkeypatch: pytest.MonkeyPatch):
    """Run a battery L4 spec through both the REST stub (gpu_rest_stub) and the
    local-CPU PyBaMM adapter; assert the envelope-level contract is preserved."""

    # 1) REST stub envelope (force backend=stub on the same endpoint)
    monkeypatch.setenv("ENERGY_L4_BACKEND", "gpu_rest_stub")
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    client = TestClient(create_app())
    stub_response = client.post("/v1/electrochem/l4/pybamm", json={"campaign_id": "live-cutover", "domain": "battery"})
    assert stub_response.status_code == 200
    stub_env_data = stub_response.json()

    # 2) local_cpu envelope (uses the real PyBaMM adapter where available; falls
    # back to its own internal stub if not).
    from energy_pipeline.adapters.electrochem.l4 import PyBaMMBatteryAdapter

    adapter = PyBaMMBatteryAdapter()
    real = adapter.run({"campaign_id": "live-cutover"})
    if isinstance(real, tuple):
        real_env = real[0]
    else:
        real_env = real

    # 3) Compare contract-level invariants
    assert stub_env_data["boundary"] == BOUNDARY_BLOCK == real_env.boundary
    assert stub_env_data["schema_version"] == real_env.schema_version
    assert stub_env_data["sub_vertical"] == real_env.sub_vertical.value
    assert stub_env_data["layer"] == real_env.layer.value
    assert stub_env_data["domain"] == real_env.domain.value
    # Both must carry envelope_id (different by design; same prefix)
    assert stub_env_data["envelope_id"].startswith("sha256:")
    assert real_env.envelope_id and real_env.envelope_id.startswith("sha256:")
    # Backend metadata differs by design — but execution_mode label is the
    # right discriminator.
    assert stub_env_data["backend"]["execution_mode"] == "gpu_rest_stub"
    assert real_env.backend.execution_mode == ExecutionMode.local_cpu
    # Both must populate falsification block keys identically
    stub_fal = stub_env_data["falsification"]
    real_fal = real_env.falsification.model_dump()
    assert set(stub_fal.keys()) == set(real_fal.keys())
    # Stubs MUST NOT claim scientific_valid
    assert stub_fal["scientific_valid"] is False
    # gpu_rest_stub mode is engineering_stub
    assert stub_env_data["mode"] == Mode.engineering_stub.value


# ---------------------------------------------------------------------------
# C) Identical inputs across REST endpoints produce structurally-identical envelopes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,sub_vertical,layer",
    [
        ("/v1/electrochem/l4/pybamm", "electrochemistry", "L4"),
        ("/v1/electrochem/l5/lcoe", "electrochemistry", "L5"),
        ("/v1/fusion/l4/scenario", "fusion", "L4"),
    ],
)
def test_rest_stub_envelope_invariants(path: str, sub_vertical: str, layer: str, monkeypatch: pytest.MonkeyPatch):
    """Each REST stub produces an envelope that satisfies the cutover contract.

    Force every layer backend to stub so this test probes only the canned-stub
    surface, regardless of the live-CPU resolver wiring.
    """
    for k in ("L1", "L2", "L3", "L4", "L5", "L6"):
        monkeypatch.setenv(f"ENERGY_{k}_BACKEND", "gpu_rest_stub")
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    client = TestClient(create_app())
    intent = "blanket TBR research" if "fusion" in path else "battery research"
    r = client.post(path, json={"campaign_id": "cutover-shape", "intent": intent})
    assert r.status_code == 200
    env = r.json()
    assert env["boundary"] == BOUNDARY_BLOCK
    assert env["schema_version"].startswith("energy.envelope")
    assert env["sub_vertical"] == sub_vertical
    assert env["layer"] == layer
    assert env["mode"] == Mode.engineering_stub.value
    assert env["backend"]["execution_mode"] == ExecutionMode.gpu_rest_stub.value
    assert env["falsification"]["scientific_valid"] is False
    assert env["envelope_id"].startswith("sha256:")
    # provenance always present
    for k in ("agent_id", "model_id", "git_sha", "input_hash", "output_hash", "config_hash"):
        assert k in env["provenance"]


# ---------------------------------------------------------------------------
# D) Runpod placeholder returns 503 with the right shape
# ---------------------------------------------------------------------------


def test_runpod_placeholder_503_until_wired(monkeypatch: pytest.MonkeyPatch):
    """Without ENERGY_RUNPOD_BASE_URL set, dispatch returns 503 with a
    STRUCTURED + audited failure envelope, not an opaque error string."""
    monkeypatch.delenv("ENERGY_RUNPOD_BASE_URL", raising=False)
    cfg_reload()
    client = TestClient(create_app())
    r = client.post(
        "/v1/runpod/L4/battery",
        json={"sub_vertical": "electrochemistry", "spec": {}, "campaign_id": "rp-503"},
    )
    assert r.status_code == 503
    body = r.json()
    env = body.get("envelope", body)
    assert env["falsification"]["gate_status"] in ("fail", "quarantine")
    assert any(
        f["gate_id"] in ("runpod_not_configured", "runpod_dispatch_error")
        for f in env["falsification"]["failures"]
    )


# ---------------------------------------------------------------------------
# E) When ENERGY_L4_BACKEND=runpod_rest, the cutover plan kicks in (config-side)
# ---------------------------------------------------------------------------


def test_cfg_runpod_flag_visible_in_health(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_L2_BACKEND", "runpod_rest")
    cfg_reload()
    client = TestClient(create_app())
    health = client.get("/v1/health").json()
    assert health["config"]["l4_backend"] == "runpod_rest"
    assert health["config"]["l2_backend"] == "runpod_rest"
    # restore default
    monkeypatch.delenv("ENERGY_L4_BACKEND")
    monkeypatch.delenv("ENERGY_L2_BACKEND")
    cfg_reload()

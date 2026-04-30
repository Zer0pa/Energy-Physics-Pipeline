"""Live Runpod dispatch + golden-fixture invariance.

Per CPU hardening brief §1: a fake Runpod handler in tests must prove schema parity
and golden fixture invariance across local_cpu / gpu_rest_stub / runpod_rest.

Test surface:
  - dispatch with no `ENERGY_RUNPOD_BASE_URL` -> structured failure envelope
  - dispatch with a configured fake (via `httpx.MockTransport`) -> identical
    canonical output projection compared to the local-CPU adapter
  - the runpod-side envelope is forced to declare `execution_mode=runpod_rest`
    even if the upstream forgot to set it
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from energy_pipeline.adapters.shared.runpod_dispatch import RunpodRestAdapter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.l6 import reload as cfg_reload
from energy_pipeline.schemas import (
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    SubVertical,
)
from energy_pipeline.schemas.canonical import sha256_of


def _canonical_outputs_projection(env_dump: dict[str, Any]) -> str:
    """Drop fields that are expected to differ across paths (provenance, ids,
    timestamps, run-specific metadata) and return a sha256 over the rest."""
    proj = {
        "schema_version": env_dump["schema_version"],
        "boundary": env_dump["boundary"],
        "sub_vertical": env_dump["sub_vertical"],
        "layer": env_dump["layer"],
        "domain": env_dump["domain"],
        "outputs": env_dump["outputs"],
        "uncertainty": env_dump["uncertainty"],
        # falsifier IDs are part of contract; gate_status may differ across paths
        "falsifier_gate_ids": sorted({
            f["gate_id"] for f in env_dump["falsification"].get("failures", [])
        }),
    }
    return sha256_of(proj)


# ---------------------------------------------------------------------------
# A) Unconfigured dispatch returns a structured failure envelope
# ---------------------------------------------------------------------------


def test_dispatch_unconfigured_returns_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ENERGY_RUNPOD_BASE_URL", raising=False)
    cfg_reload()
    env = RunpodRestAdapter().dispatch(
        layer=LayerLevel.L4,
        domain=Domain.battery,
        sub_vertical=SubVertical.electrochemistry,
        op="pybamm",
        spec={"campaign_id": "rp-unc"},
        campaign_id="rp-unc",
    )
    assert env.boundary == BOUNDARY_BLOCK
    assert env.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "runpod_not_configured" for f in env.falsification.failures)
    assert env.backend.execution_mode == ExecutionMode.runpod_rest


# ---------------------------------------------------------------------------
# B) Configured dispatch through MockTransport returns the upstream envelope
#    AND forces execution_mode=runpod_rest on the response
# ---------------------------------------------------------------------------


def _golden_envelope_from_local_cpu() -> dict[str, Any]:
    """Run the real local-CPU PyBaMM adapter on a frozen spec and return its
    envelope dump. Used as the golden fixture for the runpod-parity test.
    """
    pytest.importorskip("pybamm")
    from energy_pipeline.adapters.electrochem.l4 import PyBaMMBatteryAdapter

    adapter = PyBaMMBatteryAdapter()
    out = adapter.run({"campaign_id": "rp-golden"})
    env, _dro = out if isinstance(out, tuple) else (out, None)
    return env.model_dump(mode="json")


def test_dispatch_through_mock_transport_returns_runpod_envelope(monkeypatch: pytest.MonkeyPatch):
    """A fake Runpod backend (via MockTransport) returns a copy of the local-CPU
    envelope. Dispatch must accept it, force `execution_mode=runpod_rest`, and
    preserve the canonical output projection.
    """
    golden = _golden_envelope_from_local_cpu()
    # Strip the production ENVELOPE_ID and run-specific metadata; the runpod side
    # will compute its own envelope_id when finalize() runs.
    golden_for_upstream = {k: v for k, v in golden.items() if k != "envelope_id"}
    # Mark the upstream as having come from a different backend so the dispatcher
    # has work to do (force execution_mode=runpod_rest).
    golden_for_upstream["backend"] = {
        **golden_for_upstream["backend"],
        "execution_mode": "local_cpu",  # upstream "forgot" — dispatcher must overwrite
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/runpod/L4/battery/pybamm"
        return httpx.Response(200, json=golden_for_upstream)

    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    cfg_reload()
    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)

    runpod_env = RunpodRestAdapter(http_client=client).dispatch(
        layer=LayerLevel.L4,
        domain=Domain.battery,
        sub_vertical=SubVertical.electrochemistry,
        op="pybamm",
        spec={"campaign_id": "rp-parity"},
        campaign_id="rp-parity",
    )

    # 1. Boundary preserved
    assert runpod_env.boundary == BOUNDARY_BLOCK
    # 2. execution_mode forced to runpod_rest by dispatcher
    assert runpod_env.backend.execution_mode == ExecutionMode.runpod_rest
    # 3. Canonical output projection matches between local-CPU and runpod paths.
    runpod_dump = runpod_env.model_dump(mode="json")
    assert _canonical_outputs_projection(golden) == _canonical_outputs_projection(runpod_dump)


# ---------------------------------------------------------------------------
# C) Upstream returns malformed JSON -> structured failure (not a raise)
# ---------------------------------------------------------------------------


def test_dispatch_handles_malformed_upstream(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    cfg_reload()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"this is not JSON")

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
    env = RunpodRestAdapter(http_client=client).dispatch(
        layer=LayerLevel.L4,
        domain=Domain.battery,
        sub_vertical=SubVertical.electrochemistry,
        op="pybamm",
        spec={},
    )
    assert env.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "runpod_dispatch_error" for f in env.falsification.failures)


# ---------------------------------------------------------------------------
# D) Upstream returns 5xx -> structured failure
# ---------------------------------------------------------------------------


def test_dispatch_handles_upstream_5xx(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    cfg_reload()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream busy"})

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
    env = RunpodRestAdapter(http_client=client).dispatch(
        layer=LayerLevel.L4,
        domain=Domain.battery,
        sub_vertical=SubVertical.electrochemistry,
        op="pybamm",
        spec={},
    )
    assert env.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "runpod_dispatch_error" for f in env.falsification.failures)


# ---------------------------------------------------------------------------
# E) Upstream returns boundary-mutated envelope -> structured failure
# ---------------------------------------------------------------------------


def test_dispatch_rejects_boundary_drift(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    cfg_reload()

    # Build an envelope with a bad boundary string.
    bad = _golden_envelope_from_local_cpu()
    bad.pop("envelope_id", None)
    bad["boundary"] = BOUNDARY_BLOCK + " (extra)"  # mutation

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bad)

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
    env = RunpodRestAdapter(http_client=client).dispatch(
        layer=LayerLevel.L4,
        domain=Domain.battery,
        sub_vertical=SubVertical.electrochemistry,
        op="pybamm",
        spec={},
    )
    assert env.falsification.gate_status == GateStatus.fail
    # We accept either gate_id depending on whether Pydantic validation or our
    # boundary post-check fires first.
    assert any(
        f.gate_id in ("runpod_envelope_invalid", "runpod_boundary_drift")
        for f in env.falsification.failures
    )

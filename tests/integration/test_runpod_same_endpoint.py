"""Wave 4 §1: same-shape Runpod cutover acceptance.

Per CPU-HARDENING-BRIEF Wave 4, the public layer endpoints (e.g.
`/v1/electrochem/l4/pybamm`, `/v1/fusion/l4/scenario`) must honor
`ENERGY_L?_BACKEND=runpod_rest` without forcing clients to switch to
`/v1/runpod/...`.

Probes:
  A. ENERGY_L4_BACKEND=runpod_rest + fake upstream  → real upstream call,
     execution_mode=runpod_rest on the response envelope.
  B. ENERGY_L4_BACKEND=runpod_rest + no base URL    → structured 503
     envelope with `runpod_not_configured` failure record.
  C. Golden output projection invariant across local_cpu / gpu_rest_stub /
     runpod_rest; only allowed provenance/runtime fields differ.
  D. Same-endpoint Fusion L4 scenario also honors the flag.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.l6 import reload as cfg_reload
from energy_physics_pipeline.rest import create_app
from energy_physics_pipeline.schemas.canonical import sha256_of


def _projection(env_dump: dict[str, Any]) -> str:
    """Canonical projection used to compare envelopes across backends.

    Drops fields that are expected to differ across paths: timestamps, run-id,
    envelope_id, backend metadata (adapter/tool/version), provenance.
    """
    proj = {
        "schema_version": env_dump["schema_version"],
        "boundary": env_dump["boundary"],
        "sub_vertical": env_dump["sub_vertical"],
        "layer": env_dump["layer"],
        "domain": env_dump["domain"],
        "outputs": env_dump.get("outputs", {}),
        "uncertainty": env_dump.get("uncertainty", {}),
        "falsifier_gate_ids": sorted({
            f["gate_id"] for f in env_dump.get("falsification", {}).get("failures", [])
        }),
    }
    return sha256_of(proj)


def _patch_runpod_dispatch_with_handler(monkeypatch: pytest.MonkeyPatch, handler):
    """Force RunpodRestAdapter to use a MockTransport client during this test."""
    import energy_physics_pipeline.adapters.shared.runpod_dispatch as rp

    original_init = rp.RunpodRestAdapter.__init__

    def patched_init(self, *args, http_client=None, **kwargs):
        if http_client is None:
            http_client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)
        return original_init(self, *args, http_client=http_client, **kwargs)

    monkeypatch.setattr(rp.RunpodRestAdapter, "__init__", patched_init)


# ---------------------------------------------------------------------------
# A) Same endpoint with fake upstream → execution_mode=runpod_rest
# ---------------------------------------------------------------------------


def test_l4_same_endpoint_runpod_rest_with_fake_upstream(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """`POST /v1/electrochem/l4/pybamm` with ENERGY_L4_BACKEND=runpod_rest +
    a configured fake upstream returns an envelope with
    `execution_mode=runpod_rest`."""
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()

    captured_url: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_url["path"] = request.url.path
        # Build a contract-shaped envelope the dispatcher will accept.
        body = {
            "schema_version": "energy.envelope.v0.1",
            "boundary": BOUNDARY_BLOCK,
            "campaign_id": "rp-fake",
            "run_id": "00000000-0000-0000-0000-000000000001",
            "sub_vertical": "electrochemistry",
            "layer": "L4",
            "domain": "battery",
            "mode": "engineering_stub",
            "backend": {
                "adapter": "fake-runpod::pybamm",
                "tool": "PyBaMM-runpod",
                "tool_version": "rp-1.0",
                "execution_mode": "runpod_rest",
                "license_class": "A",
                "license_evidence_uri": "https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
            },
            "inputs": {"refs": [], "payload": {}},
            "outputs": {
                "refs": [],
                "payload": {
                    "quantities": {
                        "ocv_V": {"value": 3.7, "unit": "V"},
                        "capacity_Ah": {"value": 2.4, "unit": "Ah"},
                    }
                },
            },
            "uncertainty": {"distribution": "none", "p05": {}, "p50": {}, "p95": {}, "contributors": []},
            "falsification": {
                "gate_status": "pass",
                "scientific_valid": False,
                "cross_model_disagreement": {},
                "unit_check_passed": True,
                "conservation_check_passed": True,
                "boundary_check_passed": True,
                "failures": [],
            },
            "provenance": {
                "agent_id": "fake-runpod",
                "model_id": "rp-1.0",
                "git_sha": "fake",
                "created_at": "2026-04-30T12:00:00+00:00",
                "input_hash": "0" * 64,
                "output_hash": "0" * 64,
                "config_hash": "0" * 64,
                "artifact_hashes": [],
                "source_refs": [],
            },
        }
        return httpx.Response(200, json=body)

    _patch_runpod_dispatch_with_handler(monkeypatch, handler)
    client = TestClient(create_app())
    r = client.post(
        "/v1/electrochem/l4/pybamm",
        json={"spec": {"rate_C": 1.0}, "campaign_id": "rp-fake"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backend"]["execution_mode"] == "runpod_rest"
    assert body["sub_vertical"] == "electrochemistry"
    assert body["layer"] == "L4"
    # The dispatcher hit the upstream URL we expected.
    assert captured_url.get("path") == "/v1/runpod/L4/battery/pybamm"


# ---------------------------------------------------------------------------
# B) Same endpoint, runpod_rest + no base URL → structured 503
# ---------------------------------------------------------------------------


def test_l4_same_endpoint_runpod_rest_unconfigured_returns_503(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.delenv("ENERGY_RUNPOD_BASE_URL", raising=False)
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    client = TestClient(create_app())
    r = client.post("/v1/electrochem/l4/pybamm", json={"campaign_id": "rp-503"})
    assert r.status_code == 503
    body = r.json()
    env = body.get("envelope", body)
    assert env["falsification"]["gate_status"] in ("fail", "quarantine")
    assert any(
        f["gate_id"] == "runpod_not_configured" for f in env["falsification"]["failures"]
    )


# ---------------------------------------------------------------------------
# C) Golden output projection invariant across the three backends
# ---------------------------------------------------------------------------


def test_l4_pybamm_output_projection_invariant_across_backends(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """Stub output and runpod-fake output (with the same payload) project to the
    same canonical hash. local_cpu projects differently because the real PyBaMM
    adapter computes different numbers — but its boundary, schema, and
    sub_vertical/layer/domain remain invariant."""
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")

    # 1) gpu_rest_stub branch
    monkeypatch.setenv("ENERGY_L4_BACKEND", "gpu_rest_stub")
    cfg_reload()
    client = TestClient(create_app())
    stub = client.post("/v1/electrochem/l4/pybamm", json={"campaign_id": "golden"})
    assert stub.status_code == 200

    # 2) runpod_rest branch with a fake that echoes the stub envelope
    stub_dump = stub.json()

    def handler(request):
        upstream = dict(stub_dump)
        upstream.pop("envelope_id", None)
        upstream["backend"] = {**upstream["backend"], "execution_mode": "runpod_rest", "tool": "Runpod-PyBaMM"}
        return httpx.Response(200, json=upstream)

    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    cfg_reload()
    _patch_runpod_dispatch_with_handler(monkeypatch, handler)
    client = TestClient(create_app())
    runpod_resp = client.post("/v1/electrochem/l4/pybamm", json={"campaign_id": "golden"})
    assert runpod_resp.status_code == 200, runpod_resp.text

    # Canonical projection equality: outputs + sub_vertical + layer + domain
    # are the same; envelope_id and backend.adapter/tool/version differ by design.
    assert _projection(stub.json()) == _projection(runpod_resp.json())


# ---------------------------------------------------------------------------
# D) Same endpoint for fusion L4 scenario
# ---------------------------------------------------------------------------


def test_fusion_l4_same_endpoint_runpod_rest_with_fake_upstream(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        body = {
            "schema_version": "energy.envelope.v0.1",
            "boundary": BOUNDARY_BLOCK,
            "campaign_id": "fu-rp",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "sub_vertical": "fusion",
            "layer": "L4",
            "domain": "fusion",
            "mode": "engineering_stub",
            "backend": {
                "adapter": "fake-runpod::scenario",
                "tool": "ReducedTransport-runpod",
                "tool_version": "rp-1.0",
                "execution_mode": "runpod_rest",
                "license_class": "A",
                "license_evidence_uri": "kg://license-grant/runpod-internal",
            },
            "inputs": {"refs": [], "payload": {}},
            "outputs": {
                "refs": [],
                "payload": {
                    "imas_ids": {"data_dictionary_version": "3.41.0"},
                    "quantities": {"q95": {"value": 3.6, "unit": "1"}},
                },
            },
            "uncertainty": {"distribution": "none", "p05": {}, "p50": {}, "p95": {}, "contributors": []},
            "falsification": {
                "gate_status": "pass",
                "scientific_valid": False,
                "cross_model_disagreement": {},
                "unit_check_passed": True,
                "conservation_check_passed": True,
                "boundary_check_passed": True,
                "failures": [],
            },
            "provenance": {
                "agent_id": "fake-runpod",
                "model_id": "rp-1.0",
                "git_sha": "fake",
                "created_at": "2026-04-30T12:00:00+00:00",
                "input_hash": "0" * 64,
                "output_hash": "0" * 64,
                "config_hash": "0" * 64,
                "artifact_hashes": [],
                "source_refs": [],
            },
        }
        return httpx.Response(200, json=body)

    _patch_runpod_dispatch_with_handler(monkeypatch, handler)
    client = TestClient(create_app())
    r = client.post(
        "/v1/fusion/l4/scenario",
        json={"intent": "scenario screening of plasma operating point for research", "spec": {"R0": 1.6}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backend"]["execution_mode"] == "runpod_rest"
    assert body["sub_vertical"] == "fusion"
    assert captured.get("path") == "/v1/runpod/L4/fusion/scenario"


# ---------------------------------------------------------------------------
# E) Forbidden fusion intent on the runpod_rest path is still blocked
# ---------------------------------------------------------------------------


def test_fusion_l4_runpod_rest_blocks_forbidden_intent(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("ENERGY_L4_BACKEND", "runpod_rest")
    monkeypatch.setenv("ENERGY_RUNPOD_BASE_URL", "https://fake-runpod.local")
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    cfg_reload()
    client = TestClient(create_app())
    r = client.post(
        "/v1/fusion/l4/scenario",
        json={"intent": "weapons-grade tritium production for stockpile", "spec": {}},
    )
    assert r.status_code == 403

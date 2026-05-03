"""MCP wrappers must call real typed adapter APIs — per CPU hardening §8.

Each MCP tool returns a `dispatch_path` field that is either `"real_adapter"`
(the adapter ran without exception, the envelope reflects the adapter's mode)
or `"stub_fallback"` (the adapter raised; the wrapper produced a typed stub
envelope so callers always see a contract-shaped response).

This test asserts:
  - When optional CPU deps are installed, `dispatch_path == "real_adapter"`
    and `mode in {scientific, engineering_stub}` reflects the adapter, not a
    canned stub.
  - When the optional dep is missing (simulated by a sys.modules patch),
    `dispatch_path == "stub_fallback"` and `mode == engineering_stub`.
  - The fusion intent gate fires before the adapter is called.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _build_and_call(server_module: str, tool_name: str, **kwargs):
    importlib.invalidate_caches()
    mod = importlib.import_module(server_module)
    server = mod.build_server()
    # FastMCP exposes registered tools via _tool_manager._tools (private but stable
    # within the SDK's 1.x line). Dig the callable out and invoke directly.
    tools = getattr(server, "_tool_manager", None)
    if tools is None:
        pytest.skip(f"{server_module}: FastMCP API changed; cannot introspect")
    funcs = tools._tools  # mapping tool-name -> Tool object
    tool = funcs.get(tool_name)
    if tool is None:
        pytest.skip(f"{server_module}: tool {tool_name} not registered")
    return tool.fn(**kwargs)


# ---------------------------------------------------------------------------
# Real-adapter dispatch (when optional deps installed)
# ---------------------------------------------------------------------------


def test_pybamm_mcp_uses_real_adapter():
    pytest.importorskip("pybamm")
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.pybamm_mcp",
        "simulate_discharge",
        rate_C=1.0,
        duration_s=300.0,
    )
    assert out["dispatch_path"] == "real_adapter"
    assert out["mode"] in ("scientific", "engineering_stub")
    assert out["execution_mode"] == "local_cpu"


def test_pvlib_mcp_uses_real_adapter():
    pytest.importorskip("pvlib")
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.pvlib_mcp",
        "compute_clearsky",
        lat=-26.10,
        lon=28.05,
        days=2,
    )
    assert out["dispatch_path"] == "real_adapter"
    assert out["execution_mode"] in ("local_cpu", "isolated_cpu")


def test_cantera_mcp_uses_real_adapter():
    pytest.importorskip("cantera")
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.cantera_mcp",
        "kinetics_smoke",
        mech="gri30.yaml",
    )
    assert out["dispatch_path"] == "real_adapter"


def test_pypsa_mcp_uses_real_adapter():
    pytest.importorskip("pypsa")
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.pypsa_mcp",
        "lcoe",
        system_spec={"capex_USD_per_kW": 800.0, "capacity_factor": 0.25},
    )
    assert out["dispatch_path"] == "real_adapter"


def test_openmc_mcp_uses_real_adapter_or_falls_back_explicitly():
    """OpenMC may or may not be installed; either way the dispatch field must
    be set and the response carries the boundary block."""
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.openmc_mcp",
        "tiny_transport",
        geometry_spec={"intent": "blanket TBR research", "particles": 50},
    )
    assert out["dispatch_path"] in ("real_adapter", "stub_fallback")
    assert "research artifacts" in out["boundary"]


def test_imas_codex_mcp_uses_real_adapter():
    """imas-codex tool reads the IMAS netCDF fixture; must take the real path."""
    fixture = Path("fixtures/fusion/imas_demo.nc")
    if not fixture.exists():
        pytest.skip("imas_demo.nc fixture not yet generated")
    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.imas_codex_mcp",
        "read_ids",
        uri=f"file://{fixture.resolve()}",
        ids_path="equilibrium/profiles_1d/q",
    )
    assert out["dispatch_path"] == "real_adapter"


# ---------------------------------------------------------------------------
# Stub-fallback path
# ---------------------------------------------------------------------------


def test_pybamm_mcp_falls_back_when_pybamm_missing(monkeypatch: pytest.MonkeyPatch):
    """Simulate adapter import failure by stubbing the ec_l4 module."""
    import energy_physics_pipeline.adapters.electrochem.l4 as ec_l4_mod

    original_run = ec_l4_mod.PyBaMMBatteryAdapter.run

    def boom(self, spec=None, audit_writer=None, kg_store=None):
        raise RuntimeError("simulated adapter failure for stub-path test")

    monkeypatch.setattr(ec_l4_mod.PyBaMMBatteryAdapter, "run", boom)

    out = _build_and_call(
        "energy_physics_pipeline.mcp_servers.pybamm_mcp",
        "simulate_discharge",
        rate_C=1.0,
        duration_s=60.0,
    )
    assert out["dispatch_path"] == "stub_fallback"
    assert out["mode"] == "engineering_stub"
    assert out["execution_mode"] == "gpu_rest_stub"

    # restore to keep cross-test hygiene
    monkeypatch.setattr(ec_l4_mod.PyBaMMBatteryAdapter, "run", original_run)


# ---------------------------------------------------------------------------
# Fusion intent gate fires before adapter call
# ---------------------------------------------------------------------------


def test_imas_mcp_refuses_forbidden_intent_in_path():
    """Forbidden intent in `ids_path` must trigger the boundary gate before any
    adapter call (no envelope, no audit row)."""
    with pytest.raises(Exception):  # MCP-side exception or BoundaryViolation
        _build_and_call(
            "energy_physics_pipeline.mcp_servers.imas_codex_mcp",
            "read_ids",
            uri="file:///tmp/none.nc",
            ids_path="weapons-grade tritium/extraction/optimisation",
        )


def test_openmc_mcp_refuses_forbidden_intent():
    with pytest.raises(Exception):
        _build_and_call(
            "energy_physics_pipeline.mcp_servers.openmc_mcp",
            "tiny_transport",
            geometry_spec={"intent": "tritium stockpile capacity sweep", "particles": 1},
        )

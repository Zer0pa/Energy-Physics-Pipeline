"""MCP server smoke tests.

Exercises every server in-process (no subprocess spawning).
Each test:
  - Calls build_server() to get a FastMCP instance.
  - Lists tools via mcp.list_tools() and verifies boundary block is present.
  - Calls one tool via mcp.call_tool() and verifies the envelope shape.
  - Verifies at least one audit row was written.

Runtime: < 30 s. No process spawning.

call_tool() returns list[ContentBlock]. Each ContentBlock.text is a JSON string.
We parse it via _call(mcp, tool, kwargs) -> dict.
"""
from __future__ import annotations

import asyncio
import importlib
import json

import pytest

from energy_pipeline.audit.writer import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.mcp_servers.registry import get_server, list_servers

# FastMCP wraps any tool exception (including McpError) as ToolError.
from mcp.server.fastmcp.exceptions import ToolError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_loop_run(coro):
    """Run a coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _import_build_server(module_path: str):
    mod = importlib.import_module(module_path)
    return mod.build_server


def _count_audit_rows() -> int:
    w = AuditWriter()
    n = w.count()
    w.close()
    return n


def _build_and_list(server_name: str):
    """Build a server and return (mcp_instance, tools_list)."""
    info = get_server(server_name)
    build_fn = _import_build_server(info["module"])
    mcp = build_fn()
    tools = _new_loop_run(mcp.list_tools())
    return mcp, tools


def _call(mcp, tool_name: str, kwargs: dict) -> dict:
    """Call a tool and return the parsed dict result."""
    contents = _new_loop_run(mcp.call_tool(tool_name, kwargs))
    # call_tool returns list[ContentBlock]; each .text is JSON.
    text = contents[0].text if isinstance(contents, list) else str(contents)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_registry_completeness():
    """All 9 servers are registered."""
    servers = list_servers()
    names = {s["name"] for s in servers}
    expected = {
        "pybamm_mcp", "pvlib_mcp", "solcore_mcp", "cantera_mcp",
        "pypsa_mcp", "pysam_mcp", "openmc_mcp", "imas_codex_mcp", "aiida_mcp",
    }
    assert expected.issubset(names), f"Missing servers: {expected - names}"


def test_registry_fields():
    """Every server record has required fields."""
    for s in list_servers():
        assert "tools" in s, f"{s['name']} missing tools"
        assert "license_class" in s, f"{s['name']} missing license_class"
        assert "mode" in s, f"{s['name']} missing mode"
        assert "boundary_check_required" in s, f"{s['name']} missing boundary_check_required"
        assert s["boundary_check_required"] is True, f"{s['name']} must require boundary check"
        assert s["mode"] == "read-only", f"{s['name']} must default to read-only"


# ---------------------------------------------------------------------------
# Boundary block in all tool descriptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "server_name",
    [
        "pybamm_mcp", "pvlib_mcp", "solcore_mcp", "cantera_mcp",
        "pypsa_mcp", "pysam_mcp", "openmc_mcp", "imas_codex_mcp", "aiida_mcp",
    ],
)
def test_boundary_block_in_tool_descriptions(server_name: str):
    """Every tool description must embed the BOUNDARY_BLOCK string verbatim."""
    _, tools = _build_and_list(server_name)
    assert tools, f"{server_name} has no tools"
    for tool in tools:
        desc = tool.description or ""
        assert BOUNDARY_BLOCK in desc, (
            f"{server_name}.{tool.name}: BOUNDARY_BLOCK missing from description"
        )


# ---------------------------------------------------------------------------
# pybamm_mcp — simulate_discharge
# ---------------------------------------------------------------------------


def test_pybamm_simulate_discharge_envelope_shape():
    """pybamm_mcp: simulate_discharge returns a valid envelope shape."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("pybamm_mcp")
    result = _call(mcp, "simulate_discharge", {"rate_C": 1.0, "duration_s": 3600.0})

    assert "envelope_id" in result, "missing envelope_id"
    assert "boundary" in result, "missing boundary"
    assert result["boundary"] == BOUNDARY_BLOCK, "boundary mismatch"
    assert "dro_summary" in result, "missing dro_summary"
    assert result["sub_vertical"] == "electrochemistry"
    assert result["domain"] == "battery"
    assert result["layer"] == "L4"

    after = _count_audit_rows()
    assert after > before, "No audit row written for pybamm simulate_discharge"


# ---------------------------------------------------------------------------
# pvlib_mcp — compute_clearsky
# ---------------------------------------------------------------------------


def test_pvlib_compute_clearsky():
    """pvlib_mcp: compute_clearsky returns irradiance summary with envelope."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("pvlib_mcp")
    result = _call(mcp, "compute_clearsky", {"lat": 37.7, "lon": -122.4, "days": 7})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "irradiance_summary" in result
    assert result["sub_vertical"] == "electrochemistry"
    assert result["domain"] == "pv"

    after = _count_audit_rows()
    assert after > before


# ---------------------------------------------------------------------------
# solcore_mcp — iv_curve
# ---------------------------------------------------------------------------


def test_solcore_iv_curve():
    """solcore_mcp: iv_curve returns IV summary."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("solcore_mcp")
    result = _call(mcp, "iv_curve", {"material": "GaAs", "irradiance_W_m2": 1000.0})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "iv_summary" in result
    assert result["domain"] == "pv"

    after = _count_audit_rows()
    assert after > before


# ---------------------------------------------------------------------------
# cantera_mcp — kinetics_smoke
# ---------------------------------------------------------------------------


def test_cantera_kinetics_smoke():
    """cantera_mcp: kinetics_smoke returns kinetics summary."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("cantera_mcp")
    result = _call(mcp, "kinetics_smoke", {"mech": "gri30.yaml"})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "kinetics_summary" in result
    assert result["domain"] == "sofc"

    after = _count_audit_rows()
    assert after > before


# ---------------------------------------------------------------------------
# pypsa_mcp — lcoe
# ---------------------------------------------------------------------------


def test_pypsa_lcoe():
    """pypsa_mcp: lcoe returns LCOE result."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("pypsa_mcp")
    spec = {"capex_USD_per_kW": 1200.0, "capacity_factor": 0.25,
            "lifetime_years": 25, "discount_rate": 0.07}
    result = _call(mcp, "lcoe", {"system_spec": spec})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "lcoe_result" in result
    assert "lcoe_USD_per_kWh" in result["lcoe_result"]

    after = _count_audit_rows()
    assert after > before


# ---------------------------------------------------------------------------
# pysam_mcp — lcoe_with_uncertainty
# ---------------------------------------------------------------------------


def test_pysam_lcoe_with_uncertainty():
    """pysam_mcp: lcoe_with_uncertainty returns P5/P50/P95."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("pysam_mcp")
    result = _call(mcp, "lcoe_with_uncertainty", {"system_spec": {"system_capacity_kW": 100}})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    p = result["lcoe_percentiles"]
    assert "lcoe_p05_USD_per_kWh" in p
    assert "lcoe_p50_USD_per_kWh" in p
    assert "lcoe_p95_USD_per_kWh" in p
    assert p["lcoe_p05_USD_per_kWh"] <= p["lcoe_p50_USD_per_kWh"] <= p["lcoe_p95_USD_per_kWh"]

    after = _count_audit_rows()
    assert after > before


# ---------------------------------------------------------------------------
# openmc_mcp — tiny_transport
# ---------------------------------------------------------------------------


def test_openmc_tiny_transport():
    """openmc_mcp: tiny_transport returns tally summary."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("openmc_mcp")
    geom = {"material": "iron", "thickness_cm": 10.0, "source_energy_MeV": 14.1}
    result = _call(mcp, "tiny_transport", {"geometry_spec": geom})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "transport_summary" in result
    assert result["sub_vertical"] == "fusion"
    assert result["domain"] == "fusion"

    after = _count_audit_rows()
    assert after > before


def test_openmc_fusion_gate_blocks_forbidden_intent():
    """openmc_mcp: tiny_transport MUST refuse 'weapons-grade tritium' input."""
    mcp, _ = _build_and_list("openmc_mcp")
    evil_spec = {
        "material": "tritium",
        "intent": "weapons-grade tritium extraction optimization",
        "thickness_cm": 5.0,
    }
    with pytest.raises(ToolError) as exc_info:
        _call(mcp, "tiny_transport", {"geometry_spec": evil_spec})

    msg = str(exc_info.value)
    assert "boundary blocked" in msg.lower(), (
        f"Expected 'boundary blocked' in error message, got: {msg}"
    )


# ---------------------------------------------------------------------------
# imas_codex_mcp — read_ids (read-only)
# ---------------------------------------------------------------------------


def test_imas_codex_read_ids():
    """imas_codex_mcp: read_ids returns IDS result."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("imas_codex_mcp")
    result = _call(mcp, "read_ids", {
        "uri": "file:///fixtures/imas_scenario.nc",
        "ids_path": "equilibrium/time_slice/0/global_quantities/ip",
    })

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    assert "ids_result" in result
    assert result["sub_vertical"] == "fusion"

    after = _count_audit_rows()
    assert after > before


def test_imas_codex_read_ids_blocks_forbidden_intent():
    """imas_codex_mcp: read_ids MUST refuse when ids_path contains 'weapons-grade tritium'."""
    mcp, _ = _build_and_list("imas_codex_mcp")
    with pytest.raises(ToolError) as exc_info:
        _call(mcp, "read_ids", {
            "uri": "imas://shot/99999",
            "ids_path": "weapons-grade tritium extraction profile",
        })

    msg = str(exc_info.value)
    assert "boundary blocked" in msg.lower(), (
        f"Expected 'boundary blocked' in error message, got: {msg}"
    )


def test_imas_codex_has_no_mutation_tool():
    """imas_codex_mcp: must NOT expose any write/mutation tool."""
    _, tools = _build_and_list("imas_codex_mcp")
    tool_names = [t.name for t in tools]
    mutation_suspects = [n for n in tool_names if any(
        kw in n.lower()
        for kw in ["write", "put", "post", "create", "update", "delete", "submit", "mutate"]
    )]
    assert not mutation_suspects, (
        f"imas_codex_mcp must not expose mutation tools; found: {mutation_suspects}"
    )


# ---------------------------------------------------------------------------
# aiida_mcp — submit_dryrun
# ---------------------------------------------------------------------------


def test_aiida_submit_dryrun():
    """aiida_mcp: submit_dryrun returns a deterministic workflow_id placeholder."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list("aiida_mcp")
    wf = {"plugin": "quantumespresso.pw", "computer": "localhost", "code": "pw-6.8"}
    result = _call(mcp, "submit_dryrun", {"workflow": wf})

    assert "envelope_id" in result
    assert result["boundary"] == BOUNDARY_BLOCK
    r = result["workflow_result"]
    assert "workflow_id" in r
    assert r["workflow_id"].startswith("aiida-dryrun-")
    assert r["submitted"] is False

    after = _count_audit_rows()
    assert after > before


def test_aiida_submit_dryrun_is_deterministic():
    """aiida_mcp: same workflow spec produces the same workflow_id."""
    mcp, _ = _build_and_list("aiida_mcp")
    wf = {"plugin": "quantumespresso.pw", "computer": "localhost", "code": "pw-6.8"}
    r1 = _call(mcp, "submit_dryrun", {"workflow": wf})
    r2 = _call(mcp, "submit_dryrun", {"workflow": wf})
    assert r1["workflow_result"]["workflow_id"] == r2["workflow_result"]["workflow_id"]


# ---------------------------------------------------------------------------
# Cross-server: every server writes at least one audit row per call
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "server_name,tool_name,kwargs",
    [
        ("pybamm_mcp", "simulate_discharge", {"rate_C": 2.0, "duration_s": 1800.0}),
        ("pvlib_mcp", "compute_clearsky", {"lat": 0.0, "lon": 0.0, "days": 1}),
        ("solcore_mcp", "iv_curve", {"material": "Si", "irradiance_W_m2": 500.0}),
        ("cantera_mcp", "kinetics_smoke", {"mech": "h2o2.yaml"}),
        ("pypsa_mcp", "lcoe", {"system_spec": {}}),
        ("pysam_mcp", "lcoe_with_uncertainty", {"system_spec": {}}),
        ("openmc_mcp", "tiny_transport", {"geometry_spec": {"material": "water"}}),
        ("imas_codex_mcp", "read_ids", {"uri": "file:///dev/null", "ids_path": "equilibrium/ip"}),
        ("aiida_mcp", "submit_dryrun", {"workflow": {"plugin": "test"}}),
    ],
)
def test_each_server_writes_audit_row(server_name: str, tool_name: str, kwargs: dict):
    """Every server must write at least one audit row per tool call."""
    before = _count_audit_rows()
    mcp, _ = _build_and_list(server_name)
    _call(mcp, tool_name, kwargs)
    after = _count_audit_rows()
    assert after > before, f"{server_name}.{tool_name} wrote no audit row"

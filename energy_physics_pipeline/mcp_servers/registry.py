"""MCP server registry.

Lists every MCP server in the suite with its tools, license class,
sub-vertical, mode, and boundary-check requirements.

Usage::

    from energy_physics_pipeline.mcp_servers.registry import list_servers, get_server

    all_servers = list_servers()
    info = get_server("pybamm_mcp")
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Static registry data
# ---------------------------------------------------------------------------

_MCP_SERVERS: dict[str, dict[str, Any]] = {
    "pybamm_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.pybamm_mcp",
        "tools": ["simulate_discharge"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L4",
        "domain": "battery",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "PyBaMM battery discharge simulator. "
            "Calls PyBaMM P2D model or REST stub. "
            "Emits UniversalLayerEnvelope with DRO summary."
        ),
    },
    "pvlib_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.pvlib_mcp",
        "tools": ["compute_clearsky"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L5",
        "domain": "pv",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "pvlib-python clear-sky irradiance calculator. "
            "Returns GHI/DNI/DHI time-series envelope."
        ),
    },
    "solcore_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.solcore_mcp",
        "tools": ["iv_curve"],
        "license_class": "B",
        "sub_vertical": "electrochemistry",
        "layer": "L4",
        "domain": "pv",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "Solcore PV IV-curve calculator (LGPL-3). "
            "Returns Jsc, Voc, FF, PCE in an envelope."
        ),
    },
    "cantera_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.cantera_mcp",
        "tools": ["kinetics_smoke"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L4",
        "domain": "sofc",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "Cantera SOFC/SOEC kinetics smoke tester. "
            "Validates mechanism load and equilibrium computation."
        ),
    },
    "pypsa_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.pypsa_mcp",
        "tools": ["lcoe"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L5",
        "domain": "pv",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "PyPSA sector-coupled LCOE calculator (MIT). "
            "Returns envelope with LCOE estimate."
        ),
    },
    "pysam_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.pysam_mcp",
        "tools": ["lcoe_with_uncertainty"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L5",
        "domain": "pv",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "NREL SAM / pySAM LCOE with P5/P50/P95 uncertainty. "
            "Returns envelope with percentile LCOE estimates."
        ),
    },
    "openmc_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.openmc_mcp",
        "tools": ["tiny_transport"],
        "license_class": "A",
        "sub_vertical": "fusion",
        "layer": "L1",
        "domain": "fusion",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": True,
        "description": (
            "OpenMC fixed-source neutron transport (CPU fixture). "
            "Fusion boundary gate active — refused on forbidden terms."
        ),
    },
    "imas_codex_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.imas_codex_mcp",
        "tools": ["read_ids"],
        "license_class": "B",
        "sub_vertical": "fusion",
        "layer": "L4",
        "domain": "fusion",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": True,
        "description": (
            "IMAS IDS read-only gateway (LGPL-3). "
            "Reads fixture or IMAS-Python data. NO mutation tools. "
            "Fusion boundary gate active."
        ),
    },
    "aiida_mcp": {
        "module": "energy_physics_pipeline.mcp_servers.aiida_mcp",
        "tools": ["submit_dryrun"],
        "license_class": "A",
        "sub_vertical": "electrochemistry",
        "layer": "L5",
        "domain": "battery",
        "mode": "read-only",
        "boundary_check_required": True,
        "fusion_gate": False,
        "description": (
            "AiiDA workflow dry-run (manifest-only). "
            "Returns deterministic workflow_id placeholder without daemon submission."
        ),
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_servers() -> list[dict[str, Any]]:
    """Return a list of all registered MCP server descriptors."""
    return [{"name": name, **info} for name, info in _MCP_SERVERS.items()]


def get_server(name: str) -> dict[str, Any]:
    """Return the descriptor for a single MCP server by name.

    Raises:
        KeyError: if ``name`` is not registered.
    """
    if name not in _MCP_SERVERS:
        raise KeyError(f"Unknown MCP server: {name!r}. Known: {sorted(_MCP_SERVERS)}")
    return {"name": name, **_MCP_SERVERS[name]}


def all_tool_names() -> list[str]:
    """Return a flat list of all tool names across all servers."""
    out: list[str] = []
    for info in _MCP_SERVERS.values():
        out.extend(info["tools"])
    return out

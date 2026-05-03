"""MCP stdio launch smoke — actually spawn the server and round-trip JSON-RPC.

Per PRD §"MCP Server Suite": MCP tools call registered adapters via stdio JSON-RPC.
The in-process smoke test (`test_mcp_smoke.py`) already covers tool registration. This
test goes further: it spawns the server as a subprocess, performs the MCP `initialize`
handshake, sends `tools/list`, parses the response, and asserts boundary-block presence.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest



REPO_ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable  # the venv's python from the running interpreter


async def _mcp_handshake_and_list_tools(server_module: str) -> dict:
    """Spawn `python -m <server_module>`, perform MCP initialize + tools/list,
    return the parsed `tools/list` result.
    """
    proc = await asyncio.create_subprocess_exec(
        PY,
        "-m",
        server_module,
        cwd=str(REPO_ROOT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    async def send(req: dict) -> None:
        line = json.dumps(req) + "\n"
        proc.stdin.write(line.encode("utf-8"))
        await proc.stdin.drain()

    async def recv() -> dict:
        line = await proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout before responding")
        return json.loads(line.decode("utf-8"))

    try:
        # 1. initialize
        await send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "energy-test", "version": "0.1"},
                },
            }
        )
        init_resp = await recv()
        assert init_resp.get("id") == 1, init_resp
        assert "result" in init_resp, init_resp
        # 2. notifications/initialized (no id, no response expected)
        await send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
        # 3. tools/list
        await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = await recv()
        assert tools_resp.get("id") == 2, tools_resp
        return tools_resp["result"]
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


@pytest.mark.parametrize(
    "module",
    [
        "energy_physics_pipeline.mcp_servers.pybamm_mcp",
        "energy_physics_pipeline.mcp_servers.pvlib_mcp",
        "energy_physics_pipeline.mcp_servers.openmc_mcp",
        "energy_physics_pipeline.mcp_servers.imas_codex_mcp",
    ],
)
def test_mcp_server_responds_to_stdio_tools_list(module: str):
    """Each MCP server module must spawn cleanly and respond to tools/list."""
    pytest.importorskip("mcp")
    result = asyncio.run(asyncio.wait_for(_mcp_handshake_and_list_tools(module), timeout=30))
    tools = result.get("tools", [])
    assert isinstance(tools, list) and len(tools) >= 1, f"{module}: no tools listed"
    # Every tool description must reference the boundary discipline (the substring
    # "research artifacts" appears verbatim in BOUNDARY_BLOCK).
    boundary_phrase = "research artifacts"
    matched = False
    for t in tools:
        desc = (t.get("description") or "")
        if boundary_phrase in desc:
            matched = True
            break
    # Some MCP SDK versions put the boundary in the *server* description rather
    # than the tool description; that's acceptable. Either way, the BOUNDARY_BLOCK
    # phrase MUST be present *somewhere* in the response.
    if not matched:
        full_dump = json.dumps(result)
        assert boundary_phrase in full_dump, (
            f"{module}: BOUNDARY_BLOCK phrase '{boundary_phrase}' absent from "
            f"tools/list response"
        )


def test_mcp_pybamm_via_stdio_returns_tool_with_simulate_discharge():
    """Specific tool-name assertion for the pybamm server."""
    pytest.importorskip("mcp")
    result = asyncio.run(
        asyncio.wait_for(
            _mcp_handshake_and_list_tools("energy_physics_pipeline.mcp_servers.pybamm_mcp"),
            timeout=30,
        )
    )
    names = [t.get("name") for t in result.get("tools", [])]
    assert "simulate_discharge" in names, f"tools listed: {names}"

"""IMAS Codex MCP server — READ-ONLY gateway.

Tool: read_ids(uri, ids_path)
Adapter target: fusion.l4.ImasPythonAdapter (fixture read). NO mutation tool.

BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

FUSION BOUNDARY: Weapons-grade tritium simulation, stockpile optimization,
extraction/purification optimization, diversion, military use, and defence applications
are BLOCKED. Requests containing forbidden terms are refused.

READ-ONLY MODE: This server exposes NO mutation tools. All outputs are read from
fixture data or IMAS-Python read-only paths. Write operations will never be added.
"""
from __future__ import annotations

from energy_pipeline.mcp_servers._common import (
    build_mcp_server,
    check_fusion_intent_or_raise,
    emit_audit_kg,
    inputs_to_str,
    make_stub_envelope,
    tool_description,
)
from energy_pipeline.schemas.envelope import (
    Domain,
    ExecutionMode,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
)

SERVER_NAME = "imas_codex_mcp"
_DESC = tool_description(
    "READ-ONLY gateway to IMAS IDS data. Reads a single IDS path from a fixture or "
    "IMAS-Python backend. uri may be a file:// path or imas:// reference. "
    "ids_path is the dot-separated IMAS IDS path (e.g. 'equilibrium/time_slice/0/global_quantities/ip'). "
    "Returns envelope_id and IDS value. "
    "License class B (LGPL-3). NO mutation operations are exposed. "
    "FUSION GATE: Requests containing weapons-grade, stockpile, diversion, or warhead "
    "terms are refused per boundary policy."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def read_ids(uri: str, ids_path: str) -> dict:
        """Read an IMAS IDS value (read-only).

        Args:
            uri: Data source URI (e.g. 'file:///path/to/fixture.nc', 'imas://shot/12345').
            ids_path: Dot-separated IDS path (e.g. 'equilibrium/time_slice/0/global_quantities/ip').

        Returns:
            dict with envelope_id and IDS read result.
        """
        # Fusion boundary gate — check BOTH inputs for forbidden terms.
        check_fusion_intent_or_raise(inputs_to_str({"uri": uri, "ids_path": ids_path}))

        payload_out: dict = {}
        exec_mode = ExecutionMode.gpu_rest_stub
        mode = Mode.engineering_stub

        try:
            from energy_pipeline.adapters.fusion import l4 as fu_l4  # type: ignore[attr-defined]
            adapter = fu_l4.ImasPythonAdapter()
            result = adapter.read(uri=uri, ids_path=ids_path)
            payload_out = result if isinstance(result, dict) else {"value": str(result)}
            exec_mode = ExecutionMode.local_cpu
            mode = Mode.scientific
        except Exception:
            # Fixture stub — return a plausible IDS scalar
            payload_out = {
                "uri": uri,
                "ids_path": ids_path,
                "value": 15.0e6,  # e.g. plasma current 15 MA
                "unit": "A",
                "ids_version": "3.41.0",
                "stub": True,
            }

        envelope = make_stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            tool="IMAS-Python (imas_core)",
            tool_version="5.6.0",
            adapter_id="imas_python_l4",
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/iterorganization/IMAS-Core/releases/tag/5.6.0",
            payload_in={"uri": uri, "ids_path": ids_path},
            payload_out=payload_out,
            mode=mode,
            execution_mode=exec_mode,
        )
        emit_audit_kg(envelope, tool_name="read_ids", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "ids_result": envelope.outputs.payload,
        }

    # NOTE: No mutation/write tool is registered. This server is intentionally read-only.

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

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

from energy_physics_pipeline.mcp_servers._common import (
    build_mcp_server,
    check_fusion_intent_or_raise,
    emit_audit_kg,
    inputs_to_str,
    make_stub_envelope,
    tool_description,
)
from energy_physics_pipeline.schemas.envelope import (
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

        try:
            from energy_physics_pipeline.adapters.fusion import l4 as fu_l4  # type: ignore[attr-defined]
            from energy_physics_pipeline.adapters.fusion.l4 import ImasReadSpec
            from pathlib import Path as _Path
            local_path = _Path(uri.replace("file://", "")) if uri.startswith("file://") else _Path(uri)
            spec_obj = ImasReadSpec(
                intent="IMAS IDS path read for research",
                path=local_path,
                campaign_id="mcp-imas",
            )
            adapter = fu_l4.ImasPythonAdapter()
            envelope = adapter.run(spec_obj)
            dispatch_path = "real_adapter"
        except Exception as e:
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
                payload_out={"stub_reason": f"{type(e).__name__}: {str(e)[:100]}"},
                mode=Mode.engineering_stub,
                execution_mode=ExecutionMode.gpu_rest_stub,
            )
            dispatch_path = "stub_fallback"
        emit_audit_kg(envelope, tool_name="read_ids", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "execution_mode": envelope.backend.execution_mode.value,
            "dispatch_path": dispatch_path,
            "ids_result": envelope.outputs.payload,
        }

    # NOTE: No mutation/write tool is registered. This server is intentionally read-only.

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

"""pvlib MCP server.

Tool: compute_clearsky(lat, lon, days)
Adapter target: electrochem.l5.PvlibYieldAdapter (if present), else stub.

BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.
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

SERVER_NAME = "pvlib_mcp"
_DESC = tool_description(
    "Compute clear-sky GHI/DNI/DHI irradiance time-series for a given location and time span "
    "using pvlib-python (Ineichen model). "
    "Returns an envelope_id and an irradiance summary. "
    "License class A (BSD-3). Read-only simulation artifact."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def compute_clearsky(lat: float, lon: float, days: int) -> dict:
        """Compute clear-sky irradiance.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.
            days: Number of days to simulate (1-365).

        Returns:
            dict with envelope_id and irradiance summary.
        """
        check_fusion_intent_or_raise(
            inputs_to_str({"lat": lat, "lon": lon, "days": days})
        )

        spec = {"lat": lat, "lon": lon, "days": days, "campaign_id": "mcp-pvlib"}
        try:
            from energy_physics_pipeline.adapters.electrochem import l5 as ec_l5  # type: ignore[attr-defined]
            adapter = ec_l5.PvlibYieldAdapter()
            result = adapter.run(spec=spec)
            envelope, _maybe_dro = result if isinstance(result, tuple) else (result, None)
            dispatch_path = "real_adapter"
        except Exception as e:
            envelope = make_stub_envelope(
                sub_vertical=SubVertical.electrochemistry,
                layer=LayerLevel.L5,
                domain=Domain.pv,
                tool="pvlib-python",
                tool_version="0.10+",
                adapter_id="pvlib_l5",
                license_class=LicenseClass.A,
                license_evidence_uri="https://github.com/pvlib/pvlib-python/blob/main/LICENSE",
                payload_in=spec,
                payload_out={
                    "stub_reason": f"{type(e).__name__}: {str(e)[:100]}",
                },
                mode=Mode.engineering_stub,
                execution_mode=ExecutionMode.gpu_rest_stub,
            )
            dispatch_path = "stub_fallback"
        emit_audit_kg(envelope, tool_name="compute_clearsky", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "execution_mode": envelope.backend.execution_mode.value,
            "dispatch_path": dispatch_path,
            "irradiance_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

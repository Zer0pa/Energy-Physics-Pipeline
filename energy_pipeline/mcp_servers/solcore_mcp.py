"""Solcore MCP server.

Tool: iv_curve(material, irradiance_W_m2)
Adapter target: electrochem.l4.SolcorePvAdapter (if present), else stub.

BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.
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

SERVER_NAME = "solcore_mcp"
_DESC = tool_description(
    "Compute an IV curve for a single-junction PV cell using Solcore. "
    "Inputs: semiconductor material string (e.g. 'GaAs') and irradiance in W/m². "
    "Returns envelope_id and IV curve summary (Jsc, Voc, FF, PCE). "
    "License class B (LGPL-3). Read-only simulation artifact."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def iv_curve(material: str, irradiance_W_m2: float) -> dict:
        """Compute IV curve for a PV cell.

        Args:
            material: Semiconductor material string (e.g. 'GaAs', 'Si').
            irradiance_W_m2: Incident irradiance in W/m².

        Returns:
            dict with envelope_id and IV summary metrics.
        """
        check_fusion_intent_or_raise(
            inputs_to_str({"material": material, "irradiance_W_m2": irradiance_W_m2})
        )

        payload_out: dict = {}
        exec_mode = ExecutionMode.gpu_rest_stub
        mode = Mode.engineering_stub

        try:
            from energy_pipeline.adapters.electrochem import l4 as ec_l4  # type: ignore[attr-defined]
            adapter = ec_l4.SolcorePvAdapter()
            result = adapter.run(material=material, irradiance_W_m2=irradiance_W_m2)
            payload_out = result if isinstance(result, dict) else {"result": str(result)}
            exec_mode = ExecutionMode.local_cpu
            mode = Mode.scientific
        except Exception:
            # Stub: simple GaAs-like values scaled by irradiance fraction
            irr_frac = irradiance_W_m2 / 1000.0
            payload_out = {
                "material": material,
                "irradiance_W_m2": irradiance_W_m2,
                "Jsc_mA_cm2": round(29.5 * irr_frac, 3),
                "Voc_V": round(1.03 - 0.02 * (1.0 - irr_frac), 4),
                "FF": 0.85,
                "PCE_pct": round(29.5 * irr_frac * 1.03 * 0.85 / irradiance_W_m2 * 100, 2),
                "stub": True,
            }

        envelope = make_stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domain=Domain.pv,
            tool="Solcore",
            tool_version="6.x",
            adapter_id="solcore_l4",
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/qpv-research-group/solcore5/blob/develop/LICENSE.txt",
            payload_in={"material": material, "irradiance_W_m2": irradiance_W_m2},
            payload_out=payload_out,
            mode=mode,
            execution_mode=exec_mode,
        )
        emit_audit_kg(envelope, tool_name="iv_curve", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "iv_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

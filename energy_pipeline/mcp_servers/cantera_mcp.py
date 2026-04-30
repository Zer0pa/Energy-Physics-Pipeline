"""Cantera MCP server.

Tool: kinetics_smoke(mech)
Adapter target: electrochem.l4.CanteraSofcAdapter (if present), else stub.

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

SERVER_NAME = "cantera_mcp"
_DESC = tool_description(
    "Run a kinetics smoke test using Cantera for a given reaction mechanism file (SOFC/SOEC). "
    "Validates that the mechanism loads, species counts are sane, and equilibrium is computable. "
    "Returns envelope_id and kinetics summary. "
    "License class A (BSD-3). Read-only research artifact."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def kinetics_smoke(mech: str) -> dict:
        """Run a Cantera kinetics smoke test.

        Args:
            mech: Mechanism file name or identifier (e.g. 'gri30.yaml', 'h2o2.yaml').

        Returns:
            dict with envelope_id and kinetics summary.
        """
        check_fusion_intent_or_raise(inputs_to_str({"mech": mech}))

        spec = {"mech": mech, "campaign_id": "mcp-cantera"}
        try:
            from energy_pipeline.adapters.electrochem import l4 as ec_l4  # type: ignore[attr-defined]
            adapter = ec_l4.CanteraSofcAdapter()
            result = adapter.run(spec=spec)
            envelope, _dro = result if isinstance(result, tuple) else (result, None)
            dispatch_path = "real_adapter"
        except Exception as e:
            envelope = make_stub_envelope(
                sub_vertical=SubVertical.electrochemistry,
                layer=LayerLevel.L4,
                domain=Domain.sofc,
                tool="Cantera",
                tool_version="3.2",
                adapter_id="cantera_l4",
                license_class=LicenseClass.A,
                license_evidence_uri="https://github.com/Cantera/cantera/blob/main/License.txt",
                payload_in=spec,
                payload_out={"stub_reason": f"{type(e).__name__}: {str(e)[:100]}"},
                mode=Mode.engineering_stub,
                execution_mode=ExecutionMode.gpu_rest_stub,
            )
            dispatch_path = "stub_fallback"
        emit_audit_kg(envelope, tool_name="kinetics_smoke", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "execution_mode": envelope.backend.execution_mode.value,
            "dispatch_path": dispatch_path,
            "kinetics_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

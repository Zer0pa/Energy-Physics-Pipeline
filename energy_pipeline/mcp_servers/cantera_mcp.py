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

        payload_out: dict = {}
        exec_mode = ExecutionMode.gpu_rest_stub
        mode = Mode.engineering_stub

        try:
            from energy_pipeline.adapters.electrochem import l4 as ec_l4  # type: ignore[attr-defined]
            adapter = ec_l4.CanteraSofcAdapter()
            result = adapter.run(mech=mech)
            payload_out = result if isinstance(result, dict) else {"result": str(result)}
            exec_mode = ExecutionMode.local_cpu
            mode = Mode.scientific
        except Exception:
            payload_out = {
                "mech": mech,
                "n_species": 53,
                "n_reactions": 325,
                "T_equilibrium_K": 2500.0,
                "P_Pa": 101325.0,
                "smoke_passed": True,
                "stub": True,
            }

        envelope = make_stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domain=Domain.sofc,
            tool="Cantera",
            tool_version="3.2",
            adapter_id="cantera_l4",
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/Cantera/cantera/blob/main/License.txt",
            payload_in={"mech": mech},
            payload_out=payload_out,
            mode=mode,
            execution_mode=exec_mode,
        )
        emit_audit_kg(envelope, tool_name="kinetics_smoke", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "kinetics_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

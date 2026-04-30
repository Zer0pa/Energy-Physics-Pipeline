"""OpenMC MCP server (fusion, L1 transport).

Tool: tiny_transport(geometry_spec)
Adapter target: fusion.l1.OpenMcManifestAdapter (if present), else stub.

BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

FUSION BOUNDARY: Weapons-grade tritium simulation, stockpile optimization,
extraction/purification optimization, diversion, military use, and defence applications
are BLOCKED. Requests containing forbidden terms are refused.
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

SERVER_NAME = "openmc_mcp"
_DESC = tool_description(
    "Run a tiny fixed-source neutron transport calculation using OpenMC (CPU fixture mode). "
    "geometry_spec dict may include material, thickness_cm, source_energy_MeV. "
    "Returns envelope_id and tally summary (k-eff, relative error). "
    "License class A (MIT). Read-only research artifact. "
    "FUSION GATE: Requests containing weapons-grade, stockpile, diversion, or warhead "
    "terms are refused per boundary policy."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def tiny_transport(geometry_spec: dict) -> dict:
        """Run a tiny OpenMC neutron transport smoke test.

        Args:
            geometry_spec: Dict specifying geometry/material (e.g. material, thickness_cm).

        Returns:
            dict with envelope_id and transport tally summary.
        """
        # Fusion boundary gate — check ALL input fields.
        check_fusion_intent_or_raise(inputs_to_str(geometry_spec))

        payload_out: dict = {}
        exec_mode = ExecutionMode.gpu_rest_stub
        mode = Mode.engineering_stub

        try:
            from energy_pipeline.adapters.fusion import l1 as fu_l1  # type: ignore[attr-defined]
            adapter = fu_l1.OpenMcManifestAdapter()
            result = adapter.run(geometry_spec=geometry_spec)
            payload_out = result if isinstance(result, dict) else {"result": str(result)}
            exec_mode = ExecutionMode.local_cpu
            mode = Mode.scientific
        except Exception:
            payload_out = {
                "tally_keff": {"value": 0.0, "unit": "1"},
                "tally_relative_error": 0.05,
                "library_version": "ENDF/B-VIII.1",
                "geometry_spec": geometry_spec,
                "stub": True,
            }

        envelope = make_stub_envelope(
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L1,
            domain=Domain.fusion,
            tool="OpenMC",
            tool_version="0.15.3",
            adapter_id="openmc_l1",
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/openmc-dev/openmc/blob/develop/LICENSE",
            payload_in={"geometry_spec": geometry_spec},
            payload_out=payload_out,
            mode=mode,
            execution_mode=exec_mode,
        )
        emit_audit_kg(envelope, tool_name="tiny_transport", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "transport_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

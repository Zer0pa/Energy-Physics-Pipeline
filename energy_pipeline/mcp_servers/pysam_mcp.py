"""PySAM MCP server.

Tool: lcoe_with_uncertainty(system_spec)
Adapter target: electrochem.l5.PySAMLcoeAdapter (if present), else stub.

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

SERVER_NAME = "pysam_mcp"
_DESC = tool_description(
    "Compute LCOE with P5/P50/P95 uncertainty bounds using NREL SAM (pySAM). "
    "system_spec dict may include system_capacity_kW, dc_ac_ratio, inv_eff, losses_pct, "
    "capital_cost_USD, fixed_operating_cost_USD_yr, variable_operating_cost_USD_kWh. "
    "Returns envelope_id and LCOE percentile estimates. "
    "License class A (BSD-3). Read-only research artifact."
)


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def lcoe_with_uncertainty(system_spec: dict) -> dict:
        """Compute LCOE with uncertainty (P5/P50/P95) using PySAM.

        Args:
            system_spec: Dictionary specifying PV system parameters.

        Returns:
            dict with envelope_id and LCOE percentile estimates.
        """
        check_fusion_intent_or_raise(inputs_to_str(system_spec))

        spec = {**system_spec, "campaign_id": "mcp-pysam"}
        try:
            from energy_pipeline.adapters.electrochem import l5 as ec_l5  # type: ignore[attr-defined]
            adapter = ec_l5.PySAMLcoeAdapter()
            result = adapter.run(spec=spec)
            envelope, _dro = result if isinstance(result, tuple) else (result, None)
            dispatch_path = "real_adapter"
        except Exception as e:
            envelope = make_stub_envelope(
                sub_vertical=SubVertical.electrochemistry,
                layer=LayerLevel.L5,
                domain=Domain.pv,
                tool="NREL SAM (pySAM)",
                tool_version="2024",
                adapter_id="pysam_l5",
                license_class=LicenseClass.A,
                license_evidence_uri="https://github.com/NREL/pysam/blob/main/LICENSE",
                payload_in={"system_spec": system_spec},
                payload_out={"stub_reason": f"{type(e).__name__}: {str(e)[:100]}"},
                mode=Mode.engineering_stub,
                execution_mode=ExecutionMode.gpu_rest_stub,
            )
            dispatch_path = "stub_fallback"
        emit_audit_kg(envelope, tool_name="lcoe_with_uncertainty", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "execution_mode": envelope.backend.execution_mode.value,
            "dispatch_path": dispatch_path,
            "lcoe_percentiles": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

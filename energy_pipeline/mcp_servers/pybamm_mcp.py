"""PyBaMM MCP server.

Tool: simulate_discharge(rate_C, duration_s)
Adapter target: electrochem.l4.PyBaMMBatteryAdapter (if present), else REST stub.

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

SERVER_NAME = "pybamm_mcp"
_DESC = tool_description(
    "Simulate a constant-current discharge of a lithium-ion cell using PyBaMM (P2D model). "
    "Returns an envelope_id and a DRO summary with voltage-time curve metadata. "
    "License class A (BSD-3). Read-only simulation artifact."
)


def build_server():  # noqa: ANN201
    """Return a configured FastMCP server for PyBaMM."""
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def simulate_discharge(rate_C: float, duration_s: float) -> dict:
        """Simulate constant-current discharge.

        Args:
            rate_C: C-rate (e.g. 1.0 = 1C discharge).
            duration_s: Simulation duration in seconds.

        Returns:
            dict with envelope_id and DRO summary fields.
        """
        check_fusion_intent_or_raise(inputs_to_str({"rate_C": rate_C, "duration_s": duration_s}))

        # Call the real adapter with its typed spec dict. The adapter's
        # internal `_has_pybamm` flag decides whether the real PyBaMM engine
        # runs (mode=scientific) or the analytic fallback (mode=engineering_stub).
        spec = {
            "rate_C": rate_C,
            "duration_s": duration_s,
            "campaign_id": "mcp-pybamm",
        }
        try:
            from energy_pipeline.adapters.electrochem import l4 as ec_l4  # type: ignore[attr-defined]
            adapter = ec_l4.PyBaMMBatteryAdapter()
            envelope, _dro = adapter.run(spec=spec)
            dispatch_path = "real_adapter"
        except Exception as e:
            # Adapter unavailable entirely — fall back to a typed stub envelope
            # so callers always get a contract-shaped response.
            envelope = make_stub_envelope(
                sub_vertical=SubVertical.electrochemistry,
                layer=LayerLevel.L4,
                domain=Domain.battery,
                tool="PyBaMM",
                tool_version="23.5+",
                adapter_id="pybamm_l4",
                license_class=LicenseClass.A,
                license_evidence_uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
                payload_in=spec,
                payload_out={
                    "stub_reason": f"{type(e).__name__}: {str(e)[:100]}",
                    "rate_C_input": rate_C,
                    "duration_s_input": duration_s,
                },
                mode=Mode.engineering_stub,
                execution_mode=ExecutionMode.gpu_rest_stub,
            )
            dispatch_path = "stub_fallback"

        emit_audit_kg(envelope, tool_name="simulate_discharge", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "execution_mode": envelope.backend.execution_mode.value,
            "dispatch_path": dispatch_path,
            "dro_summary": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

"""AiiDA MCP server.

Tool: submit_dryrun(workflow)
Returns a manifest-only placeholder workflow_id (no actual AiiDA daemon required).

BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.
"""
from __future__ import annotations

import hashlib
import json

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

SERVER_NAME = "aiida_mcp"
_DESC = tool_description(
    "Dry-run an AiiDA workflow: validates the workflow dict, generates a deterministic "
    "workflow_id placeholder, and returns a manifest envelope without submitting to any daemon. "
    "workflow dict may include: plugin, inputs, computer, code. "
    "Returns envelope_id and workflow_id placeholder. "
    "License class A (MIT). Manifest-only — no daemon submission."
)


def _workflow_id(workflow: dict) -> str:
    """Generate a deterministic workflow_id from the workflow spec."""
    blob = json.dumps(workflow, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(blob).hexdigest()[:16]
    return f"aiida-dryrun-{digest}"


def build_server():  # noqa: ANN201
    mcp = build_mcp_server(SERVER_NAME)

    @mcp.tool(description=_DESC)
    def submit_dryrun(workflow: dict) -> dict:
        """Dry-run an AiiDA workflow (manifest only, no daemon submission).

        Args:
            workflow: Dict describing the workflow (plugin, inputs, computer, code).

        Returns:
            dict with envelope_id and workflow_id placeholder.
        """
        check_fusion_intent_or_raise(inputs_to_str(workflow))

        wf_id = _workflow_id(workflow)
        payload_out = {
            "workflow_id": wf_id,
            "status": "dryrun_manifest_only",
            "plugin": workflow.get("plugin", "unknown"),
            "computer": workflow.get("computer", "localhost"),
            "code": workflow.get("code", "unknown"),
            "submitted": False,
            "stub": True,
        }

        envelope = make_stub_envelope(
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L5,
            domain=Domain.battery,
            tool="AiiDA",
            tool_version="2.x",
            adapter_id="aiida_l5_manifest",
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/aiidateam/aiida-core/blob/main/LICENSE.txt",
            payload_in={"workflow": workflow},
            payload_out=payload_out,
            mode=Mode.engineering_stub,
            execution_mode=ExecutionMode.gpu_rest_stub,
        )
        emit_audit_kg(envelope, tool_name="submit_dryrun", server_name=SERVER_NAME)
        return {
            "envelope_id": envelope.envelope_id,
            "boundary": envelope.boundary,
            "sub_vertical": envelope.sub_vertical.value,
            "domain": envelope.domain.value,
            "layer": envelope.layer.value,
            "mode": envelope.mode.value,
            "workflow_result": envelope.outputs.payload,
        }

    return mcp


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_server().run_stdio_async())

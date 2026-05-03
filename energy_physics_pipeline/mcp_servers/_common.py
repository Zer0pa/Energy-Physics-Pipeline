"""Shared utilities for the MCP server suite.

Provides:
- ``build_mcp_server(name)`` — create a named FastMCP instance.
- ``make_stub_envelope(...)`` — wrap an adapter/REST call into a UniversalLayerEnvelope.
- ``emit_audit_kg(envelope, tool_name, server_name)`` — write AuditWriter + KGStore events.
- ``check_fusion_intent_or_raise(inputs_str)`` — refuse blocked terms with MCPError.

Convention: every tool description MUST embed BOUNDARY_BLOCK verbatim.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from energy_physics_pipeline.audit.writer import AuditWriter
from energy_physics_pipeline.boundary import (
    BOUNDARY_BLOCK,
    check_fusion_intent as _check_fusion_intent,
)
from energy_physics_pipeline.kg.graph import KGStore
from energy_physics_pipeline.schemas.envelope import (
    BackendBlock,
    Domain,
    ExecutionMode,
    FalsificationBlock,
    GateStatus,
    IOBlock,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
    UncertaintyBlock,
    UncertaintyDistribution,
)

# Shared singleton writers — one per process, thread-safe internally.
_audit_writer: AuditWriter | None = None
_kg_store: KGStore | None = None


def _get_audit() -> AuditWriter:
    global _audit_writer
    if _audit_writer is None:
        _audit_writer = AuditWriter()
    return _audit_writer


def _get_kg() -> KGStore:
    global _kg_store
    if _kg_store is None:
        _kg_store = KGStore()
    return _kg_store


def build_mcp_server(name: str) -> FastMCP:
    """Return a FastMCP instance configured with the project name."""
    return FastMCP(name=name, instructions=BOUNDARY_BLOCK)


def make_stub_envelope(
    *,
    sub_vertical: SubVertical,
    layer: LayerLevel,
    domain: Domain,
    tool: str,
    tool_version: str,
    adapter_id: str,
    license_class: LicenseClass = LicenseClass.A,
    license_evidence_uri: str = "kg://license-grant/stub",
    payload_in: dict[str, Any],
    payload_out: dict[str, Any],
    mode: Mode = Mode.engineering_stub,
    execution_mode: ExecutionMode = ExecutionMode.gpu_rest_stub,
) -> UniversalLayerEnvelope:
    """Build and finalize a stub UniversalLayerEnvelope for MCP tool calls."""
    env = UniversalLayerEnvelope(
        campaign_id=str(payload_in.get("campaign_id", f"mcp-{tool}")),
        sub_vertical=sub_vertical,
        layer=layer,
        domain=domain,
        mode=mode,
        backend=BackendBlock(
            adapter=adapter_id,
            tool=tool,
            tool_version=tool_version,
            execution_mode=execution_mode,
            license_class=license_class,
            license_evidence_uri=license_evidence_uri,
        ),
        inputs=IOBlock(payload=payload_in),
        outputs=IOBlock(payload=payload_out),
        uncertainty=UncertaintyBlock(distribution=UncertaintyDistribution.none),
        falsification=FalsificationBlock(
            gate_status=GateStatus.warn,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=False,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id=f"mcp-server::{tool}",
            model_id="n/a",
            git_sha="local",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    ).finalize()
    return env


def emit_audit_kg(
    envelope: UniversalLayerEnvelope,
    *,
    tool_name: str,
    server_name: str,
) -> UniversalLayerEnvelope:
    """Wave 4 §2: route MCP outputs through the *central* enforcement path
    (`accept_envelope`) so audit/KG semantics match REST and adapter paths.

    The legacy private `_get_audit()` / `_get_kg()` singletons are still used
    as a fallback when a process-default writer/store cannot be created (rare).
    Returns the gated envelope so callers can surface the production
    falsifier-block to the client.
    """
    from energy_physics_pipeline.l6 import accept_envelope, EnvelopeRejected

    try:
        gated = accept_envelope(envelope)
        return gated
    except EnvelopeRejected:
        # Strict gate refused; surface a structured exception with the
        # envelope state so the MCP layer can return an error to the client.
        raise
    except Exception:
        # Last-resort: write via the local singletons so we never silently
        # drop an MCP-emitted envelope in tests / lab environments.
        audit = _get_audit()
        kg = _get_kg()
        payload = envelope.model_dump(mode="json")
        kind = payload.get("schema_version", "envelope")
        audit.write_event(kind=kind, payload=payload)
        tool_node_id = f"tool-adapter::{server_name}::{tool_name}"
        try:
            kg.add_node(
                kind="ToolAdapter",
                node_id=tool_node_id,
                attrs={
                    "boundary": BOUNDARY_BLOCK,
                    "server_name": server_name,
                    "tool_name": tool_name,
                },
                boundary_required=True,
            )
        except Exception:
            pass
        run_node_id = f"sim-run::{envelope.envelope_id or uuid.uuid4().hex}"
        kg.add_node(
            kind="SimulationRun",
            node_id=run_node_id,
            attrs={
                "boundary": BOUNDARY_BLOCK,
                "envelope_id": str(envelope.envelope_id),
                "tool": envelope.backend.tool,
                "domain": envelope.domain.value,
                "layer": envelope.layer.value,
            },
            boundary_required=True,
        )
        kg.add_edge(kind="USED_TOOL", src=run_node_id, dst=tool_node_id)
        return envelope


def check_fusion_intent_or_raise(inputs_str: str) -> None:
    """Check inputs string for forbidden fusion intents; raise McpError if found."""
    hit = _check_fusion_intent(inputs_str)
    if hit:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"boundary blocked: {hit}",
            )
        )


def tool_description(base: str) -> str:
    """Prepend the boundary block to a tool description."""
    return f"{base}\n\nBOUNDARY: {BOUNDARY_BLOCK}"


def inputs_to_str(inputs: dict[str, Any]) -> str:
    """Serialize tool inputs to a string for intent checking."""
    return json.dumps(inputs, default=str)

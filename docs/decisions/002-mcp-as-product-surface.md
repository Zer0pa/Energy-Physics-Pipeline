# ADR 002 — MCP as Product Surface, Not Authority Surface

**Status:** Accepted  
**Date:** 2026-04-30  
**Authors:** Zer0pa Energy pipeline team

---

## Context

The Model Context Protocol (MCP) is an open standard for connecting AI assistants to data sources and tools (see <https://modelcontextprotocol.io/>). Every MCP server exposes a set of typed tools that a language model can call. The Zer0pa Energy pipeline exposes research simulators — PyBaMM, pvlib, Solcore, Cantera, PyPSA, PySAM, OpenMC, IMAS-Python, AiiDA — as MCP tools.

## Decision

**MCP is a product surface, not an authority surface.**

MCP tools are thin wrappers. They call registered adapters in `energy_pipeline.l6.default_registry()` (or REST stubs when the real adapter is absent), emit the standard `UniversalLayerEnvelope`, and write audit and KG events. They do not make policy decisions, bypass the boundary block, or short-circuit the falsification pipeline.

## Read-Only Default

Every MCP server in this suite is declared `mode: read-only` in `registry.py`. Tools return simulation artifacts — envelopes, DRO summaries, tally results — but do not mutate persistent state, dispatch compute jobs, or write to databases. The only side effects are: one `AuditWriter` event per call (append-only JSONL + DuckDB) and two KG nodes plus one edge per call (append-only JSONL + NetworkX in-memory).

## Mutation Gate

Any future mutation tool (e.g. submitting a real AiiDA workflow, writing back IMAS IDS data) requires:

1. A **signed plan** document describing the mutation, scope, and rollback.
2. An **audit event** of kind `mutation_intent` written before the mutation executes.
3. A `kg://license-grant/...` URI present in the tool input for license-class C/D/E backends.

Tools that do not carry all three are refused at the `make_stub_envelope` layer — the envelope validator will reject the combination.

## Boundary Block Propagation

Every tool description embeds `BOUNDARY_BLOCK` verbatim (via `tool_description()` in `_common.py`). Every tool output carries `envelope.boundary == BOUNDARY_BLOCK`. Fusion tools additionally run `check_fusion_intent_or_raise()` on all string inputs before any computation begins.

## References

- MCP specification: <https://modelcontextprotocol.io/>
- MCP Python SDK: <https://github.com/modelcontextprotocol/python-sdk>
- `energy_pipeline/boundary.py` — `BOUNDARY_BLOCK`, `FUSION_FORBIDDEN_INTENTS`
- `energy_pipeline/mcp_servers/_common.py` — shared utilities
- `energy_pipeline/mcp_servers/registry.py` — server catalogue
- PRD §"MCP Server Suite"

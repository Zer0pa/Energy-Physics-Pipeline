"""MCP server suite for the Zer0pa Energy CPU-first pipeline.

Each sub-module exposes ``build_server() -> FastMCP`` and a ``__main__`` guard.
The registry module lists all servers and their metadata.

MCP as product surface: tools call registered adapters and emit normal artifacts.
Default mode is read-only. Mutation requires a signed plan and audit event.
"""
from energy_physics_pipeline.mcp_servers.registry import get_server, list_servers

__all__ = ["get_server", "list_servers"]

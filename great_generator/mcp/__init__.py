"""Optional MCP support for Great Generator."""

from __future__ import annotations

__all__ = ["create_server", "list_registered_tools"]


def create_server():
    """Create the MCP server when optional MCP dependencies are installed."""

    from great_generator.mcp.server import create_server as _create_server

    return _create_server()


def list_registered_tools() -> list[str]:
    """Return MCP tool names without importing the optional MCP SDK."""

    from great_generator.mcp.server import list_registered_tools as _list_registered_tools

    return _list_registered_tools()

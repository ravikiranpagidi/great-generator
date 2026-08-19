from __future__ import annotations

import pytest

from great_generator.mcp import list_registered_tools
from great_generator.mcp.server import TOOL_SPECS, create_server


def test_server_imports_without_mcp_sdk_installed():
    assert list_registered_tools() == [
        "generate_from_schema",
        "parse_ddl",
        "generate_relational",
        "validate_query_coverage",
        "export_dataset",
    ]


def test_tool_descriptions_are_present():
    descriptions = {tool.name: tool.description for tool in TOOL_SPECS}

    assert descriptions["generate_from_schema"]
    assert descriptions["parse_ddl"]
    assert descriptions["generate_relational"]
    assert descriptions["validate_query_coverage"]
    assert descriptions["export_dataset"]


def test_create_server_when_mcp_sdk_is_available():
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError:
        try:
            from mcp.server.mcpserver import MCPServer  # noqa: F401
        except ImportError:
            pytest.skip("MCP SDK server classes are not installed")

    server = create_server()

    assert type(server).__name__ in {"FastMCP", "MCPServer"}

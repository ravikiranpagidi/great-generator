"""Stdio MCP server for Great Generator."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from great_generator.mcp.tools import (
    export_dataset_tool,
    generate_from_schema_tool,
    generate_relational_tool,
    parse_ddl_tool,
    validate_query_coverage_tool,
)


@dataclass(frozen=True)
class MCPToolSpec:
    """Description of a Great Generator MCP tool."""

    name: str
    description: str
    handler: Callable[..., dict[str, Any]]


def generate_from_schema(
    schema: Any,
    rows: int,
    output_dir: str,
    seed: int | None = None,
    format: str = "csv",
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    overwrite: bool = False,
    preview_rows: int = 5,
    allow_large: bool = False,
) -> dict[str, Any]:
    """Generate synthetic data from a schema and write it to local files."""

    return generate_from_schema_tool(
        schema=schema,
        rows=rows,
        output_dir=output_dir,
        seed=seed,
        format=format,
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        overwrite=overwrite,
        preview_rows=preview_rows,
        allow_large=allow_large,
    )


def parse_ddl(
    ddl: str,
    dialect: str = "ansi",
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    """Parse SQL CREATE TABLE DDL and return a schema contract summary."""

    return parse_ddl_tool(
        ddl=ddl,
        dialect=dialect,
        include_diagnostics=include_diagnostics,
    )


def generate_relational(
    schemas: Mapping[str, Any],
    rows: Mapping[str, int] | int | None,
    output_dir: str,
    relationships: list[str | Mapping[str, str]] | None = None,
    seed: int | None = None,
    format: str = "csv",
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    ensure_join_coverage: bool = False,
    overwrite: bool = False,
    preview_rows: int = 5,
    allow_large: bool = False,
) -> dict[str, Any]:
    """Generate related synthetic tables and write one local file per table."""

    return generate_relational_tool(
        schemas=schemas,
        rows=rows,
        output_dir=output_dir,
        relationships=relationships,
        seed=seed,
        format=format,
        required_values=required_values,
        partition_by=partition_by,
        ensure_join_coverage=ensure_join_coverage,
        overwrite=overwrite,
        preview_rows=preview_rows,
        allow_large=allow_large,
    )


def validate_query_coverage(
    data_path: str,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    relationships: list[str | Mapping[str, str]] | None = None,
    ensure_join_coverage: bool = False,
) -> dict[str, Any]:
    """Validate query-aware coverage for a supported local generated dataset."""

    return validate_query_coverage_tool(
        data_path=data_path,
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        relationships=relationships,
        ensure_join_coverage=ensure_join_coverage,
    )


def export_dataset(
    input_path: str,
    output_dir: str,
    format: str = "csv",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export a supported local generated dataset to another local file format."""

    return export_dataset_tool(
        input_path=input_path,
        output_dir=output_dir,
        format=format,
        overwrite=overwrite,
    )


TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec(
        name="generate_from_schema",
        description=(
            "Generate synthetic data from a schema, write a local CSV, JSONL, or Parquet "
            "file, and return row counts, columns, a small preview, warnings, and a manifest path."
        ),
        handler=generate_from_schema,
    ),
    MCPToolSpec(
        name="parse_ddl",
        description=(
            "Parse documented SQL CREATE TABLE DDL into a Great Generator contract summary. "
            "This tool does not generate data."
        ),
        handler=parse_ddl,
    ),
    MCPToolSpec(
        name="generate_relational",
        description=(
            "Generate related synthetic tables with primary-key and foreign-key behavior, write "
            "one local output file per table, and return summaries and previews."
        ),
        handler=generate_relational,
    ),
    MCPToolSpec(
        name="validate_query_coverage",
        description=(
            "Validate a supported local generated dataset for required values, partition dates, "
            "selectivity targets, and optional join coverage."
        ),
        handler=validate_query_coverage,
    ),
    MCPToolSpec(
        name="export_dataset",
        description=(
            "Export a supported local generated dataset to CSV, JSONL, or Parquet under the "
            "configured allowed root."
        ),
        handler=export_dataset,
    ),
)


def list_registered_tools() -> list[str]:
    """Return the names of MCP tools exposed by this package."""

    return [tool.name for tool in TOOL_SPECS]


def create_server() -> Any:
    """Create and configure the stdio MCP server."""

    server_class = _load_mcp_server_class()
    try:
        server = server_class(
            "great-generator",
            title="Great Generator",
            description="Optional local MCP server for Great Generator synthetic data tools.",
        )
    except TypeError:
        server = server_class("great-generator")
    for tool in TOOL_SPECS:
        server.tool(name=tool.name, description=tool.description)(tool.handler)
    return server


def _load_mcp_server_class() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP

        return FastMCP
    except ImportError:
        pass
    try:
        from mcp.server.mcpserver import MCPServer

        return MCPServer
    except ImportError as exc:
        raise RuntimeError(
            "MCP support requires optional dependencies. Install with: "
            'pip install "great-generator[mcp]"'
        ) from exc


def main() -> int:
    """Run the Great Generator MCP server over stdio."""

    try:
        server = create_server()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        server.run(transport="stdio")
    except TypeError:
        server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

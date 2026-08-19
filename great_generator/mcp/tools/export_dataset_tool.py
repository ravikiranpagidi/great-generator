"""export_dataset MCP tool."""

from __future__ import annotations

from typing import Any

import pandas as pd

from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import resolve_input_path, resolve_output_dir, validate_format
from great_generator.mcp.serializers import (
    dataset_summary,
    json_safe,
    load_dataset_path,
    output_files_for_dataset,
)


def export_dataset_tool(
    input_path: str,
    output_dir: str,
    *,
    format: str = "csv",
    overwrite: bool = False,
    config: MCPConfig | None = None,
) -> dict[str, Any]:
    """Export a supported local generated dataset to another local file format."""

    source_path = resolve_input_path(input_path, config=config)
    out_dir = resolve_output_dir(output_dir, config=config)
    format_name = validate_format(format)
    data = load_dataset_path(source_path)
    output_files = output_files_for_dataset(data, out_dir, format_name, overwrite=overwrite)
    summary = dataset_summary(data)
    row_counts: int | dict[str, int]
    if isinstance(data, pd.DataFrame):
        row_counts = int(len(data))
    else:
        row_counts = {table_name: int(len(frame)) for table_name, frame in data.items()}
    return {
        "status": "ok",
        "tool": "export_dataset",
        "input_path": str(source_path),
        "output_files": [str(path) for path in output_files],
        "format": format_name,
        "row_counts": json_safe(row_counts),
        "schema_summary": json_safe(summary),
        "warnings": [],
    }

"""validate_query_coverage MCP tool."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from great_generator import validate_query_coverage
from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import resolve_input_path
from great_generator.mcp.serializers import json_safe, load_dataset_path


def validate_query_coverage_tool(
    data_path: str,
    *,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    relationships: list[str | Mapping[str, str]] | None = None,
    ensure_join_coverage: bool = False,
    config: MCPConfig | None = None,
) -> dict[str, Any]:
    """Validate query-aware coverage for a supported local dataset path."""

    path = resolve_input_path(data_path, config=config)
    data = load_dataset_path(path)
    report = validate_query_coverage(
        data,
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        relationships=relationships,
        ensure_join_coverage=ensure_join_coverage,
    )
    return {
        "status": "ok",
        "tool": "validate_query_coverage",
        "data_path": str(path),
        "report": json_safe(report),
        "warnings": json_safe(report.get("warnings", [])),
    }

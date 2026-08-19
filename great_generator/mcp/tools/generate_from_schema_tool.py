"""generate_from_schema MCP tool."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from great_generator import generate_from_schema, validate_query_coverage
from great_generator.io.manifest import build_generation_manifest
from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import (
    GreatGeneratorMCPError,
    ensure_can_write,
    output_file_path,
    resolve_output_dir,
    validate_format,
    validate_preview_rows,
    validate_row_count,
)
from great_generator.mcp.serializers import (
    dataframe_preview,
    dataframe_summary,
    json_safe,
    mcp_manifest_payload,
    write_dataframe,
    write_json,
)


def generate_from_schema_tool(
    schema: Any,
    rows: int,
    output_dir: str,
    *,
    seed: int | None = None,
    format: str = "csv",
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    overwrite: bool = False,
    preview_rows: int = 5,
    allow_large: bool = False,
    config: MCPConfig | None = None,
) -> dict[str, Any]:
    """Generate synthetic data from a schema and write it to a local file."""

    if schema is None or schema == "":
        raise GreatGeneratorMCPError("schema is required.")
    row_count = validate_row_count(rows, allow_large=allow_large, config=config)
    preview_count = validate_preview_rows(preview_rows, config=config)
    format_name = validate_format(format)
    out_dir = resolve_output_dir(output_dir, config=config)
    output_path = output_file_path(out_dir, "dataset", format_name, overwrite=overwrite)
    manifest_path = out_dir / "manifest.json"
    ensure_can_write(manifest_path, overwrite=overwrite)

    frame = generate_from_schema(
        schema=schema,
        rows=row_count,
        seed=seed,
        engine="pandas",
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
    )
    write_dataframe(frame, output_path, format_name)

    warnings: list[str] = []
    validation: dict[str, Any] = {}
    coverage_path = None
    if required_values or partition_by or target_selectivity:
        coverage = validate_query_coverage(
            frame,
            required_values=required_values,
            partition_by=partition_by,
            target_selectivity=target_selectivity,
        )
        validation["query_coverage"] = coverage
        coverage_path = out_dir / "query_coverage.json"
        write_json(coverage_path, coverage, overwrite=overwrite)

    schema_summary = dataframe_summary(frame)
    manifest = build_generation_manifest(
        dataset_name="great_generator_mcp_schema_dataset",
        tables={"dataset": frame},
        engine="pandas",
        seed=seed,
        parameters={
            "tool": "generate_from_schema",
            "rows": row_count,
            "format": format_name,
            "required_values": json_safe(required_values or {}),
            "partition_by": json_safe(partition_by or {}),
            "target_selectivity": json_safe(target_selectivity or {}),
        },
        validation=validation,
        warnings=warnings,
        real_data_ingested=False,
    )
    manifest_payload = mcp_manifest_payload(
        manifest,
        tool_name="generate_from_schema",
        output_files=[output_path],
        schema_summary=schema_summary,
        query_coverage_report_path=coverage_path,
    )
    write_json(manifest_path, manifest_payload, overwrite=overwrite)

    return {
        "status": "ok",
        "tool": "generate_from_schema",
        "output_files": [str(output_path)],
        "row_count": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "schema_summary": json_safe(schema_summary),
        "preview": dataframe_preview(frame, preview_count),
        "manifest_path": str(manifest_path),
        "query_coverage_report_path": str(coverage_path) if coverage_path else None,
        "warnings": warnings,
    }

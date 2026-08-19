"""generate_relational MCP tool."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from great_generator import generate_relational, validate_query_coverage
from great_generator.io.manifest import build_generation_manifest
from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import (
    GreatGeneratorMCPError,
    ensure_can_write,
    resolve_output_dir,
    validate_format,
    validate_preview_rows,
    validate_row_count,
    validate_row_mapping,
)
from great_generator.mcp.serializers import (
    dataframe_preview,
    dataset_summary,
    json_safe,
    mcp_manifest_payload,
    output_files_for_dataset,
    write_json,
)


def generate_relational_tool(
    schemas: Mapping[str, Any],
    rows: Mapping[str, int] | int | None,
    output_dir: str,
    *,
    relationships: list[str | Mapping[str, str]] | None = None,
    seed: int | None = None,
    format: str = "csv",
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    ensure_join_coverage: bool = False,
    overwrite: bool = False,
    preview_rows: int = 5,
    allow_large: bool = False,
    config: MCPConfig | None = None,
) -> dict[str, Any]:
    """Generate related synthetic tables and write one local file per table."""

    if not schemas:
        raise GreatGeneratorMCPError("schemas is required and must contain at least one table.")
    preview_count = validate_preview_rows(preview_rows, config=config)
    format_name = validate_format(format)
    out_dir = resolve_output_dir(output_dir, config=config)
    rows_arg = _validate_rows_from_inputs(schemas, rows, allow_large=allow_large, config=config)
    manifest_path = out_dir / "manifest.json"
    ensure_can_write(manifest_path, overwrite=overwrite)

    tables = _tables_from_schemas(schemas, rows_arg)
    data = generate_relational(
        tables=tables,
        relationships=relationships,
        rows=rows_arg if not _tables_define_rows(tables) else None,
        engine="pandas",
        seed=seed,
        required_values=required_values,
        partition_by=partition_by,
        ensure_join_coverage=ensure_join_coverage,
    )
    output_files = output_files_for_dataset(data, out_dir, format_name, overwrite=overwrite)

    warnings: list[str] = []
    validation: dict[str, Any] = {}
    coverage_path = None
    if required_values or partition_by or ensure_join_coverage:
        coverage = validate_query_coverage(
            data,
            required_values=required_values,
            partition_by=partition_by,
            relationships=relationships,
            ensure_join_coverage=ensure_join_coverage,
        )
        validation["query_coverage"] = coverage
        warnings.extend(str(item) for item in coverage.get("warnings", []))
        coverage_path = out_dir / "query_coverage.json"
        write_json(coverage_path, coverage, overwrite=overwrite)

    schema_summary = dataset_summary(data)
    manifest = build_generation_manifest(
        dataset_name="great_generator_mcp_relational_dataset",
        tables=data,
        engine="pandas",
        seed=seed,
        parameters={
            "tool": "generate_relational",
            "rows": json_safe(rows_arg),
            "format": format_name,
            "relationships": json_safe(relationships or []),
            "required_values": json_safe(required_values or {}),
            "partition_by": json_safe(partition_by or {}),
            "ensure_join_coverage": ensure_join_coverage,
        },
        validation=validation,
        warnings=warnings,
        real_data_ingested=False,
    )
    manifest_payload = mcp_manifest_payload(
        manifest,
        tool_name="generate_relational",
        output_files=output_files,
        schema_summary=schema_summary,
        query_coverage_report_path=coverage_path,
    )
    write_json(manifest_path, manifest_payload, overwrite=overwrite)

    return {
        "status": "ok",
        "tool": "generate_relational",
        "output_files": [str(path) for path in output_files],
        "row_counts": {table_name: int(len(frame)) for table_name, frame in data.items()},
        "tables": list(data),
        "relationship_summary": json_safe(relationships or []),
        "schema_summary": json_safe(schema_summary),
        "preview": {
            table_name: dataframe_preview(frame, preview_count)
            for table_name, frame in data.items()
        },
        "manifest_path": str(manifest_path),
        "query_coverage_report_path": str(coverage_path) if coverage_path else None,
        "warnings": warnings,
    }


def _tables_from_schemas(
    schemas: Mapping[str, Any],
    rows: Mapping[str, int] | int | None,
) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    for table_name, schema_spec in schemas.items():
        if isinstance(schema_spec, Mapping) and "schema" in schema_spec:
            tables[str(table_name)] = dict(schema_spec)
        else:
            spec: dict[str, Any] = {"schema": schema_spec}
            if isinstance(rows, Mapping) and table_name in rows:
                spec["rows"] = int(rows[table_name])
            tables[str(table_name)] = spec
    return tables


def _validate_rows_from_inputs(
    schemas: Mapping[str, Any],
    rows: Mapping[str, int] | int | None,
    *,
    allow_large: bool,
    config: MCPConfig | None,
) -> Mapping[str, int] | int | None:
    if rows is not None:
        return validate_row_mapping(rows, allow_large=allow_large, config=config)
    spec_counts: dict[str, int] = {}
    for table_name, schema_spec in schemas.items():
        if isinstance(schema_spec, Mapping) and "rows" in schema_spec:
            spec_counts[str(table_name)] = validate_row_count(
                int(schema_spec["rows"]),
                allow_large=allow_large,
                config=config,
                label=f"rows[{table_name}]",
            )
    if spec_counts:
        validate_row_count(
            sum(spec_counts.values()),
            allow_large=allow_large,
            config=config,
            label="total rows",
        )
    return None


def _tables_define_rows(tables: Mapping[str, Any]) -> bool:
    return any(isinstance(spec, Mapping) and "rows" in spec for spec in tables.values())

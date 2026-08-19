"""JSON-safe serialization and local file helpers for MCP tools."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from great_generator.mcp.safety import SYNTHETIC_DATA_NOTICE, GreatGeneratorMCPError, safe_file_stem

_SUPPORTED_INPUT_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet"}
_RESERVED_JSON_FILES = {"manifest.json", "query_coverage.json"}


def json_safe(value: Any) -> Any:
    """Return a JSON-safe representation for common scientific Python values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (Mapping, Sequence, str, bytes)) else False:
        return None
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (ValueError, TypeError):
            pass
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [json_safe(item) for item in value]
    return str(value)


def dataframe_preview(frame: pd.DataFrame, preview_rows: int) -> list[dict[str, Any]]:
    if preview_rows <= 0:
        return []
    return json_safe(frame.head(preview_rows).to_dict(orient="records"))


def dataframe_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "row_count": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
    }


def dataset_summary(data: pd.DataFrame | Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    if isinstance(data, pd.DataFrame):
        return dataframe_summary(data)
    return {str(table): dataframe_summary(frame) for table, frame in data.items()}


def contract_summary(contract: Any, *, include_diagnostics: bool = False) -> dict[str, Any]:
    if not hasattr(contract, "as_dict"):
        raise GreatGeneratorMCPError("DDL parser did not return a contract-like object.")
    payload = contract.as_dict()
    tables = payload.get("tables", {})
    summary = {
        "name": payload.get("name"),
        "namespace": payload.get("namespace"),
        "source_format": payload.get("source_format"),
        "source_dialect": payload.get("source_dialect"),
        "table_count": len(tables),
        "tables": tables,
    }
    if hasattr(contract, "fingerprint"):
        summary["fingerprint"] = contract.fingerprint()
    if include_diagnostics:
        summary["diagnostics"] = payload.get("metadata", {}).get("diagnostics", [])
    return json_safe(summary)


def write_dataframe(frame: pd.DataFrame, path: Path, format_name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "csv":
        frame.to_csv(path, index=False)
    elif format_name == "jsonl":
        frame.to_json(path, orient="records", lines=True, date_format="iso")
    elif format_name == "parquet":
        frame.to_parquet(path, index=False)
    else:
        raise GreatGeneratorMCPError(f"Unsupported format '{format_name}'.")
    return path


def write_json(path: Path, payload: Mapping[str, Any], *, overwrite: bool) -> Path:
    if path.exists() and not overwrite:
        raise GreatGeneratorMCPError(
            f"Output file already exists: {path}. Pass overwrite=True to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_dataset_path(path: Path) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load supported local generated files into Pandas DataFrames."""

    if path.is_file():
        return _read_frame(path)
    if not path.is_dir():
        raise GreatGeneratorMCPError(f"Unsupported input path: {path}.")

    frames: dict[str, pd.DataFrame] = {}
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        if child.is_file() and _is_data_file(child):
            frames[child.stem] = _read_frame(child)
        elif child.is_dir():
            data_files = [
                item for item in sorted(child.iterdir()) if item.is_file() and _is_data_file(item)
            ]
            if data_files:
                frames[child.name] = _read_frame(data_files[0])
    if not frames:
        raise GreatGeneratorMCPError(f"No supported data files found under {path}.")
    return frames


def output_files_for_dataset(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    output_dir: Path,
    format_name: str,
    *,
    overwrite: bool,
) -> list[Path]:
    from great_generator.mcp.safety import output_file_path

    if isinstance(data, pd.DataFrame):
        path = output_file_path(output_dir, "dataset", format_name, overwrite=overwrite)
        write_dataframe(data, path, format_name)
        return [path]

    files: list[Path] = []
    for table_name, frame in data.items():
        path = output_file_path(
            output_dir, safe_file_stem(table_name), format_name, overwrite=overwrite
        )
        write_dataframe(frame, path, format_name)
        files.append(path)
    return files


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(path, lines=True)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise GreatGeneratorMCPError(
        f"Unsupported input file format '{path.suffix}'. Use csv, jsonl, or parquet."
    )


def _is_data_file(path: Path) -> bool:
    return (
        path.suffix.lower() in _SUPPORTED_INPUT_SUFFIXES and path.name not in _RESERVED_JSON_FILES
    )


def mcp_manifest_payload(
    manifest: Mapping[str, Any],
    *,
    tool_name: str,
    output_files: Sequence[Path],
    schema_summary: Mapping[str, Any],
    query_coverage_report_path: Path | None = None,
) -> dict[str, Any]:
    payload = dict(manifest)
    payload.update(
        {
            "generated_by": "Great Generator MCP",
            "tool_name": tool_name,
            "synthetic_data_notice": SYNTHETIC_DATA_NOTICE,
            "output_files": [str(path) for path in output_files],
            "schema_summary": json_safe(schema_summary),
        }
    )
    if query_coverage_report_path is not None:
        payload["query_coverage_report_path"] = str(query_coverage_report_path)
    return json_safe(payload)

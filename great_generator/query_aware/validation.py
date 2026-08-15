"""Coverage reports for Query-Aware Generation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from great_generator.query_aware.config import (
    QueryProfile,
    normalize_query_profile,
    normalize_required_values,
)

_RELATIONSHIP_RE = re.compile(
    r"^\s*(?P<table>[A-Za-z_][\w]*)\.(?P<column>[A-Za-z_][\w]*)\s*"
    r"(?:->|references)\s*"
    r"(?P<parent_table>[A-Za-z_][\w]*)"
    r"(?:\.(?P<parent_column>[A-Za-z_][\w]*)|\(\s*(?P<paren_column>[A-Za-z_][\w]*)\s*\))"
    r"\s*$",
    re.IGNORECASE,
)


def validate_query_coverage(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    *,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    relationships: Sequence[str | Mapping[str, str]] | None = None,
    ensure_join_coverage: bool = False,
    query_profile: QueryProfile | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate that generated data covers requested query-aware constraints."""

    profile = normalize_query_profile(
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        query_profile=query_profile,
        ensure_join_coverage=ensure_join_coverage,
    )
    warnings: list[str] = []
    report: dict[str, Any] = {
        "required_values_status": _required_values_status(data, profile.required_values),
        "partition_coverage_status": _partition_coverage_status(data, profile.partition_by),
        "partition_counts": _partition_counts(data, profile.partition_by),
        "selectivity_actuals": _selectivity_actuals(
            data,
            profile.target_selectivity,
            warnings=warnings,
        ),
        "selectivity_targets": _jsonable_mapping(profile.target_selectivity or {}),
        "join_coverage_status": _join_coverage_status(
            data,
            profile.required_values,
            relationships=relationships,
            ensure_join_coverage=profile.ensure_join_coverage,
            warnings=warnings,
        ),
        "warnings": warnings,
    }
    report["passed"] = _report_passed(report)
    return report


def _required_values_status(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    required_values: Mapping[str, Any] | None,
) -> dict[str, dict[str, bool]]:
    status: dict[str, dict[str, bool]] = {}
    for key, values in normalize_required_values(required_values).items():
        frame, column_name, report_key = _resolve_frame_and_column(data, key)
        status[report_key] = {
            str(value): bool(_normalized_isin(frame[column_name], [value]).any())
            for value in values
        }
    return status


def _partition_coverage_status(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    partition_by: Mapping[str, Any] | None,
) -> dict[str, dict[str, bool]]:
    if not partition_by:
        return {}
    frame, column_name, report_key = _resolve_partition(data, partition_by)
    values = list(partition_by.get("values") or (partition_by.get("counts") or {}).keys())
    return {
        report_key: {
            str(value): bool(_normalized_isin(frame[column_name], [value]).any())
            for value in values
        }
    }


def _partition_counts(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    partition_by: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not partition_by:
        return {}
    frame, column_name, report_key = _resolve_partition(data, partition_by)
    counts = {
        str(key): int(value)
        for key, value in frame[column_name].map(_normalize_scalar).value_counts().items()
    }
    if isinstance(data, pd.DataFrame):
        return counts
    return {report_key: counts}


def _selectivity_actuals(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    target_selectivity: Mapping[str, Mapping[str, float]] | None,
    *,
    warnings: list[str],
) -> dict[str, dict[str, float]]:
    actuals: dict[str, dict[str, float]] = {}
    for key, targets in (target_selectivity or {}).items():
        frame, column_name, report_key = _resolve_frame_and_column(data, key)
        row_count = len(frame)
        actuals[report_key] = {}
        for value, target in targets.items():
            actual = (
                float(_normalized_isin(frame[column_name], [value]).sum()) / row_count
                if row_count
                else 0.0
            )
            actuals[report_key][str(value)] = actual
            tolerance = max(0.03, 1.0 / max(row_count, 1))
            if abs(actual - float(target)) > tolerance:
                warnings.append(
                    f"target_selectivity for '{report_key}' value '{value}' requested "
                    f"{float(target):.4f}, actual {actual:.4f}."
                )
    return actuals


def _join_coverage_status(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    required_values: Mapping[str, Any] | None,
    *,
    relationships: Sequence[str | Mapping[str, str]] | None,
    ensure_join_coverage: bool,
    warnings: list[str],
) -> dict[str, bool]:
    if not ensure_join_coverage:
        return {}
    if isinstance(data, pd.DataFrame):
        warnings.append("join coverage applies only to relational data.")
        return {}
    parsed_relationships = [_parse_relationship(item) for item in relationships or ()]
    if not parsed_relationships:
        warnings.append("join coverage requested, but no relationships were provided.")
        return {}

    status: dict[str, bool] = {}
    for required_key, values in normalize_required_values(required_values).items():
        if "." not in required_key:
            continue
        parent_table, required_column = required_key.split(".", 1)
        if parent_table not in data:
            status[required_key] = False
            continue
        matching_relationships = [
            relationship
            for relationship in parsed_relationships
            if relationship["parent_table"] == parent_table
        ]
        for relationship in matching_relationships:
            parent_frame = data[parent_table]
            child_table = relationship["table"]
            child_column = relationship["column"]
            parent_column = relationship["parent_column"]
            report_key = f"{child_table}->{parent_table}.{required_column}"
            if child_table not in data or child_column not in data[child_table].columns:
                status[report_key] = False
                continue
            parent_mask = _normalized_isin(parent_frame[required_column], values)
            parent_keys = parent_frame.loc[parent_mask, parent_column].dropna().tolist()
            child_frame = data[child_table]
            status[report_key] = bool(
                parent_keys and _normalized_isin(child_frame[child_column], parent_keys).any()
            )
    if not status:
        warnings.append(
            "join coverage requested, but no required parent values matched relationships."
        )
    return status


def _resolve_partition(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    partition_by: Mapping[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    column_name = str(partition_by["column"])
    if isinstance(data, pd.DataFrame):
        _ensure_column(data, column_name, "partition_by")
        return data, column_name, column_name
    table_name = str(partition_by.get("table", ""))
    if not table_name:
        raise ValueError("partition_by for relational coverage must include 'table'.")
    if table_name not in data:
        raise ValueError(f"partition_by references unknown table '{table_name}'.")
    _ensure_column(data[table_name], column_name, "partition_by")
    return data[table_name], column_name, f"{table_name}.{column_name}"


def _resolve_frame_and_column(
    data: pd.DataFrame | Mapping[str, pd.DataFrame],
    key: str,
) -> tuple[pd.DataFrame, str, str]:
    if isinstance(data, pd.DataFrame):
        _ensure_column(data, key, "required_values")
        return data, key, key
    if "." not in key:
        raise ValueError(
            "Relational query coverage requires table-qualified columns like 'table.column'."
        )
    table_name, column_name = key.split(".", 1)
    if table_name not in data:
        raise ValueError(f"Query coverage references unknown table '{table_name}'.")
    _ensure_column(data[table_name], column_name, "required_values")
    return data[table_name], column_name, key


def _ensure_column(frame: pd.DataFrame, column_name: str, option_name: str) -> None:
    if column_name not in frame.columns:
        raise ValueError(
            f"{option_name} references unknown column '{column_name}'. "
            f"Available columns: {list(frame.columns)}."
        )


def _parse_relationship(relationship: str | Mapping[str, str]) -> dict[str, str]:
    if isinstance(relationship, str):
        match = _RELATIONSHIP_RE.match(relationship)
        if match is None:
            raise ValueError(
                "Relationship strings must look like "
                "'orders.customer_id -> customers.customer_id'."
            )
        return {
            "table": match.group("table"),
            "column": match.group("column"),
            "parent_table": match.group("parent_table"),
            "parent_column": match.group("parent_column") or match.group("paren_column"),
        }
    return {
        "table": str(relationship.get("table") or relationship.get("child_table")),
        "column": str(relationship.get("column") or relationship.get("child_column")),
        "parent_table": str(relationship.get("parent_table")),
        "parent_column": str(relationship.get("parent_column")),
    }


def _report_passed(report: Mapping[str, Any]) -> bool:
    for section in ("required_values_status", "partition_coverage_status", "join_coverage_status"):
        values = report.get(section, {})
        if not _nested_status_passed(values):
            return False
    return True


def _nested_status_passed(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_nested_status_passed(item) for item in value.values())
    return bool(value)


def _normalized_isin(series: pd.Series, values: list[Any]) -> pd.Series:
    normalized_values = {_normalize_scalar(value) for value in values}
    return series.map(_normalize_scalar).isin(normalized_values)


def _normalize_scalar(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _jsonable_mapping(mapping: Mapping[str, Mapping[str, float]]) -> dict[str, dict[str, float]]:
    return {
        str(column): {str(value): float(ratio) for value, ratio in values.items()}
        for column, values in mapping.items()
    }

"""Pandas implementation for Query-Aware Generation."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import cycle
from typing import Any

import pandas as pd

from great_generator.query_aware.config import (
    QueryProfile,
    normalize_other_values,
    normalize_required_values,
)
from great_generator.schemas.models import DomainSchema, TableSchema
from great_generator.utils.random import get_rng


def apply_query_aware_pandas(
    frame: pd.DataFrame,
    table: TableSchema,
    profile: QueryProfile,
    *,
    seed: int | None = None,
) -> pd.DataFrame:
    """Apply query-aware constraints to a single pandas DataFrame."""

    if not profile.enabled:
        return frame

    result = frame.copy()
    required_values = normalize_required_values(profile.required_values)
    other_values = normalize_other_values(profile.required_values)
    target_selectivity = profile.target_selectivity or {}
    partition_column = (
        str(profile.partition_by["column"]) if profile.partition_by is not None else None
    )

    _validate_columns(table, [*required_values, *target_selectivity])
    if partition_column is not None:
        _validate_columns(table, [partition_column])

    for column_name, targets in target_selectivity.items():
        if column_name == partition_column:
            continue
        result = _apply_target_selectivity(
            result,
            table,
            str(column_name),
            targets,
            other_values=other_values.get(str(column_name), []),
            seed=seed,
        )

    result = _ensure_required_value_combinations(
        result,
        table,
        {
            column: values
            for column, values in required_values.items()
            if column != partition_column
        },
        target_selectivity=target_selectivity,
        other_values=other_values,
        seed=seed,
    )

    if profile.partition_by is not None:
        result = _apply_partitioning(result, table, profile.partition_by, seed=seed)

    return result


def apply_query_aware_relational_pandas(
    data: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
    profile: QueryProfile,
    *,
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Apply query-aware constraints to a relational pandas dataset."""

    if not profile.enabled:
        return dict(data)

    table_required = _split_table_qualified_mapping(
        profile.required_values,
        schema,
        option_name="required_values",
    )
    table_selectivity = _split_table_qualified_mapping(
        profile.target_selectivity,
        schema,
        option_name="target_selectivity",
    )
    table_partition = _relational_partition_by(profile.partition_by, schema)

    result = {name: frame.copy() for name, frame in data.items()}
    for table_name, table in schema.tables.items():
        table_profile = QueryProfile(
            required_values=table_required.get(table_name),
            partition_by=table_partition if table_partition.get("table") == table_name else None,
            target_selectivity=table_selectivity.get(table_name),
            ensure_join_coverage=False,
        )
        if table_profile.enabled:
            result[table_name] = apply_query_aware_pandas(
                result[table_name],
                table,
                table_profile,
                seed=seed,
            )

    if profile.ensure_join_coverage:
        result = _ensure_join_coverage(
            result,
            schema,
            table_required,
            seed=seed,
        )

    return result


def _apply_target_selectivity(
    frame: pd.DataFrame,
    table: TableSchema,
    column_name: str,
    targets: Mapping[str, float],
    *,
    other_values: list[Any],
    seed: int | None,
) -> pd.DataFrame:
    row_count = len(frame)
    if row_count == 0:
        if any(float(ratio) > 0 for ratio in targets.values()):
            raise ValueError(
                f"target_selectivity for column '{column_name}' cannot be satisfied with zero rows."
            )
        return frame

    column = _column(table, column_name)
    coerced_targets = {
        _coerce_value(value, column, frame[column_name]): float(ratio)
        for value, ratio in targets.items()
    }
    counts = _target_counts(coerced_targets, row_count)
    rng = get_rng(seed, f"query-aware:selectivity:{table.name}.{column_name}")
    indices = rng.permutation(row_count)
    position = 0
    for value, count in counts.items():
        if count <= 0:
            continue
        selected = indices[position : position + count]
        _set_column_positions(frame, column_name, selected, value)
        position += count

    assigned = set(int(index) for index in indices[:position])
    remaining = [index for index in range(row_count) if index not in assigned]
    frame = _replace_avoided_values(
        frame,
        table,
        column_name,
        avoid_values=list(coerced_targets),
        row_indices=remaining,
        other_values=other_values,
    )
    return frame


def _ensure_required_value_combinations(
    frame: pd.DataFrame,
    table: TableSchema,
    required_values: Mapping[str, list[Any]],
    *,
    target_selectivity: Mapping[str, Mapping[str, float]],
    other_values: Mapping[str, list[Any]],
    seed: int | None,
) -> pd.DataFrame:
    if not required_values:
        return frame

    row_count = len(frame)
    max_required = max(len(values) for values in required_values.values())
    if row_count == 0 or row_count < max_required:
        raise ValueError(
            "required_values cannot be satisfied because the requested row count is "
            f"{row_count}, but at least {max_required} row(s) are needed."
        )

    rng = get_rng(seed, f"query-aware:required:{table.name}")
    selected_indices = rng.permutation(row_count)[:max_required]

    for column_name, values in required_values.items():
        column = _column(table, column_name)
        coerced = [_coerce_value(value, column, frame[column_name]) for value in values]
        value_cycle = cycle(coerced)
        for row_index in selected_indices:
            _set_cell_position(frame, column_name, int(row_index), next(value_cycle))

    for column_name, values in required_values.items():
        if column_name in target_selectivity:
            continue
        column = _column(table, column_name)
        coerced = [_coerce_value(value, column, frame[column_name]) for value in values]
        frame = _ensure_non_required_value_when_possible(
            frame,
            table,
            column_name,
            required_values=coerced,
            other_values=other_values.get(column_name, []),
        )

    return frame


def _apply_partitioning(
    frame: pd.DataFrame,
    table: TableSchema,
    partition_by: Mapping[str, Any],
    *,
    seed: int | None,
) -> pd.DataFrame:
    row_count = len(frame)
    column_name = str(partition_by["column"])
    column = _column(table, column_name)
    counts = _partition_counts(partition_by, row_count)
    if row_count == 0 and any(count > 0 for count in counts.values()):
        raise ValueError("partition_by cannot be satisfied with zero rows.")

    rng = get_rng(seed, f"query-aware:partition:{table.name}.{column_name}")
    indices = rng.permutation(row_count)
    position = 0
    for raw_value, count in counts.items():
        value = _coerce_value(raw_value, column, frame[column_name])
        selected = indices[position : position + count]
        _set_column_positions(frame, column_name, selected, value)
        position += count
    return frame


def _ensure_join_coverage(
    data: dict[str, pd.DataFrame],
    schema: DomainSchema,
    table_required: Mapping[str, Mapping[str, Any]],
    *,
    seed: int | None,
) -> dict[str, pd.DataFrame]:
    parent_requirements = {
        table_name: required
        for table_name, required in table_required.items()
        if required and schema.tables[table_name].primary_key is not None
    }
    if not parent_requirements:
        return data

    inbound_fks = _inbound_foreign_keys(schema)
    for parent_table in parent_requirements:
        if parent_table not in inbound_fks:
            raise ValueError(
                "ensure_join_coverage=True requires a child relationship for required "
                f"values on table '{parent_table}'."
            )

    result = {name: frame.copy() for name, frame in data.items()}
    required_parent_keys: dict[str, list[Any]] = {}
    for parent_table, required in parent_requirements.items():
        parent_schema = schema.tables[parent_table]
        parent_key = parent_schema.primary_key
        if parent_key is None:
            continue
        parent_frame = result[parent_table]
        key_values = _matching_parent_keys(parent_frame, parent_schema, required)
        if not key_values:
            raise ValueError(
                "ensure_join_coverage=True could not find parent rows matching "
                f"required_values for table '{parent_table}'."
            )
        required_parent_keys[parent_table] = key_values

    rng = get_rng(seed, "query-aware:join-coverage")
    for child_table, table in schema.tables.items():
        relevant_fks = [fk for fk in table.foreign_keys if fk.parent_table in required_parent_keys]
        if not relevant_fks:
            continue
        child_frame = result[child_table].copy()
        if child_frame.empty:
            raise ValueError(
                "ensure_join_coverage=True cannot create join coverage because child "
                f"table '{child_table}' has zero rows."
            )
        coverage_rows = max(
            [1, len(relevant_fks)]
            + [len(required_parent_keys[fk.parent_table]) for fk in relevant_fks]
        )
        selected_indices = rng.permutation(len(child_frame))[: min(len(child_frame), coverage_rows)]
        for fk in relevant_fks:
            keys = required_parent_keys[fk.parent_table]
            key_cycle = cycle(keys)
            for row_index in selected_indices:
                _set_cell_position(child_frame, fk.column, int(row_index), next(key_cycle))
        result[child_table] = child_frame
    return result


def _matching_parent_keys(
    frame: pd.DataFrame,
    table: TableSchema,
    required: Mapping[str, Any],
) -> list[Any]:
    if table.primary_key is None:
        return []
    mask = pd.Series(True, index=frame.index)
    for column_name, values in normalize_required_values(required).items():
        column = _column(table, column_name)
        coerced = [_coerce_value(value, column, frame[column_name]) for value in values]
        mask = mask & _normalized_isin(frame[column_name], coerced)
    return frame.loc[mask, table.primary_key].dropna().tolist()


def _split_table_qualified_mapping(
    value: Mapping[str, Any] | None,
    schema: DomainSchema,
    *,
    option_name: str,
) -> dict[str, dict[str, Any]]:
    split: dict[str, dict[str, Any]] = {}
    for qualified_column, spec in (value or {}).items():
        table_name, column_name = _split_qualified_column(
            str(qualified_column),
            schema,
            option_name=option_name,
        )
        split.setdefault(table_name, {})[column_name] = spec
    return split


def _split_qualified_column(
    value: str,
    schema: DomainSchema,
    *,
    option_name: str,
) -> tuple[str, str]:
    if "." not in value:
        raise ValueError(
            f"{option_name} for relational generation must use table-qualified columns "
            f"like 'table.column'. Received '{value}'."
        )
    table_name, column_name = value.split(".", 1)
    if table_name not in schema.tables:
        raise ValueError(
            f"{option_name} references unknown table '{table_name}'. "
            f"Available tables: {sorted(schema.tables)}."
        )
    return table_name, column_name


def _relational_partition_by(
    partition_by: Mapping[str, Any] | None,
    schema: DomainSchema,
) -> dict[str, Any]:
    if partition_by is None:
        return {}
    table_name = partition_by.get("table")
    if not table_name:
        raise ValueError("partition_by for relational generation must include 'table'.")
    table_name = str(table_name)
    if table_name not in schema.tables:
        raise ValueError(
            f"partition_by references unknown table '{table_name}'. "
            f"Available tables: {sorted(schema.tables)}."
        )
    return dict(partition_by)


def _inbound_foreign_keys(schema: DomainSchema) -> dict[str, list[tuple[str, Any]]]:
    inbound: dict[str, list[tuple[str, Any]]] = {}
    for child_table, table in schema.tables.items():
        for fk in table.foreign_keys:
            inbound.setdefault(fk.parent_table, []).append((child_table, fk))
    return inbound


def _partition_counts(partition_by: Mapping[str, Any], row_count: int) -> dict[Any, int]:
    if partition_by.get("counts"):
        counts = {value: int(count) for value, count in partition_by["counts"].items()}
        total = sum(counts.values())
        if total != row_count:
            raise ValueError(
                "partition_by custom counts must sum to rows. "
                f"Got counts sum {total} for {row_count} generated rows."
            )
        return counts

    values = list(partition_by.get("values") or [])
    if not values:
        raise ValueError("partition_by must include non-empty 'values' or 'counts'.")
    if row_count < len(values):
        raise ValueError(
            "partition_by values cannot all appear because rows is smaller than the "
            f"number of partition values ({row_count} rows, {len(values)} values)."
        )
    base = row_count // len(values)
    remainder = row_count % len(values)
    return {value: base + (1 if index < remainder else 0) for index, value in enumerate(values)}


def _target_counts(targets: Mapping[Any, float], row_count: int) -> dict[Any, int]:
    counts = {value: int(round(float(ratio) * row_count)) for value, ratio in targets.items()}
    for value, ratio in targets.items():
        if ratio > 0 and counts[value] == 0 and row_count >= len(targets):
            counts[value] = 1
    while sum(counts.values()) > row_count:
        largest = max(counts, key=lambda value: counts[value])
        counts[largest] -= 1
    return counts


def _replace_avoided_values(
    frame: pd.DataFrame,
    table: TableSchema,
    column_name: str,
    *,
    avoid_values: list[Any],
    row_indices: list[int],
    other_values: list[Any],
) -> pd.DataFrame:
    if not row_indices:
        return frame
    replacement_values = _replacement_values(
        frame,
        table,
        column_name,
        avoid_values=avoid_values,
        other_values=other_values,
    )
    if not replacement_values:
        return frame
    replacement_cycle = cycle(replacement_values)
    series = frame[column_name]
    normalized_avoid = {_normalize_scalar(value) for value in avoid_values}
    matching_indices = [
        row_index
        for row_index in row_indices
        if _normalize_scalar(series.iat[int(row_index)]) in normalized_avoid
    ]
    for row_index in matching_indices:
        _set_cell_position(frame, column_name, int(row_index), next(replacement_cycle))
    return frame


def _ensure_non_required_value_when_possible(
    frame: pd.DataFrame,
    table: TableSchema,
    column_name: str,
    *,
    required_values: list[Any],
    other_values: list[Any],
) -> pd.DataFrame:
    if len(frame) <= len(required_values):
        return frame
    if not _normalized_isin(frame[column_name], required_values).all():
        return frame
    replacements = _replacement_values(
        frame,
        table,
        column_name,
        avoid_values=required_values,
        other_values=other_values,
    )
    if replacements:
        _set_cell_position(frame, column_name, len(required_values), replacements[0])
    return frame


def _replacement_values(
    frame: pd.DataFrame,
    table: TableSchema,
    column_name: str,
    *,
    avoid_values: list[Any],
    other_values: list[Any],
) -> list[Any]:
    column = _column(table, column_name)
    if other_values:
        return [_coerce_value(value, column, frame[column_name]) for value in other_values]
    existing = [
        value
        for value in frame[column_name].dropna().unique().tolist()
        if _normalize_scalar(value) not in {_normalize_scalar(item) for item in avoid_values}
    ]
    if existing:
        return existing
    return [_fallback_other_value(column, avoid_values, frame[column_name])]


def _fallback_other_value(column: Any, avoid_values: list[Any], series: pd.Series) -> Any:
    kind = _dtype_kind(column.dtype)
    candidate: Any
    if kind in {"int", "long"}:
        candidate = 1
        avoided = {_normalize_scalar(value) for value in avoid_values}
        while _normalize_scalar(candidate) in avoided:
            candidate += 1
        return candidate
    if kind in {"float", "decimal"}:
        candidate = 1.0
        avoided = {_normalize_scalar(value) for value in avoid_values}
        while _normalize_scalar(candidate) in avoided:
            candidate += 1.0
        return candidate
    if kind == "bool":
        return not bool(avoid_values[0]) if avoid_values else True
    if kind == "date":
        return _coerce_value("2099-12-31", column, series)
    if kind == "timestamp":
        return _coerce_value("2099-12-31T00:00:00", column, series)
    candidate = "__OTHER__"
    avoided = {_normalize_scalar(value) for value in avoid_values}
    suffix = 1
    while _normalize_scalar(candidate) in avoided:
        candidate = f"__OTHER_{suffix}__"
        suffix += 1
    return candidate


def _set_column_positions(
    frame: pd.DataFrame,
    column_name: str,
    row_positions: Any,
    value: Any,
) -> None:
    labels = [frame.index[int(position)] for position in row_positions]
    if labels:
        frame.loc[labels, column_name] = value


def _set_cell_position(
    frame: pd.DataFrame,
    column_name: str,
    row_position: int,
    value: Any,
) -> None:
    frame.at[frame.index[int(row_position)], column_name] = value


def _validate_columns(table: TableSchema, column_names: list[str]) -> None:
    available = set(table.column_names())
    for column_name in column_names:
        if str(column_name) not in available:
            raise ValueError(
                f"Query-aware option references unknown column '{column_name}' in "
                f"table '{table.name}'. Available columns: {table.column_names()}."
            )


def _column(table: TableSchema, column_name: str) -> Any:
    for column in table.columns:
        if column.name == column_name:
            return column
    raise ValueError(
        f"Column '{column_name}' does not exist in table '{table.name}'. "
        f"Available columns: {table.column_names()}."
    )


def _coerce_value(value: Any, column: Any, series: pd.Series) -> Any:
    if value is None:
        return None
    kind = _dtype_kind(column.dtype)
    try:
        if kind in {"int", "long"}:
            return int(value)
        if kind in {"float", "decimal"}:
            return float(value)
        if kind == "bool":
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "y"}:
                    return True
                if lowered in {"false", "0", "no", "n"}:
                    return False
                raise ValueError
            return bool(value)
        if kind == "date":
            timestamp = pd.to_datetime(value)
            return timestamp if pd.api.types.is_datetime64_any_dtype(series) else timestamp.date()
        if kind == "timestamp":
            return pd.to_datetime(value)
        return str(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"Value {value!r} is incompatible with column '{column.name}' "
            f"of type '{column.dtype}'."
        ) from exc


def _dtype_kind(dtype: str) -> str:
    normalized = str(dtype).lower().strip()
    if "bool" in normalized:
        return "bool"
    if "timestamp" in normalized or "datetime" in normalized:
        return "timestamp"
    if normalized == "date" or normalized.endswith("date"):
        return "date"
    if "decimal" in normalized or "numeric" in normalized:
        return "decimal"
    if any(token in normalized for token in ("double", "float", "real")):
        return "float"
    if "bigint" in normalized or "long" in normalized:
        return "long"
    if "int" in normalized and "interval" not in normalized:
        return "int"
    return "string"


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

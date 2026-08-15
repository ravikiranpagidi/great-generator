"""Configuration normalization for query-aware generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryProfile:
    """Normalized query-aware generation options.

    Users can pass a plain dictionary through ``query_profile`` or use direct
    keyword arguments such as ``required_values`` and ``partition_by``. Direct
    arguments are preferred in beginner documentation.
    """

    required_values: Mapping[str, Any] | None = None
    partition_by: Mapping[str, Any] | None = None
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None
    ensure_join_coverage: bool = False

    @property
    def enabled(self) -> bool:
        return bool(
            self.required_values
            or self.partition_by
            or self.target_selectivity
            or self.ensure_join_coverage
        )


def has_query_aware_options(
    *,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Any | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    query_profile: QueryProfile | Mapping[str, Any] | None = None,
    ensure_join_coverage: bool | None = None,
) -> bool:
    """Return true when any query-aware option is present."""

    return bool(
        required_values
        or _looks_like_query_partition(partition_by)
        or target_selectivity
        or query_profile
        or ensure_join_coverage
    )


def normalize_query_profile(
    *,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    query_profile: QueryProfile | Mapping[str, Any] | None = None,
    ensure_join_coverage: bool | None = None,
) -> QueryProfile:
    """Merge a reusable profile with direct keyword overrides."""

    base = _profile_from_mapping(query_profile)
    merged_required_values = (
        required_values if required_values is not None else base.required_values
    )
    merged_partition_by = partition_by if partition_by is not None else base.partition_by
    merged_target_selectivity = (
        target_selectivity if target_selectivity is not None else base.target_selectivity
    )
    merged_join_coverage = (
        bool(ensure_join_coverage)
        if ensure_join_coverage is not None
        else bool(base.ensure_join_coverage)
    )
    _validate_partition_config(merged_partition_by)
    _validate_target_selectivity(merged_target_selectivity)
    normalized_required = _normalize_required_values(
        merged_required_values,
        merged_target_selectivity,
    )
    return QueryProfile(
        required_values=normalized_required,
        partition_by=merged_partition_by,
        target_selectivity=merged_target_selectivity,
        ensure_join_coverage=merged_join_coverage,
    )


def normalize_required_values(required_values: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    """Normalize the simple and advanced required-values forms."""

    normalized: dict[str, list[Any]] = {}
    for column, spec in (required_values or {}).items():
        normalized[str(column)] = _values_from_required_spec(column, spec)
    return normalized


def normalize_other_values(required_values: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    """Return optional ``other_values`` from advanced required-values specs."""

    other_values: dict[str, list[Any]] = {}
    for column, spec in (required_values or {}).items():
        if isinstance(spec, Mapping) and "other_values" in spec:
            other_values[str(column)] = _as_list(spec["other_values"])
    return other_values


def _profile_from_mapping(profile: QueryProfile | Mapping[str, Any] | None) -> QueryProfile:
    if profile is None:
        return QueryProfile()
    if isinstance(profile, QueryProfile):
        return profile
    if not isinstance(profile, Mapping):
        raise TypeError("query_profile must be a QueryProfile or mapping.")
    return QueryProfile(
        required_values=profile.get("required_values"),
        partition_by=profile.get("partition_by"),
        target_selectivity=profile.get("target_selectivity"),
        ensure_join_coverage=bool(profile.get("ensure_join_coverage", False)),
    )


def _normalize_required_values(
    required_values: Mapping[str, Any] | None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, Any] | None:
    if not required_values and not target_selectivity:
        return None
    merged: dict[str, Any] = dict(required_values or {})
    for column, value_targets in (target_selectivity or {}).items():
        existing = (
            normalize_required_values({column: merged[column]})[str(column)]
            if column in merged
            else []
        )
        target_values = [value for value in value_targets]
        merged[str(column)] = list(dict.fromkeys([*existing, *target_values]))
    return merged


def _values_from_required_spec(column: Any, spec: Any) -> list[Any]:
    if isinstance(spec, Mapping):
        if "values" not in spec:
            raise ValueError(f"required_values['{column}'] mapping must include a 'values' entry.")
        return _as_list(spec["values"])
    return _as_list(spec)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return [value]
    return list(value)


def _validate_partition_config(partition_by: Mapping[str, Any] | None) -> None:
    if partition_by is None:
        return
    if not isinstance(partition_by, Mapping):
        raise TypeError("partition_by must be a mapping for query-aware generation.")
    column = partition_by.get("column")
    if not column or not str(column).strip():
        raise ValueError("partition_by must include a non-empty 'column'.")
    distribution = str(partition_by.get("distribution", "balanced")).lower()
    has_values = bool(partition_by.get("values"))
    has_counts = bool(partition_by.get("counts"))
    if has_counts:
        counts = partition_by["counts"]
        if not isinstance(counts, Mapping) or not counts:
            raise ValueError("partition_by['counts'] must be a non-empty mapping.")
        for value, count in counts.items():
            if int(count) < 0:
                raise ValueError(
                    f"partition_by['counts']['{value}'] must be greater than or equal to zero."
                )
        return
    if distribution not in {"balanced", "custom_counts"}:
        raise ValueError("partition_by['distribution'] must be 'balanced' or 'custom_counts'.")
    if distribution == "custom_counts" and not has_counts:
        raise ValueError("partition_by with distribution='custom_counts' must include 'counts'.")
    if not has_values:
        raise ValueError("partition_by must include 'values' or 'counts'.")


def _validate_target_selectivity(
    target_selectivity: Mapping[str, Mapping[str, float]] | None,
) -> None:
    for column, targets in (target_selectivity or {}).items():
        if not isinstance(targets, Mapping) or not targets:
            raise ValueError(f"target_selectivity['{column}'] must be a non-empty mapping.")
        total = 0.0
        for value, ratio in targets.items():
            numeric_ratio = float(ratio)
            if numeric_ratio < 0.0 or numeric_ratio > 1.0:
                raise ValueError(
                    f"target_selectivity['{column}']['{value}'] must be between 0 and 1."
                )
            total += numeric_ratio
        if total > 1.0 + 1e-9:
            raise ValueError(f"target_selectivity for column '{column}' must not exceed 1.0.")


def _looks_like_query_partition(partition_by: Any | None) -> bool:
    return isinstance(partition_by, Mapping)

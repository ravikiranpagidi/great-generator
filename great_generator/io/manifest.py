"""Manifest helpers for generated data outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from great_generator.planning import ColumnTags, GenerationPlan

MANIFEST_VERSION = "1.0"


def build_generation_manifest(
    *,
    dataset_name: str,
    tables: Mapping[str, Any],
    engine: str = "pandas",
    seed: int | None = None,
    schema_fingerprint: str | None = None,
    parameters: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
    warnings: Sequence[str] | None = None,
    real_data_ingested: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a lightweight provenance manifest for generated datasets.

    The manifest is intentionally descriptive. It records how a dataset was
    requested, what tables were produced, and whether any real data was used as
    input. It does not hash full data contents. For Spark DataFrames, it avoids
    implicit row-count actions; record expected or validated row counts in
    ``parameters`` or ``validation`` when needed.
    """

    return {
        "manifest_version": MANIFEST_VERSION,
        "dataset_name": dataset_name,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "seed": seed,
        "schema_fingerprint": schema_fingerprint,
        "real_data_ingested": bool(real_data_ingested),
        "privacy_note": (
            "Great Generator creates synthetic data and does not anonymize, mask, "
            "de-identify, or transform production records."
        ),
        "parameters": dict(parameters or {}),
        "tables": {
            table_name: _table_manifest_entry(table) for table_name, table in sorted(tables.items())
        },
        "validation": dict(validation or {}),
        "warnings": list(warnings or []),
    }


def _table_manifest_entry(table: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "row_count": _safe_row_count(table),
        "columns": _safe_columns(table),
    }
    dtypes = _safe_dtypes(table)
    if dtypes:
        entry["dtypes"] = dtypes
    return entry


def _safe_row_count(table: Any) -> int | None:
    module_name = type(table).__module__
    if module_name.startswith("pyspark."):
        return None
    if hasattr(table, "shape"):
        try:
            return int(table.shape[0])
        except (TypeError, ValueError, IndexError):
            return None
    if hasattr(table, "count"):
        try:
            return int(table.count())
        except (TypeError, ValueError):
            return None
    return None


def _safe_columns(table: Any) -> list[str]:
    columns = getattr(table, "columns", None)
    if columns is None:
        return []
    return [str(column) for column in columns]


def _safe_dtypes(table: Any) -> dict[str, str]:
    dtypes = getattr(table, "dtypes", None)
    if dtypes is None:
        return {}
    if isinstance(dtypes, list):
        return {str(name): str(dtype) for name, dtype in dtypes}
    if hasattr(dtypes, "items"):
        return {str(name): str(dtype) for name, dtype in dtypes.items()}
    return {}


def advisor_manifest_entry(
    plan: GenerationPlan,
    *,
    tags: ColumnTags | None = None,
    called_at: Sequence[str] | None = None,
    cache_hit: bool | None = None,
) -> dict[str, Any]:
    """Build the advisor section for a manifest."""

    entry: dict[str, Any] = {
        "name": plan.advisor,
        "model_id": plan.model_id,
        "plan_version": plan.plan_version,
        "plan_fingerprint": plan.fingerprint(),
        "called_at": list(called_at or ["schema_understanding"]),
        "human_reviewed": plan.human_reviewed,
    }
    if cache_hit is not None:
        entry["cache_hit"] = bool(cache_hit)
    if tags is not None:
        entry["columns_tagged"] = len(tags.columns)
        if "column_tagging" not in entry["called_at"]:
            entry["called_at"].append("column_tagging")
    return entry


def enrich_manifest(
    manifest: Mapping[str, Any],
    *,
    plan: GenerationPlan | None = None,
    tags: ColumnTags | None = None,
    called_at: Sequence[str] | None = None,
    cache_hit: bool | None = None,
) -> dict[str, Any]:
    """Return a manifest copy with advisor metadata when a plan is present."""

    enriched = dict(manifest)
    if plan is not None:
        enriched["advisor"] = advisor_manifest_entry(
            plan,
            tags=tags,
            called_at=called_at,
            cache_hit=cache_hit,
        )
    return enriched

"""Shared helpers for compact industry domain packs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from great_generator.distributions.time_patterns import (
    random_timestamps_on_dates,
    sampled_month_starts,
    weighted_calendar_dates,
)
from great_generator.schemas.generation import generate_domain_schema_pandas
from great_generator.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema
from great_generator.utils.random import get_rng


def c(name: str, dtype: str, nullable: bool = False, description: str = "") -> ColumnSpec:
    """Create a column spec with terse domain-module syntax."""

    return ColumnSpec(name=name, dtype=dtype, nullable=nullable, description=description)


def table(
    name: str,
    primary_key: str,
    columns: Sequence[ColumnSpec],
    foreign_keys: Sequence[ForeignKey] = (),
    description: str = "",
) -> TableSchema:
    """Create a table schema with common defaults."""

    return TableSchema(
        name=name,
        primary_key=primary_key,
        columns=tuple(columns),
        foreign_keys=tuple(foreign_keys),
        description=description,
    )


def fk(column: str, parent_table: str, parent_column: str) -> ForeignKey:
    """Create a foreign-key relationship."""

    return ForeignKey(column, parent_table, parent_column)


def generate_industry_pandas(
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    seed: int | None = None,
    choices: Mapping[str, Sequence[Any]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate deterministic, relationship-safe pandas tables for an industry schema.

    The base schema generator creates valid keys and foreign keys. This helper then enriches
    non-key columns with pragmatic domain-looking values driven by column names and optional
    exact choice lists.
    """

    data = generate_domain_schema_pandas(schema, rows=row_counts, seed=seed)
    choices = choices or {}

    for table_name, table_schema in schema.tables.items():
        frame = data[table_name]
        skip = {table_schema.primary_key, *(key.column for key in table_schema.foreign_keys)}
        for column in table_schema.columns:
            if column.name in skip or column.name not in frame.columns:
                continue
            rng = get_rng(seed, f"{schema.name}.{table_name}.{column.name}")
            frame[column.name] = _values_for_column(
                table_name=table_name,
                column=column,
                rows=len(frame),
                rng=rng,
                choices=choices,
            )
    return data


def _values_for_column(
    table_name: str,
    column: ColumnSpec,
    rows: int,
    rng: np.random.Generator,
    choices: Mapping[str, Sequence[Any]],
) -> Any:
    exact_choices = choices.get(f"{table_name}.{column.name}") or choices.get(column.name)
    if exact_choices:
        return rng.choice(list(exact_choices), rows)

    dtype = column.dtype.lower()
    name = column.name.lower()

    if "timestamp" in dtype or "datetime" in dtype or name.endswith("_ts"):
        dates = weighted_calendar_dates(rng, rows)
        return random_timestamps_on_dates(rng, dates, business_hours_bias=0.68)
    if (
        dtype == "date"
        or dtype.endswith("date")
        or name.endswith("_date")
        or name.endswith("_month")
    ):
        if name.endswith("_month"):
            return sampled_month_starts(rng, rows, start="2024-01-01", periods=24)
        return weighted_calendar_dates(
            rng,
            rows,
            start="2021-01-01",
            end="2025-12-31",
            weekend_multiplier=0.9,
            holiday_multiplier=1.0,
        ).date
    if "bool" in dtype:
        if any(token in name for token in ("delayed", "failed", "defect", "fraud", "hazmat")):
            return rng.random(rows) < 0.08
        return rng.random(rows) < 0.5
    if "float" in dtype or "double" in dtype or "decimal" in dtype:
        if "score" in name or "rate" in name or "probability" in name:
            return np.round(rng.beta(5, 2, rows), 3)
        if any(
            token in name
            for token in (
                "amount",
                "cost",
                "price",
                "revenue",
                "premium",
                "balance",
                "value",
                "fee",
            )
        ):
            return np.round(rng.lognormal(5.0, 0.65, rows), 2)
        if "percent" in name or "utilization" in name:
            return np.round(rng.uniform(0, 100, rows), 2)
        return np.round(rng.normal(100, 18, rows), 2)
    if "int" in dtype or "long" in dtype:
        if "year" in name:
            return rng.integers(2008, 2027, rows)
        if any(token in name for token in ("quantity", "count", "units", "capacity", "seats")):
            return rng.integers(1, 500, rows)
        if "duration" in name or "minutes" in name or "hours" in name:
            return rng.integers(1, 240, rows)
        return rng.integers(1, 10_000, rows)
    if name.endswith("_code"):
        prefix = "".join(part[0].upper() for part in table_name.split("_"))[:4]
        return [f"{prefix}{index:08d}" for index in range(1, rows + 1)]
    if name.endswith("_name"):
        label = column.name.removesuffix("_name").replace("_", " ").title()
        return [f"{label} {index:05d}" for index in range(1, rows + 1)]
    if "status" in name:
        return rng.choice(
            ["active", "pending", "closed", "cancelled"], rows, p=[0.74, 0.12, 0.10, 0.04]
        )
    if "region" in name:
        return rng.choice(["north", "south", "east", "west", "central"], rows)
    if "type" in name:
        return rng.choice(["standard", "premium", "enterprise", "specialty"], rows)
    if "category" in name:
        return rng.choice(["core", "growth", "risk", "operations", "digital"], rows)
    return [f"{column.name}_{index}" for index in range(1, rows + 1)]

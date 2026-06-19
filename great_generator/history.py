"""Temporal history helpers for generated datasets."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Number
from typing import Any, cast

import pandas as pd

from great_generator.schemas.models import DomainSchema
from great_generator.utils.random import get_rng


def add_scd2_history_tables(
    data: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
    seed: int | None = None,
    history_window: str = "2y",
) -> dict[str, pd.DataFrame]:
    """Return generated data plus SCD2 history tables for keyed tables.

    Existing tables are preserved. Each keyed table receives a companion table named
    ``<table>_history`` with ``effective_from``, ``effective_to``, and ``is_current``.
    """

    enriched = {name: frame.copy() for name, frame in data.items()}
    for table_name, table in schema.tables.items():
        if table.primary_key is None or table_name not in data:
            continue
        enriched[f"{table_name}_history"] = generate_scd2_history(
            data[table_name],
            natural_key=table.primary_key,
            seed=seed,
            history_window=history_window,
            namespace=f"{schema.name}.{table_name}",
        )
    return enriched


def generate_scd2_history(
    frame: pd.DataFrame,
    natural_key: str,
    seed: int | None = None,
    history_window: str = "2y",
    namespace: str = "history",
) -> pd.DataFrame:
    """Generate deterministic SCD2 rows for a DataFrame with a natural key."""

    if natural_key not in frame.columns:
        raise ValueError(f"natural_key '{natural_key}' does not exist in the frame.")
    if frame.empty:
        return _empty_history(frame)

    rng = get_rng(seed, f"scd2.{namespace}")
    start_date = pd.Timestamp("2023-01-01")
    days = _history_days(history_window)
    records: list[pd.Series] = []
    history_id = 1

    mutable_columns = [
        column
        for column in frame.columns
        if column != natural_key
        and not column.endswith("_id")
        and column not in {"event_date", "order_ts", "transaction_ts", "ingestion_timestamp"}
    ]

    for _, source_row in frame.iterrows():
        versions = int(rng.integers(1, 4))
        cut_points = _cut_points(days, versions)
        previous_to = start_date

        for version_index, next_offset in enumerate(cut_points):
            row = source_row.copy()
            if version_index > 0:
                _apply_version_marker(row, mutable_columns, version_index)

            effective_from = previous_to
            is_current = version_index == versions - 1
            effective_to = (
                pd.Timestamp("2262-04-11")
                if is_current
                else start_date + pd.Timedelta(days=next_offset)
            )
            previous_to = effective_to

            row["scd_id"] = history_id
            row["effective_from"] = effective_from
            row["effective_to"] = effective_to
            row["is_current"] = is_current
            records.append(row)
            history_id += 1

    result = pd.DataFrame(records)
    ordered = ["scd_id", *frame.columns, "effective_from", "effective_to", "is_current"]
    return result[ordered].reset_index(drop=True)


def _history_days(history_window: str) -> int:
    value = history_window.strip().lower()
    if value.endswith("y"):
        return int(value[:-1]) * 365
    if value.endswith("d"):
        return int(value[:-1])
    raise ValueError("history_window must use a day or year suffix, such as '180d' or '2y'.")


def _cut_points(days: int, versions: int) -> list[int]:
    if versions == 1:
        return [days]
    step = max(1, days // versions)
    return [step * (index + 1) for index in range(versions - 1)] + [days]


def _apply_version_marker(row: pd.Series, mutable_columns: list[str], version_index: int) -> None:
    if not mutable_columns:
        return
    column = mutable_columns[version_index % len(mutable_columns)]
    value = row[column]
    if isinstance(value, str):
        row[column] = f"{value} v{version_index + 1}"
    elif isinstance(value, bool):
        row[column] = not value
    elif isinstance(value, Number):
        row[column] = cast(Any, value) + version_index


def _empty_history(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["scd_id", *frame.columns, "effective_from", "effective_to", "is_current"]
    return pd.DataFrame(columns=columns)

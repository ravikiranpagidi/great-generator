"""Controlled anomaly injection for pandas and Spark datasets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from enterprise_synth.schemas.models import DomainSchema
from enterprise_synth.utils.random import get_rng

SUPPORTED_ANOMALIES = {
    "null_rate",
    "duplicate_rate",
    "orphan_fk_rate",
    "late_arrival_rate",
    "out_of_order_rate",
    "outlier_rate",
    "skew_rate",
    "negative_amount_rate",
    "invalid_status_rate",
}


def _validate_config(anomalies: Mapping[str, float] | None) -> dict[str, float]:
    config = dict(anomalies or {})
    unknown = set(config) - SUPPORTED_ANOMALIES
    if unknown:
        raise ValueError(f"Unsupported anomaly type(s): {sorted(unknown)}")
    for name, value in config.items():
        if not 0 <= value <= 1:
            raise ValueError(f"Anomaly rate '{name}' must be between 0 and 1.")
    return config


def inject_anomalies_pandas(
    data: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
    anomalies: Mapping[str, float] | None,
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Return copied pandas frames with requested anomalies applied."""

    config = _validate_config(anomalies)
    if not config:
        return {name: frame.copy() for name, frame in data.items()}

    rng = get_rng(seed, "anomalies.pandas")
    mutated = {name: frame.copy() for name, frame in data.items()}

    null_rate = config.get("null_rate", 0.0)
    if null_rate:
        for table_name, table_schema in schema.tables.items():
            frame = mutated.get(table_name)
            if frame is None or frame.empty:
                continue
            nullable_columns = [column.name for column in table_schema.columns if column.nullable]
            candidate_columns = nullable_columns or [
                column
                for column in frame.columns
                if column
                not in {table_schema.primary_key, *(fk.column for fk in table_schema.foreign_keys)}
            ]
            if not candidate_columns:
                continue
            for column in candidate_columns:
                mask = rng.random(len(frame)) < null_rate
                if frame[column].dtype == bool:
                    frame[column] = frame[column].astype("object")
                frame.loc[mask, column] = pd.NA

    duplicate_rate = config.get("duplicate_rate", 0.0)
    if duplicate_rate:
        for table_name, frame in list(mutated.items()):
            duplicate_count = int(round(len(frame) * duplicate_rate))
            if duplicate_count and not frame.empty:
                extra = frame.sample(
                    n=duplicate_count,
                    replace=False,
                    random_state=int(rng.integers(0, 2**31 - 1)),
                )
                mutated[table_name] = pd.concat([frame, extra], ignore_index=True)

    orphan_rate = config.get("orphan_fk_rate", 0.0)
    if orphan_rate:
        for table_name, table_schema in schema.tables.items():
            frame = mutated.get(table_name)
            if frame is None or frame.empty:
                continue
            for fk in table_schema.foreign_keys:
                if fk.column not in frame:
                    continue
                mask = rng.random(len(frame)) < orphan_rate
                if not mask.any():
                    continue
                parent = mutated[fk.parent_table]
                if parent.empty:
                    continue
                parent_max = pd.to_numeric(parent[fk.parent_column], errors="coerce").max()
                frame.loc[mask, fk.column] = int(parent_max) + 10_000

    late_rate = config.get("late_arrival_rate", 0.0)
    out_of_order_rate = config.get("out_of_order_rate", 0.0)
    for frame in mutated.values():
        if frame.empty:
            continue
        event_col = next(
            (
                column
                for column in ["event_timestamp", "transaction_ts", "order_ts"]
                if column in frame
            ),
            None,
        )
        ingest_col = next((column for column in ["ingestion_timestamp"] if column in frame), None)
        if event_col and ingest_col and late_rate:
            mask = rng.random(len(frame)) < late_rate
            frame.loc[mask, ingest_col] = pd.to_datetime(
                frame.loc[mask, event_col]
            ) + pd.to_timedelta(
                rng.integers(2, 8, size=int(mask.sum())),
                unit="D",
            )
            for flag in ["late_arriving", "is_late_arriving"]:
                if flag in frame:
                    frame.loc[mask, flag] = True
        if event_col and ingest_col and out_of_order_rate:
            mask = rng.random(len(frame)) < out_of_order_rate
            frame.loc[mask, ingest_col] = pd.to_datetime(
                frame.loc[mask, event_col]
            ) - pd.to_timedelta(
                rng.integers(1, 180, size=int(mask.sum())),
                unit="m",
            )
            if "out_of_order" not in frame:
                frame["out_of_order"] = False
            frame.loc[mask, "out_of_order"] = True

    outlier_rate = config.get("outlier_rate", 0.0)
    negative_rate = config.get("negative_amount_rate", 0.0)
    invalid_status_rate = config.get("invalid_status_rate", 0.0)
    skew_rate = config.get("skew_rate", 0.0)
    for table_name, frame in mutated.items():
        if frame.empty:
            continue
        amount_columns = [
            column
            for column in frame.columns
            if column
            in {"amount", "total_amount", "subtotal", "line_amount", "refund_amount", "balance"}
        ]
        for column in amount_columns:
            if outlier_rate:
                mask = rng.random(len(frame)) < outlier_rate
                frame.loc[mask, column] = (
                    pd.to_numeric(frame.loc[mask, column], errors="coerce") * 10
                )
            if negative_rate:
                mask = rng.random(len(frame)) < negative_rate
                frame.loc[mask, column] = -pd.to_numeric(
                    frame.loc[mask, column], errors="coerce"
                ).abs()
        status_columns = [
            column for column in frame.columns if column.endswith("status") or column == "status"
        ]
        for column in status_columns:
            if invalid_status_rate:
                mask = rng.random(len(frame)) < invalid_status_rate
                frame.loc[mask, column] = "__INVALID__"
        if skew_rate:
            fk_columns = (
                [fk.column for fk in schema.tables[table_name].foreign_keys]
                if table_name in schema.tables
                else []
            )
            for column in fk_columns:
                if column in frame and frame[column].notna().any():
                    hot_key = frame[column].dropna().iloc[0]
                    mask = rng.random(len(frame)) < skew_rate
                    frame.loc[mask, column] = hot_key

    return mutated


def inject_anomalies_spark(
    data: Mapping[str, Any],
    schema: DomainSchema,
    anomalies: Mapping[str, float] | None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Apply a practical subset of anomalies to Spark DataFrames."""

    config = _validate_config(anomalies)
    if not config:
        return dict(data)

    from pyspark.sql import functions as F

    mutated = dict(data)
    for table_name, table_schema in schema.tables.items():
        frame = mutated.get(table_name)
        if frame is None:
            continue
        for column in frame.columns:
            if config.get("null_rate") and column not in {
                table_schema.primary_key,
                *(fk.column for fk in table_schema.foreign_keys),
            }:
                frame = frame.withColumn(
                    column,
                    F.when(F.rand(seed) < config["null_rate"], F.lit(None)).otherwise(
                        F.col(column)
                    ),
                )
        for fk in table_schema.foreign_keys:
            if config.get("orphan_fk_rate") and fk.column in frame.columns:
                frame = frame.withColumn(
                    fk.column,
                    F.when(
                        F.rand(seed) < config["orphan_fk_rate"], F.col(fk.column) + F.lit(10_000)
                    ).otherwise(F.col(fk.column)),
                )
        if config.get("duplicate_rate"):
            duplicate_subset = frame.sample(
                withReplacement=False, fraction=config["duplicate_rate"], seed=seed
            )
            frame = frame.unionByName(duplicate_subset)
        mutated[table_name] = frame
    return mutated

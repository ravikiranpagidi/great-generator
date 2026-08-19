from __future__ import annotations

import math

import pandas as pd

from great_generator.mcp.serializers import (
    dataframe_preview,
    dataframe_summary,
    json_safe,
    load_dataset_path,
    write_dataframe,
)


def test_json_safe_handles_pandas_and_nan_values():
    payload = json_safe(
        {
            "timestamp": pd.Timestamp("2026-01-01T10:30:00"),
            "nan": math.nan,
            "items": [pd.Timestamp("2026-01-02")],
        }
    )

    assert payload["timestamp"].startswith("2026-01-01T10:30:00")
    assert payload["nan"] is None
    assert payload["items"] == ["2026-01-02T00:00:00"]


def test_dataframe_summary_and_preview_are_small_json_safe():
    frame = pd.DataFrame(
        {"id": [1, 2, 3], "created_at": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])}
    )

    summary = dataframe_summary(frame)
    preview = dataframe_preview(frame, 2)

    assert summary["row_count"] == 3
    assert summary["columns"] == ["id", "created_at"]
    assert len(preview) == 2
    assert preview[0]["created_at"].startswith("2026-01-01")


def test_load_dataset_path_reads_single_csv(tmp_path):
    path = tmp_path / "dataset.csv"
    frame = pd.DataFrame({"id": [1, 2]})
    write_dataframe(frame, path, "csv")

    loaded = load_dataset_path(path)

    assert len(loaded) == 2
    assert list(loaded.columns) == ["id"]


def test_load_dataset_path_reads_directory_tables(tmp_path):
    write_dataframe(pd.DataFrame({"customer_id": [1]}), tmp_path / "customers.csv", "csv")
    write_dataframe(pd.DataFrame({"order_id": [10]}), tmp_path / "orders.jsonl", "jsonl")

    loaded = load_dataset_path(tmp_path)

    assert sorted(loaded) == ["customers", "orders"]
    assert len(loaded["orders"]) == 1

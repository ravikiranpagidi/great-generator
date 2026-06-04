from __future__ import annotations

from pathlib import Path

import pytest

from great_generator.exporters.csv_exporter import export_csv
from great_generator.exporters.delta_exporter import export_delta
from great_generator.exporters.parquet_exporter import export_parquet


class FakeWriter:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def mode(self, value: str):
        self.calls.append(("mode", value))
        return self

    def option(self, key: str, value: object):
        self.calls.append(("option", (key, value)))
        return self

    def options(self, **options: str):
        self.calls.append(("options", options))
        return self

    def partitionBy(self, *columns: str):
        self.calls.append(("partitionBy", columns))
        return self

    def format(self, value: str):
        self.calls.append(("format", value))
        return self

    def csv(self, path: str):
        self.calls.append(("csv", path))

    def parquet(self, path: str):
        self.calls.append(("parquet", path))

    def save(self, path: str):
        self.calls.append(("save", path))


class FakeSparkFrame:
    def __init__(self, columns: list[str] | None = None):
        self.columns = columns or []
        self.write = FakeWriter()
        self.partition_calls: list[tuple[str, int]] = []

    def repartition(self, count: int):
        self.partition_calls.append(("repartition", count))
        return self

    def coalesce(self, count: int):
        self.partition_calls.append(("coalesce", count))
        return self


def test_spark_parquet_preserves_s3_uri():
    frame = FakeSparkFrame(columns=["event_date"])
    export_parquet(
        {"transactions": frame},
        output_path="s3a://demo-bucket/banking",
        engine="spark",
        partition_by=["event_date"],
    )
    assert ("parquet", "s3a://demo-bucket/banking/transactions") in frame.write.calls


def test_spark_csv_preserves_adls_uri():
    frame = FakeSparkFrame()
    export_csv(
        {"customers": frame},
        output_path="abfss://container@acct.dfs.core.windows.net/demo",
        engine="spark",
    )
    assert (
        "csv",
        "abfss://container@acct.dfs.core.windows.net/demo/customers",
    ) in frame.write.calls


def test_spark_delta_preserves_gcs_uri():
    frame = FakeSparkFrame()
    export_delta(
        {"orders": frame},
        output_path="gs://demo-bucket/ecommerce",
        engine="spark",
    )
    assert ("save", "gs://demo-bucket/ecommerce/orders") in frame.write.calls


def test_spark_paths_support_dbfs_scheme():
    frame = FakeSparkFrame()
    export_parquet(
        {"orders": frame},
        output_path="dbfs:/Volumes/catalog/schema/volume/demo",
        engine="spark",
    )
    assert (
        "parquet",
        "dbfs:/Volumes/catalog/schema/volume/demo/orders",
    ) in frame.write.calls


def test_spark_writer_options_are_forwarded():
    frame = FakeSparkFrame(columns=["event_date"])
    export_parquet(
        {"transactions": frame},
        output_path="s3a://demo-bucket/banking",
        engine="spark",
        writer_options={"compression": "snappy"},
    )
    assert ("options", {"compression": "snappy"}) in frame.write.calls


def test_spark_partition_controls_are_forwarded():
    frame = FakeSparkFrame()
    export_csv(
        {"customers": frame},
        output_path="gs://demo-bucket/customers",
        engine="spark",
        num_partitions=8,
        partition_strategy="coalesce",
    )
    assert frame.partition_calls == [("coalesce", 8)]


def test_pandas_remote_uri_raises_helpful_error():
    with pytest.raises(ValueError, match="Pandas exports require a local filesystem path"):
        export_csv({}, output_path="s3a://bucket/path", engine="pandas")


def test_pandas_local_path_still_works(tmp_path: Path):
    import pandas as pd

    export_csv({"customers": pd.DataFrame({"customer_id": [1]})}, tmp_path, engine="pandas")
    assert (tmp_path / "customers" / "customers.csv").exists()

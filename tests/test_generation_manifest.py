import pandas as pd

from great_generator.io import build_generation_manifest


def test_build_generation_manifest_summarizes_pandas_tables_without_scanning_data():
    data = {
        "customers": pd.DataFrame({"customer_id": [1, 2], "name": ["Ava", "Liam"]}),
        "orders": pd.DataFrame({"order_id": [10], "customer_id": [1]}),
    }

    manifest = build_generation_manifest(
        dataset_name="unit_test_dataset",
        tables=data,
        engine="pandas",
        seed=123,
        schema_fingerprint="sha256:test",
        parameters={"rows": {"customers": 2, "orders": 1}},
        validation={"foreign_keys_valid": True},
        real_data_ingested=False,
        generated_at="2026-01-01T00:00:00+00:00",
    )

    assert manifest["manifest_version"] == "1.0"
    assert manifest["dataset_name"] == "unit_test_dataset"
    assert manifest["generated_at"] == "2026-01-01T00:00:00+00:00"
    assert manifest["seed"] == 123
    assert manifest["real_data_ingested"] is False
    assert manifest["tables"]["customers"]["row_count"] == 2
    assert manifest["tables"]["orders"]["columns"] == ["order_id", "customer_id"]
    assert manifest["validation"]["foreign_keys_valid"] is True


def test_build_generation_manifest_does_not_count_spark_like_tables():
    class FakeSparkFrame:
        __module__ = "pyspark.sql.dataframe"
        columns = ["id", "name"]
        dtypes = [("id", "bigint"), ("name", "string")]

        def count(self):  # pragma: no cover - must not be called
            raise AssertionError("manifest creation should not trigger Spark count actions")

    manifest = build_generation_manifest(
        dataset_name="spark_dataset",
        tables={"customers": FakeSparkFrame()},
        engine="spark",
        parameters={"rows": {"customers": 1000}},
    )

    assert manifest["tables"]["customers"]["row_count"] is None
    assert manifest["tables"]["customers"]["columns"] == ["id", "name"]
    assert manifest["tables"]["customers"]["dtypes"] == {"id": "bigint", "name": "string"}

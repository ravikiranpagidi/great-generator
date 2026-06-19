import os
import sys

import pytest

from great_generator import generate_domain, get_domain_schema, list_domains


@pytest.fixture(scope="module")
def spark():
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    pyspark = pytest.importorskip("pyspark")
    return (
        pyspark.sql.SparkSession.builder.master("local[1]")
        .appName("great-generator-domain-smoke-tests")
        .getOrCreate()
    )


@pytest.mark.parametrize("domain", list_domains())
def test_spark_domain_smoke_matches_declared_schema(domain, spark):
    schema = get_domain_schema(domain)
    data = generate_domain(domain, engine="spark", scale="tiny", spark=spark, seed=42)

    assert set(data) == set(schema.tables), f"{domain} returned an unexpected table set."

    for table_name, table in schema.tables.items():
        frame = data[table_name]

        assert frame.count() > 0, f"{domain}.{table_name} should not be empty."
        assert set(frame.columns) == set(
            table.column_names()
        ), f"{domain}.{table_name} columns should match the declared schema."

        if table.primary_key is not None:
            primary_key_count = frame.select(table.primary_key).count()
            distinct_primary_key_count = frame.select(table.primary_key).distinct().count()
            assert (
                primary_key_count == distinct_primary_key_count
            ), f"{domain}.{table_name}.{table.primary_key} should be unique."

        for column in frame.columns:
            non_null_count = frame.where(frame[column].isNotNull()).limit(1).count()
            assert non_null_count == 1, f"{domain}.{table_name}.{column} should not be all null."

        for foreign_key in table.foreign_keys:
            parent = data[foreign_key.parent_table].select(foreign_key.parent_column)
            child = frame.where(frame[foreign_key.column].isNotNull()).select(foreign_key.column)
            orphan_count = child.join(
                parent,
                child[foreign_key.column] == parent[foreign_key.parent_column],
                how="left_anti",
            ).count()
            assert (
                orphan_count == 0
            ), f"{domain}.{table_name}.{foreign_key.column} should reference valid parent keys."

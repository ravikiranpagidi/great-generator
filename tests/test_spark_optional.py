import os
import sys

import pytest

from great_generator import (
    generate_domain,
    generate_from_schema,
    generate_relational,
    get_domain_schema,
)


@pytest.fixture(scope="module")
def spark():
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    pyspark = pytest.importorskip("pyspark")
    return (
        pyspark.sql.SparkSession.builder.master("local[1]")
        .appName("great-generator-tests")
        .getOrCreate()
    )


def test_spark_generation_returns_dataframes(spark):
    data = generate_domain("ecommerce", engine="spark", scale="tiny", spark=spark, seed=42)
    assert data["customers"].count() == 25
    assert data["orders"].count() == 60


def test_spark_relationships_are_valid(spark):
    data = generate_domain("banking", engine="spark", scale="tiny", spark=spark, seed=42)
    orphan_accounts = (
        data["transactions"].join(data["accounts"], on="account_id", how="left_anti").count()
    )
    assert orphan_accounts == 0


def test_spark_schema_driven_generation_supports_new_domains(spark):
    data = generate_domain("healthcare", engine="spark", scale="tiny", spark=spark, seed=42)

    assert data["patients"].count() == 30
    assert data["encounters"].count() == 90
    orphan_encounters = (
        data["encounters"].join(data["patients"], on="patient_id", how="left_anti").count()
    )
    assert orphan_encounters == 0


def test_spark_generate_from_schema_accepts_structtype(spark):
    from pyspark.sql import types as T

    schema = T.StructType(
        [
            T.StructField("id", T.IntegerType(), False),
            T.StructField("name", T.StringType(), True),
            T.StructField("amount", T.DoubleType(), True),
        ]
    )

    frame = generate_from_schema(schema, rows=5, spark=spark, seed=42)

    assert frame.count() == 5
    assert frame.schema == schema
    assert frame.select("id").orderBy("id").first()[0] == 1


def test_spark_generate_from_schema_accepts_ddl_with_spark_context(spark):
    frame = generate_from_schema("id int, name string", rows=3, spark=spark, seed=42)

    assert frame.count() == 3
    assert frame.columns == ["id", "name"]
    assert frame.select("id").orderBy("id").first()[0] == 1
    assert hasattr(frame.write.mode("overwrite"), "parquet")


def test_spark_generate_from_schema_accepts_domain_schema_with_spark_context(spark):
    data = generate_from_schema(get_domain_schema("ecommerce"), rows=2, spark=spark, seed=42)

    assert data["customers"].count() == 2
    assert data["orders"].count() == 2


def test_spark_generate_from_schema_accepts_dataframe_input_and_can_write(spark):
    from pyspark.sql import types as T

    schema = T.StructType(
        [
            T.StructField("id", T.IntegerType(), False),
            T.StructField("name", T.StringType(), True),
            T.StructField("amount", T.DoubleType(), True),
        ]
    )
    input_df = spark.createDataFrame([], schema=schema)

    df = generate_from_schema(input_df, rows=5, seed=42)

    assert df.count() == 5
    assert df.schema == schema
    assert df.select("id").orderBy("id").first()[0] == 1

    writer = df.write.mode("overwrite")
    assert hasattr(writer, "csv")
    assert hasattr(writer, "parquet")
    assert hasattr(writer, "format")


def test_generate_relational_spark_uses_active_session_without_explicit_spark_argument(spark):
    data = generate_relational(
        tables={
            "customers": {
                "schema": "customer_id int primary key, name string",
                "rows": 3,
            },
            "orders": {
                "schema": "order_id int primary key, customer_id int references customers.customer_id",
                "rows": 9,
            },
        },
        engine="spark",
    )

    assert data["customers"].count() == 3
    assert data["orders"].count() == 9
    assert data["orders"].join(data["customers"], on="customer_id", how="left_anti").count() == 0

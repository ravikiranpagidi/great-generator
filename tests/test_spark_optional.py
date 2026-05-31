import os
import sys

import pytest

from enterprise_synth import generate_domain, generate_from_schema


@pytest.fixture(scope="module")
def spark():
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    pyspark = pytest.importorskip("pyspark")
    return (
        pyspark.sql.SparkSession.builder.master("local[1]")
        .appName("enterprise-synth-tests")
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


def test_spark_generate_from_schema_accepts_structtype(spark):
    from pyspark.sql import types as T

    schema = T.StructType(
        [
            T.StructField("id", T.IntegerType(), False),
            T.StructField("name", T.StringType(), True),
            T.StructField("amount", T.DoubleType(), True),
        ]
    )

    frame = generate_from_schema(schema, rows=5, engine="spark", spark=spark, seed=42)

    assert frame.count() == 5
    assert frame.schema == schema
    assert frame.select("id").orderBy("id").first()[0] == 1


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

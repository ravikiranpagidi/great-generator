import pytest

from enterprise_synth import generate_domain


@pytest.fixture(scope="module")
def spark():
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

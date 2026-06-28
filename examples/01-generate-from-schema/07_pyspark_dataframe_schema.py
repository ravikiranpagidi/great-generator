"""Infer both StructType and SparkSession from a PySpark DataFrame input."""

from pyspark.sql import types as T

from great_generator import generate_from_schema

schema = T.StructType(
    [
        T.StructField("transaction_id", T.StringType(), False),
        T.StructField("customer_name", T.StringType(), True),
        T.StructField("transaction_amount", T.DoubleType(), True),
        T.StructField("transaction_date", T.DateType(), True),
    ]
)

empty_df = spark.createDataFrame([], schema)  # noqa: F821 - provided by the Spark notebook
generated_df = generate_from_schema(empty_df, rows=1000, domain="banking")

generated_df.show(5, truncate=False)
generated_df.write.mode("overwrite").parquet("synthetic_transactions")

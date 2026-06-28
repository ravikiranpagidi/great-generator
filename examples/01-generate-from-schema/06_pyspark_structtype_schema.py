"""Generate a Spark DataFrame from StructType. Requires great-generator[spark]."""

from pyspark.sql import types as T

from great_generator import generate_from_schema

schema = T.StructType(
    [
        T.StructField("customer_id", T.StringType(), False),
        T.StructField("customer_name", T.StringType(), True),
        T.StructField("age", T.IntegerType(), True),
        T.StructField("email", T.StringType(), True),
        T.StructField("balance", T.DoubleType(), True),
        T.StructField("created_at", T.TimestampType(), True),
    ]
)

# Uses the active SparkSession available in most Spark notebooks.
spark_df = generate_from_schema(schema, rows=1000, engine="spark")
spark_df.show(5, truncate=False)
spark_df.write.mode("overwrite").parquet("synthetic_customers_spark")

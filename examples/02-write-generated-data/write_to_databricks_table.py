"""Write generated Spark data to a Databricks table."""

from great_generator import generate_from_schema

spark_df = generate_from_schema(
    "customer_id string, customer_name string, created_at timestamp",
    rows=1000,
    engine="spark",
)
spark_df.write.format("delta").mode("overwrite").saveAsTable("dev.synthetic_customers")

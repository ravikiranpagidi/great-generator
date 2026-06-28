"""Write generated PySpark data to Snowflake with the Snowflake Spark Connector.

Databricks and other Spark clusters must provide a Snowflake Spark Connector
version compatible with their Spark and Scala runtime. Credentials are read from
a Databricks secret scope instead of being placed in notebook source.
"""

from great_generator import generate_from_schema


def secret(key: str) -> str:
    """Read a value from the Databricks secret scope used by this example."""

    return dbutils.secrets.get(scope="great-generator", key=key)  # noqa: F821


spark_df = generate_from_schema(
    {
        "customer_id": "string",
        "customer_name": "string",
        "email": "string",
        "balance": "double",
        "created_at": "timestamp",
        "account_status": "string",
    },
    rows=1000,
    engine="spark",
)

snowflake_options = {
    "sfURL": secret("snowflake-url"),
    "sfUser": secret("snowflake-user"),
    "sfPassword": secret("snowflake-password"),
    "sfDatabase": secret("snowflake-database"),
    "sfSchema": secret("snowflake-schema"),
    "sfWarehouse": secret("snowflake-warehouse"),
    "sfRole": secret("snowflake-role"),
}

(
    spark_df.write.format("net.snowflake.spark.snowflake")
    .options(**snowflake_options)
    .option("dbtable", "SYNTHETIC_CUSTOMERS")
    .mode("overwrite")
    .save()
)

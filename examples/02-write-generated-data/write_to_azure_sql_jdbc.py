"""Write generated PySpark data to Azure SQL with Spark JDBC.

The Spark runtime must include the Microsoft SQL Server JDBC driver. Databricks
credentials are read from a secret scope. Reduce partitions when necessary so a
large Spark cluster does not open too many concurrent database connections.
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

server = secret("azure-sql-server")
database = secret("azure-sql-database")
jdbc_url = (
    f"jdbc:sqlserver://{server}:1433;"
    f"databaseName={database};"
    "encrypt=true;"
    "trustServerCertificate=false;"
    "hostNameInCertificate=*.database.windows.net;"
    "loginTimeout=30;"
)

(
    spark_df.coalesce(4)
    .write.format("jdbc")
    .mode("overwrite")
    .option("url", jdbc_url)
    .option("dbtable", "dbo.synthetic_customers")
    .option("user", secret("azure-sql-user"))
    .option("password", secret("azure-sql-password"))
    .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")
    .option("batchsize", "1000")
    .save()
)

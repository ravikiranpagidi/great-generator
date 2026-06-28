# Spark Database Writes

Great Generator returns Spark DataFrames so users can write through connectors already supported by their Databricks or Spark runtime.

```python
from great_generator import generate_from_schema

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
```

## Connector choice

| Destination | Recommended Spark path | Runtime requirement |
|---|---|---|
| Snowflake | Snowflake Spark Connector | Connector compatible with the Spark and Scala runtime, plus its JDBC dependency |
| Azure SQL or SQL Server | Spark JDBC | Microsoft SQL Server JDBC driver |

Snowflake recommends its Spark connector instead of generic JDBC for larger Spark transfers because the connector is optimized for Spark-to-Snowflake movement. Azure SQL works naturally through Spark's JDBC data source and Microsoft SQL Server JDBC driver.

## Databricks secrets

The examples use a Databricks secret scope named `great-generator`. Create the scope and keys through your organization's approved process. Do not put passwords, OAuth tokens, or private keys in notebooks or source control.

Expected Snowflake keys:

```text
snowflake-url
snowflake-user
snowflake-password
snowflake-database
snowflake-schema
snowflake-warehouse
snowflake-role
```

Expected Azure SQL keys:

```text
azure-sql-server
azure-sql-database
azure-sql-user
azure-sql-password
```

## Write PySpark data to Snowflake

```python
def secret(key: str) -> str:
    return dbutils.secrets.get(scope="great-generator", key=key)


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
```

Install a Snowflake Spark Connector version compatible with the cluster's Spark and Scala versions when the runtime does not bundle it. Some recent Databricks runtimes also expose a bundled `snowflake` data source. Connector names, supported options, and serverless behavior are runtime-specific, so use the documentation for the deployed Databricks Runtime.

For production authentication, consider Snowflake key-pair authentication or External OAuth instead of a user password. The connector supports those approaches through its authentication options.

## Write PySpark data to Azure SQL with JDBC

```python
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
```

The Microsoft JDBC driver must be present on non-Databricks Spark clusters. The example uses encrypted transport and rejects an untrusted server certificate.

## Production notes

- Use `append` when rows should be added to an existing table.
- Treat `overwrite` carefully because connector behavior can recreate or truncate the target.
- Match Spark and database column types before large writes.
- Reduce DataFrame partitions when necessary to limit concurrent JDBC connections.
- Tune batch size and partitions against the target database, not only the Spark cluster.
- Grant only the database privileges required to write the target table.
- Prefer managed identity, service principal, OAuth, or key-pair authentication where the connector and organization support it.
- Confirm network access, firewall rules, private endpoints, DNS, and driver installation before troubleshooting the generator.

## Official references

- [Snowflake Spark Connector usage](https://docs.snowflake.com/en/user-guide/spark-connector-use)
- [Snowflake Spark Connector overview](https://docs.snowflake.com/en/user-guide/spark-connector-overview)
- [Databricks Spark data sources](https://learn.microsoft.com/azure/databricks/connect/spark-data-sources)
- [Databricks DataFrameWriter JDBC reference](https://learn.microsoft.com/en-us/azure/databricks/pyspark/reference/classes/dataframewriter/jdbc)

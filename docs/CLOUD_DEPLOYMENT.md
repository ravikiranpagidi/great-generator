# Cloud deployment guide

Great Generator is intentionally **storage-agnostic at the Spark layer**:

- pandas writes to local filesystem paths
- Spark writes preserve the URI you provide and let the cluster resolve it

That keeps the library portable across Databricks, EMR, Glue-style Spark runtimes, Synapse, Fabric-style Spark notebooks, and Dataproc without embedding cloud credentials in the package.

## Platform matrix

| Platform | Typical path | Usually needed outside the library |
| --- | --- | --- |
| Local pandas | `./synthetic/ecommerce` | local disk access |
| Databricks | `dbfs:/Volumes/catalog/schema/volume/...` | volume/external-location permissions |
| AWS Spark | `s3a://bucket/prefix/...` | S3A connector + IAM role/policy |
| Azure Spark | `abfss://container@account.dfs.core.windows.net/...` | ABFS connector + identity / ACLs |
| GCP Spark | `gs://bucket/prefix/...` | GCS connector + service account permissions |

## Recommended export pattern

```python
from great_generator import generate_domain

generate_domain(
    "banking",
    engine="spark",
    spark=spark,
    scale="large",
    output_path="s3a://demo-bucket/synthetic/banking",
    output_format="parquet",
    partition_by=["event_date"],
    writer_options={"compression": "snappy"},
    num_partitions=32,
    partition_strategy="repartition",
)
```

## Cloud examples

### Databricks

```python
generate_domain(
    "ecommerce",
    engine="spark",
    spark=spark,
    output_path="dbfs:/Volumes/catalog/schema/volume/synthetic/ecommerce",
    output_format="delta",
    partition_by=["event_date"],
    writer_options={"overwriteSchema": "true"},
)
```

### AWS

```python
generate_domain(
    "banking",
    engine="spark",
    spark=spark,
    output_path="s3a://demo-bucket/synthetic/banking",
    output_format="parquet",
    writer_options={"compression": "snappy"},
)
```

### Azure

```python
generate_domain(
    "banking",
    engine="spark",
    spark=spark,
    output_path="abfss://container@account.dfs.core.windows.net/synthetic/banking",
    output_format="delta",
)
```

### GCP

```python
generate_domain(
    "ecommerce",
    engine="spark",
    spark=spark,
    output_path="gs://demo-bucket/synthetic/ecommerce",
    output_format="parquet",
)
```

## Spark database destinations

Great Generator returns Spark DataFrames that can be written through database connectors already installed in the runtime.

| Destination | Recommended path |
|---|---|
| Snowflake | Snowflake Spark Connector using `net.snowflake.spark.snowflake` |
| Azure SQL or SQL Server | Spark JDBC using `com.microsoft.sqlserver.jdbc.SQLServerDriver` |

Use Databricks secret scopes or the platform's managed identity and OAuth facilities. Do not place credentials in source code.

Full examples are available in [SPARK_DATABASE_WRITES.md](SPARK_DATABASE_WRITES.md) and:

- `examples/02-write-generated-data/write_to_snowflake_spark.py`
- `examples/02-write-generated-data/write_to_azure_sql_jdbc.py`

## Export controls

| Option | Why it matters |
| --- | --- |
| `partition_by=["event_date"]` | produces query-friendly folder layouts |
| `writer_options={"compression": "snappy"}` | forwards Spark writer settings |
| `num_partitions=32` | lets you shape output-file parallelism |
| `partition_strategy="repartition"` | reshuffles to the requested count |
| `partition_strategy="coalesce"` | reduces partitions more cheaply when shrinking |

## Runtime checklist

Before blaming the library, verify the environment:

1. The path scheme is supported by the Spark runtime.
2. The cluster identity can read/write the target bucket/container/location.
3. Delta support is enabled when using `output_format="delta"`.
4. Network policies allow the cluster to reach the storage service.
5. The output path is suitable for the chosen format and overwrite behavior.
6. Database drivers or Spark connectors are installed and compatible with the runtime.
7. Database firewall, DNS, private endpoint, and network rules allow the cluster to connect.

## Deliberately not hidden inside the library

Great Generator does **not**:

- create cloud credentials
- attach storage accounts or buckets
- configure Unity Catalog, IAM, or service principals
- install Hadoop cloud connectors

Those are environment responsibilities. The library's job is to generate credible data and hand Spark a correct path.

## Next likely production additions

- optional catalog registration helpers
- save-as-table workflows for metastore-backed demos
- manifest generation and export summaries
- integration tests against real managed Spark runtimes

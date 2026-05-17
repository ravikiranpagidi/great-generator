# Cloud deployment guide

Enterprise Synth is intentionally **storage-agnostic at the Spark layer**:

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
from enterprise_synth import generate_domain

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

## Deliberately not hidden inside the library

Enterprise Synth does **not**:

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

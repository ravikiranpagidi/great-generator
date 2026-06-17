# Spark and Delta

Install Spark support only when needed:

```bash
pip install great-generator[spark]
pip install great-generator[delta]
```

Generate Spark DataFrames:

```python
data = generate_domain("banking", engine="spark", scale="large", realism="realistic")
transactions = data["transactions"]
```

In notebooks with an active Spark session, Great Generator can usually infer Spark. You may still pass `spark=spark` explicitly in scripts or jobs.

Write with native Spark APIs for maximum flexibility:

```python
transactions.write.mode("overwrite").parquet("s3://bucket/demo/banking/transactions")
transactions.write.format("delta").mode("overwrite").save("/mnt/lakehouse/banking_delta/transactions")
```

Convenience export:

```python
generate_domain(
    "banking",
    engine="spark",
    scale="large",
    output_path="s3://bucket/synthetic/banking",
    output_format="parquet",
    partition_by=["event_date"],
)
```

Storage path support depends on the Spark runtime and configured filesystem connectors:

- local paths in local Spark
- DBFS/Volumes in Databricks
- ADLS paths when Azure credentials/connectors are configured
- S3 paths when AWS credentials/connectors are configured
- GCS paths when GCP credentials/connectors are configured

Great Generator does not configure cloud IAM, secrets, mounts, or catalogs for you.

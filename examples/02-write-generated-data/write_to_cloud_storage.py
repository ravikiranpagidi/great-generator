"""Cloud writes require the matching filesystem connector and runtime authentication."""

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)

# Choose one path supported by your configured environment.
# df.to_parquet("s3://my-bucket/synthetic/customers.parquet")
# df.to_parquet("gs://my-bucket/synthetic/customers.parquet")
# df.to_parquet("abfss://container@account.dfs.core.windows.net/synthetic/customers.parquet")

print(df.head())

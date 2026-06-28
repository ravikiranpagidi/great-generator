"""Write a generated Pandas DataFrame to Parquet. PyArrow is installed by default."""

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "balance": "double"}, rows=100)
df.to_parquet("customers.parquet", index=False)

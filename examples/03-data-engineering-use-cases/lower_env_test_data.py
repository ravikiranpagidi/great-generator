"""Create a clean lower-environment customer table and a validation report."""

from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "email": "string",
    "date_of_birth": "date",
    "age": "int",
    "created_at": "timestamp",
    "updated_at": "timestamp",
}

df, report = generate_from_schema(schema, rows=5000, validate=True, return_report=True)
assert report["passed"], report["errors"]
df.to_parquet("lower_env_customers.parquet", index=False)

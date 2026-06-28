"""Generate realistic customer data from a plain Python dtype mapping."""

from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "email": "string",
    "balance": "float",
    "created_at": "datetime",
    "account_status": "string",
}

df = generate_from_schema(schema, rows=1000)
print(df.head())
df.to_csv("synthetic_customers.csv", index=False)

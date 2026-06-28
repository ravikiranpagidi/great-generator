"""Write a generated Pandas DataFrame to CSV."""

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)
df.to_csv("customers.csv", index=False)

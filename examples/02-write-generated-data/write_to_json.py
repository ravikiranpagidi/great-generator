"""Write newline-delimited JSON records from a generated Pandas DataFrame."""

from great_generator import generate_from_schema

df = generate_from_schema({"customer_id": "string", "customer_name": "string"}, rows=100)
df.to_json("customers.json", orient="records", lines=True, date_format="iso")

"""Generate data from supported compact DDL, not a full CREATE TABLE statement."""

from great_generator import generate_from_schema

schema = (
    "order_id string, customer_name string, email string, quantity int, "
    "unit_price double, total_amount double, order_date date, order_status string"
)

df = generate_from_schema(schema, rows=1000, domain="retail")
print(df.head())
df.to_parquet("synthetic_orders.parquet", index=False)

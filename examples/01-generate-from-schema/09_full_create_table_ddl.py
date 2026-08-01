"""Generate data from SQL CREATE TABLE DDL.

Run with:
    python examples/01-generate-from-schema/09_full_create_table_ddl.py
"""

from great_generator import generate_from_schema, parse_ddl

DDL = """
CREATE TABLE sales.customers (
  customer_id BIGINT PRIMARY KEY,
  customer_name STRING NOT NULL,
  email VARCHAR(120) UNIQUE,
  signup_date DATE
);

CREATE TABLE sales.orders (
  order_id BIGINT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  order_amount DECIMAL(12, 2),
  order_date DATE,
  CONSTRAINT fk_orders_customers
    FOREIGN KEY (customer_id) REFERENCES sales.customers(customer_id)
)
"""

contract = parse_ddl(DDL, dialect="databricks")
print("Contract fingerprint:", contract.fingerprint())
print("Tables:", list(contract.tables))

# One-table contracts return a DataFrame directly.
customer_contract = parse_ddl(
    """
    CREATE TABLE customers (
      customer_id BIGINT PRIMARY KEY,
      customer_name STRING,
      email STRING,
      signup_date DATE
    )
    """,
    dialect="databricks",
)
customers_df = generate_from_schema(customer_contract, rows=10)
print(customers_df.head())

# Multi-table contracts return a dictionary of DataFrames.
data = generate_from_schema(
    contract,
    rows={"sales.customers": 10, "sales.orders": 25},
    realism="placeholder",
)
print(data["sales.orders"].head())

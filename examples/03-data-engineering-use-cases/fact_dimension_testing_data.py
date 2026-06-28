"""Create custom related tables for fact and dimension join testing."""

from great_generator import generate_relational

data = generate_relational(
    tables={
        "dim_customer": {
            "schema": "customer_id int primary key, customer_name string, segment string",
            "rows": 1000,
        },
        "fact_order": {
            "schema": "order_id int primary key, customer_id int references dim_customer.customer_id, order_amount double, order_date date",
            "rows": 10000,
        },
    }
)

print(data["dim_customer"].head())
print(data["fact_order"].head())

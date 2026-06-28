"""Show semantic inference, business rules, validation, and Parquet output."""

from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "cust_name": "string",
    "email_addr": "string",
    "mobile_no": "string",
    "customer_age": "int",
    "annual_income": "double",
    "created_at": "timestamp",
    "account_status": "string",
}

df, report = generate_from_schema(
    schema,
    rows=1000,
    custom_rules={
        "customer_id": {"prefix": "CUST"},
        "customer_age": {"min": 18, "max": 85},
        "annual_income": {"min": 25000, "max": 250000},
        "account_status": {"values": ["Active", "Inactive", "Pending"]},
    },
    validate=True,
    return_report=True,
)

print(df.head())
print(report)
df.to_parquet("realistic_customers.parquet", index=False)

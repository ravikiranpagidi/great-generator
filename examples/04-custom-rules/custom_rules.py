"""Apply ranges, categories, weights, prefixes, dates, patterns, and null rates."""

from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "salary": "double",
    "status": "string",
    "created_at": "datetime",
    "campaign_code": "string",
    "secondary_email": "string",
}

df = generate_from_schema(
    schema,
    rows=5000,
    custom_rules={
        "customer_id": {"prefix": "CUST"},
        "customer_name": {"type": "full_name"},
        "age": {"min": 25, "max": 65},
        "salary": {"min": 60000, "max": 180000},
        "status": {"weighted_values": {"Active": 0.8, "Inactive": 0.2}},
        "created_at": {"start": "2023-01-01", "end": "2024-12-31"},
        "campaign_code": {"pattern": "CMP-{index:06d}"},
        "secondary_email": {"null_rate": 0.4},
    },
)

print(df.head())

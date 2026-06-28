"""Create schema-aligned source data for an ETL pipeline test."""

from great_generator import generate_from_schema

source_df = generate_from_schema(
    "transaction_id string, account_id string, transaction_amount double, transaction_date date, transaction_type string",
    rows=10000,
    domain="banking",
)

print(source_df.head())

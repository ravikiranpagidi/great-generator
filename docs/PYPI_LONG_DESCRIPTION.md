# great-generator

Generate realistic synthetic data from schema definitions for data engineering, testing, analytics, and lower environments.

## Why great-generator?

Data teams often know their schema but cannot copy production records into development, QA, SIT, UAT, sandbox, demo, or performance environments. Great Generator creates fake, non-production data from table-like schemas so teams can test pipelines, applications, dashboards, and data models without depending on production extracts.

## Main Feature: `generate_from_schema`

```python
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
```

Semantic field inference recognizes name-like fields, IDs, contact details, ages, dates, amounts, quantities, statuses, and common cross-field relationships.

## Next: Generate Related Tables

```python
from great_generator import generate_relational

data = generate_relational(
    tables={
        "customers": {
            "schema": "customer_id int primary key, customer_name string",
            "rows": 1000,
        },
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id, order_amount double",
            "rows": 5000,
        },
    }
)

customers_df = data["customers"]
orders_df = data["orders"]
```

Use `generate_relational` for your own connected tables. Use prebuilt domains later when you need ready-made demonstration data.

## Installation

```bash
pip install great-generator
pip install "great-generator[spark]"
pip install "great-generator[delta]"
```

## Supported Schema Inputs

- plain Python `{column: dtype}` mappings
- Pandas dtype mappings and DataFrames
- compact DDL strings such as `"id int, name string"`
- PySpark `StructType` and DataFrames
- Great Generator `TableSchema` and `DomainSchema` objects

Full SQL `CREATE TABLE`, JSON Schema, YAML schema profiles, SQLAlchemy, Pydantic, dataclass, and column-list inputs are planned rather than currently supported.

## Custom Rules

```python
df = generate_from_schema(
    schema,
    rows=1000,
    custom_rules={
        "customer_id": {"prefix": "CUST"},
        "age": {"min": 18, "max": 85},
        "balance": {"min": 0, "max": 100000},
        "account_status": {"values": ["Active", "Inactive", "Pending"]},
    },
)
```

## Write Output Anywhere Your DataFrame Supports

```python
df.to_csv("customers.csv", index=False)
df.to_json("customers.json", orient="records", lines=True)
df.to_parquet("customers.parquet", index=False)
```

Spark results support normal Spark writers for Parquet, Delta, Databricks tables, Fabric Lakehouse, S3, ADLS, GCS, DBFS, and catalog workflows when the runtime is configured.

## Real-World Uses

- lower-environment test data
- ETL and ELT validation
- QA, SIT, and UAT datasets
- lakehouse and warehouse testing
- API and application integration tests
- BI dashboard development
- data quality and edge-case testing
- prototypes, demos, research, and learning

## Prebuilt Domains

`generate_domain` provides ready-made related datasets for ecommerce, banking, healthcare, insurance, telecom, automotive, energy, manufacturing, logistics, media, public sector, hospitality, and SaaS. Use domains for demonstrations and learning; use `generate_from_schema` for your project's actual structures.

## Disclaimer

Great Generator creates synthetic data. It does not anonymize or transform production data and does not guarantee privacy, compliance, or statistical equivalence. Follow your organization's governance, privacy, security, and compliance requirements.

## Links

- [Documentation](https://ravikiranpagidi.github.io/great-generator/)
- [GitHub](https://github.com/ravikiranpagidi/great-generator)
- [Wiki](https://github.com/ravikiranpagidi/great-generator/wiki)
- [Issues](https://github.com/ravikiranpagidi/great-generator/issues)

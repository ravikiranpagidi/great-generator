# Great Generator

[![Tests](https://github.com/ravikiranpagidi/great-generator/actions/workflows/tests.yml/badge.svg)](https://github.com/ravikiranpagidi/great-generator/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/great-generator.svg)](https://pypi.org/project/great-generator/)
[![Python versions](https://img.shields.io/pypi/pyversions/great-generator.svg)](https://pypi.org/project/great-generator/)
[![PyPI downloads](https://img.shields.io/pypi/dm/great-generator.svg)](https://pypi.org/project/great-generator/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/ravikiranpagidi/great-generator?style=flat)](https://github.com/ravikiranpagidi/great-generator/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/ravikiranpagidi/great-generator)](https://github.com/ravikiranpagidi/great-generator/issues)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

## Generate Realistic Synthetic Data from Your Schema

**Have a schema but no safe test data?**

Use Great Generator to create realistic, fake, non-production data directly from your schema for development, QA, SIT, UAT, sandboxes, ETL validation, analytics, demos, and data engineering workflows.

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "email": "string",
    "address": "string",
    "city": "string",
    "state": "string",
    "created_at": "datetime",
    "account_status": "string",
}

df = generate_from_schema(schema=schema, rows=1000)

print(df.head())
```

Great Generator is built for teams that already know their schema but cannot use production data in lower environments.

> Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records. Always follow your organization's privacy, security, governance, and compliance policies.

## Problem Statement

Real projects need production-like data outside production. Copying production records into development, QA, SIT, UAT, sandbox, demo, or performance-testing environments is often restricted because of privacy, security, PII, PHI, PCI, internal policy, or data governance concerns.

Teams still need realistic data to:

- test ingestion and transformation pipelines
- validate schemas, joins, and business rules
- exercise APIs and application services
- build dashboards and analytics models
- test data quality controls and failure paths
- run demonstrations, prototypes, and performance checks
- onboard developers without sharing sensitive records

Great Generator turns table-like schema definitions into usable Pandas or Spark DataFrames. You keep control of where those DataFrames are written.

## Why Schema-Based Synthetic Data Matters

Most engineering teams do not begin with a blank domain. They already have a contract: column names, data types, a DataFrame, a Spark schema, or a table definition. `generate_from_schema` uses that contract and semantic field inference to generate values that are more useful than type-correct placeholders.

For example, these fields are recognized as name-like fields rather than generic strings:

- `customer_name`
- `cust_name`
- `employee_name`
- `emp_name`
- `member_name`
- `patient_name`

The same semantic layer recognizes IDs, email addresses, phone numbers, addresses, ages, dates, monetary values, quantities, statuses, and common lifecycle relationships.

## Who This Library Is For

- **Data engineers** testing ETL, ELT, Spark, Delta, and lakehouse pipelines
- **QA engineers** creating repeatable positive, negative, and edge-case datasets
- **Application developers** testing APIs, databases, and integration contracts
- **Analytics engineers** validating models, joins, dashboards, and SQL transformations
- **Platform teams** provisioning safe lower-environment datasets
- **Performance engineers** creating environment-appropriate volume tests
- **Researchers and ML engineers** building reproducible prototypes without production records
- **Students, speakers, and educators** using ready-made domain packs for learning and demos

## What You Can Do

- generate a realistic DataFrame from a schema
- use plain Python mappings, Pandas schemas, compact DDL, or PySpark schemas
- apply per-column ranges, categories, prefixes, patterns, weights, date windows, and null rates
- inspect the semantic generation plan before generating data
- validate generated values and cross-field consistency
- return Pandas or Spark DataFrames for downstream writes
- generate custom relational parent-child tables with valid keys
- use prebuilt enterprise domain packs
- simulate CDC records, anomalies, SCD2 history, dimensional models, and Data Vault models
- export domain datasets to CSV, JSON, Parquet, and Delta

## Installation

```bash
pip install great-generator
```

Optional Spark and Delta dependencies:

```bash
pip install "great-generator[spark]"
pip install "great-generator[delta]"
```

Install with a hyphen and import with an underscore:

```python
import great_generator
```

The base package supports Python 3.9 and later and installs Pandas, NumPy, PyArrow, and Faker. PySpark and Delta Lake remain optional.

## Quick Start: Generate Data from Schema

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "email": "string",
    "address": "string",
    "city": "string",
    "state": "string",
    "created_at": "datetime",
    "account_status": "string",
}

df = generate_from_schema(schema=schema, rows=1000)
```

The default `realism="realistic"` mode produces name-like, email-like, address-like, date-aware, and business-oriented values when field semantics are recognized.

Example shape:

```text
customer_id  customer_name  age  email                         city       state  account_status
CUST000001   Ava Johnson    34   ava.johnson@example.com       Austin     Texas       Active
CUST000002   Liam Patel     42   liam.patel@example.com        Seattle    Washington  Pending
```

Exact values vary. Pass an optional `seed` only when your test or experiment needs repeatable output.

## Supported Schema Input Types

The table below reflects the current implementation, not the long-term roadmap.

| Schema Input Type | Example | Best For | Status |
|---|---|---|---|
| Plain Python mapping | `{"name": "string", "age": "int"}` | Fast schema-based generation | **Supported** |
| Rich mapping with inline metadata | `{"age": {"type": "int", "min": 18}}` | Embedded business rules | **Partially supported** through separate `custom_rules`; inline metadata is planned |
| Pandas dtype mapping | `df.dtypes.to_dict()` | Pandas and notebook workflows | **Supported** |
| Pandas DataFrame schema | empty or populated `DataFrame` | Preserve Pandas column dtypes | **Supported** |
| Compact DDL string | `"id int, name string"` | SQL-like and Spark-style definitions | **Supported** |
| Full SQL `CREATE TABLE` DDL | `CREATE TABLE ...` | Database and warehouse teams | **Planned** |
| PySpark `StructType` | `StructType([...])` | Databricks, Fabric, Synapse, EMR, Spark | **Supported** for common scalar types; nested complex generation is limited |
| PySpark DataFrame | empty or existing Spark DataFrame | Infer schema and Spark session | **Supported** |
| `TableSchema` | library schema object | Typed library extensions | **Supported** |
| `DomainSchema` | library domain metadata | Multi-table schema generation | **Supported** |
| JSON Schema | `{"type": "object", "properties": ...}` | APIs and data contracts | **Planned** |
| YAML schema profile | `customer_schema.yml` | Reusable schema configurations | **Planned** |
| Column-name list | `["name", "age", "email"]` | Very fast prototypes | **Planned** |
| SQLAlchemy model | ORM class | Backend and database teams | **Planned** |
| Pydantic model | `BaseModel` class | API contract workflows | **Planned** |
| Dataclass | typed Python dataclass | Typed Python workflows | **Planned** |

JSON, TOML, and simple YAML are currently supported for **dataset recipes** through `generate_from_recipe`, not as schema inputs to `generate_from_schema`.

## Supported Schema Examples

### 1. Plain Python Dictionary

```python
from great_generator import generate_from_schema

schema = {
    "employee_id": "string",
    "emp_name": "string",
    "email": "string",
    "employee_age": "int",
    "salary": "float",
    "hire_date": "date",
    "employment_status": "string",
}

employees = generate_from_schema(schema, rows=500, domain="hr")
```

### 2. Compact DDL String

Compact column definitions are supported. A full `CREATE TABLE` statement is not yet accepted.

```python
from great_generator import generate_from_schema

customers = generate_from_schema(
    "customer_id string, customer_name string, age int, email string, balance decimal(12,2), created_at timestamp",
    rows=1000,
)
```

Spark-style `struct<...>` text is also accepted:

```python
df = generate_from_schema(
    "struct<customer_id:string,customer_name:string,age:int,balance:double>",
    rows=1000,
)
```

### 3. Pandas dtype Mapping

```python
import pandas as pd

from great_generator import generate_from_schema

sample_df = pd.DataFrame(
    {
        "customer_id": pd.Series(dtype="string"),
        "customer_name": pd.Series(dtype="string"),
        "age": pd.Series(dtype="int64"),
        "balance": pd.Series(dtype="float64"),
        "created_at": pd.Series(dtype="datetime64[ns]"),
    }
)

df = generate_from_schema(sample_df.dtypes.to_dict(), rows=1000)
```

### 4. Pandas DataFrame Schema

Pass the DataFrame itself when you want Great Generator to infer and cast back to its dtypes:

```python
df = generate_from_schema(sample_df, rows=1000)
```

The input rows are not copied. The DataFrame is used as a schema source.

### 5. PySpark StructType

```python
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from great_generator import generate_from_schema

schema = StructType(
    [
        StructField("customer_id", StringType(), False),
        StructField("customer_name", StringType(), True),
        StructField("age", IntegerType(), True),
        StructField("email", StringType(), True),
        StructField("balance", DoubleType(), True),
        StructField("created_at", TimestampType(), True),
    ]
)

spark_df = generate_from_schema(schema=schema, rows=1000, engine="spark")
```

In a notebook or cluster with an active Spark session, `engine="spark"` resolves that session automatically. You can also pass `spark=spark` explicitly when no active session can be discovered.

Current limitation: single-table Spark schema generation creates values locally and then creates a Spark DataFrame. Use environment-appropriate row counts. Native distributed generation for this API is planned; the built-in Spark domain engine already uses Spark-native generation paths.

### 6. PySpark DataFrame Schema

```python
empty_spark_df = spark.createDataFrame([], schema)

spark_df = generate_from_schema(empty_spark_df, rows=1000)
```

The input DataFrame supplies both the schema and Spark session. The returned value is a Spark DataFrame and supports normal Spark writers.

### 7. Library TableSchema

```python
from great_generator import generate_from_schema
from great_generator.schemas.models import ColumnSpec, TableSchema

schema = TableSchema(
    name="customers",
    columns=(
        ColumnSpec("customer_id", "string", nullable=False),
        ColumnSpec("customer_name", "string"),
        ColumnSpec("email", "string"),
        ColumnSpec("age", "int"),
    ),
    primary_key="customer_id",
)

df = generate_from_schema(schema, rows=1000)
```

## Rich Business Rules with `custom_rules`

Inline rich schema metadata is planned. Today, keep the type mapping simple and pass business rules separately:

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "email": "string",
    "balance": "float",
    "account_status": "string",
    "created_at": "datetime",
}

custom_rules = {
    "customer_id": {"prefix": "CUST"},
    "customer_name": {"type": "full_name"},
    "age": {"min": 18, "max": 85},
    "balance": {"min": 0, "max": 100000},
    "account_status": {
        "weighted_values": {
            "Active": 0.70,
            "Inactive": 0.15,
            "Pending": 0.10,
            "Closed": 0.05,
        }
    },
    "created_at": {"start": "2023-01-01", "end": "2024-12-31"},
}

df = generate_from_schema(
    schema=schema,
    rows=5000,
    custom_rules=custom_rules,
)
```

Currently supported rule keys include:

| Rule | Purpose |
|---|---|
| `type` | Override inferred semantic type, such as `full_name` |
| `min`, `max` | Numeric or age bounds |
| `values` | Allowed categorical values |
| `weighted_values` | Weighted categories as a mapping or value-weight pairs |
| `prefix` | Prefix generated ID-like fields |
| `pattern` | Format strings using `{index}` |
| `start`, `end` | Date generation window for date-like fields |
| `null_rate` | Opt-in null rate for non-ID fields |
| `unique` | Validation expectation; ID-like fields are generated uniquely by default |

## Realistic Mode

`realism="realistic"` is the default for `generate_from_schema`.

| Column Name | Data Type | Typical Behavior |
|---|---|---|
| `customer_name`, `cust_name` | string | realistic full name |
| `emp_name`, `employee_name` | string | realistic employee name |
| `age`, `employee_age` | int | age-appropriate range |
| `email`, `email_id` | string | email-like value |
| `phone`, `mobile_no` | string | phone-like value |
| `address`, `city`, `state` | string | address-oriented value |
| `customer_id` | string | unique prefixed identifier |
| `amount`, `salary`, `balance` | numeric | bounded business-oriented amount |
| `created_at` | date or timestamp | historical value by default |
| `updated_at` | date or timestamp | same as or after `created_at` |
| `date_of_birth`, `dob` | date | non-future birth date |
| `status`, `order_status` | string | recognizable status category |

Realistic mode is designed to avoid obvious placeholder behavior such as `customer_name_1`, ages outside expected human ranges, future historical dates, or `updated_at` before `created_at`.

Use placeholder mode when simple deterministic values are more useful than semantic realism:

```python
df = generate_from_schema(schema, rows=20, realism="placeholder")
```

`realism="basic"` and `realism="simple"` are aliases for placeholder mode. `realism="clean"` is an alias for realistic mode.

## Data Quality and Edge Cases

Schema-generated data aims to be:

- fake and non-production
- schema-aligned and type-correct
- semantically meaningful where fields are recognized
- logically consistent for supported cross-field rules
- easy to validate and write downstream

Supported clean-data behaviors include:

- name and email consistency when first and last name fields are present
- realistic age ranges
- age and date-of-birth alignment
- historical dates for fields that should not be in the future
- `updated_at >= created_at`
- `end_date >= start_date`
- `delivery_date >= order_date`
- status-aware nulls for unpaid, undelivered, active-employment, and open-account states
- unique non-null ID-like fields
- positive quantities
- total calculations from quantity, price, discount, and tax where recognized

### Explain the Generation Plan

Inspect semantic inference before generating data:

```python
from great_generator import explain_generation_plan

plan = explain_generation_plan(
    {
        "cust_nm": "string",
        "email_addr": "string",
        "txn_amt": "double",
        "created_ts": "timestamp",
    }
)

for field in plan["fields"]:
    print(field["column"], field["semantic_type"], field["confidence"])
```

### Validate Generated Data

```python
from great_generator import generate_from_schema, validate_generated_data

df = generate_from_schema(schema, rows=1000, custom_rules=custom_rules)
report = validate_generated_data(df, schema=schema, rules=custom_rules)

assert report["passed"], report["errors"]
```

Or return data and a report together:

```python
df, report = generate_from_schema(
    schema,
    rows=1000,
    validate=True,
    return_report=True,
)
```

Validation is local for Pandas results. Spark results currently return a note rather than collecting the distributed DataFrame for local validation.

## Writing Generated Data to Different Targets

Great Generator returns DataFrames so you can use the writer already trusted by your application, notebook, database driver, or Spark platform.

### Write Pandas Data to CSV, JSON, or Parquet

```python
df.to_csv("customers.csv", index=False)
df.to_json("customers.json", orient="records", lines=True)
df.to_parquet("customers.parquet", index=False)
```

### Write a Spark DataFrame to Parquet or Delta Lake

```python
spark_df.write.mode("overwrite").parquet("/data/synthetic/customers")

spark_df.write.format("delta").mode("overwrite").save("/mnt/delta/customers")
```

Delta support depends on a Delta-enabled Spark runtime or the `delta-spark` extra.

### Write to a Databricks Table

```python
spark_df.write.format("delta").mode("overwrite").saveAsTable(
    "dev.synthetic_customers"
)
```

Typical Databricks paths include `dbfs:/...` and `/Volumes/<catalog>/<schema>/<volume>/...`, depending on workspace configuration.

### Write to a Microsoft Fabric Lakehouse

```python
spark_df.write.format("delta").mode("overwrite").save(
    "Tables/synthetic_customers"
)
```

Use the path conventions and permissions configured for your Fabric workspace and lakehouse.

### Write PySpark or Databricks Data to Snowflake

For Spark workloads, use the Snowflake Spark Connector rather than collecting data into Pandas:

```python
def secret(key: str) -> str:
    return dbutils.secrets.get(scope="great-generator", key=key)


snowflake_options = {
    "sfURL": secret("snowflake-url"),
    "sfUser": secret("snowflake-user"),
    "sfPassword": secret("snowflake-password"),
    "sfDatabase": secret("snowflake-database"),
    "sfSchema": secret("snowflake-schema"),
    "sfWarehouse": secret("snowflake-warehouse"),
    "sfRole": secret("snowflake-role"),
}

(
    spark_df.write.format("net.snowflake.spark.snowflake")
    .options(**snowflake_options)
    .option("dbtable", "SYNTHETIC_CUSTOMERS")
    .mode("overwrite")
    .save()
)
```

Install a Snowflake Spark Connector version compatible with the cluster's Spark and Scala versions when it is not bundled by the runtime.

For local Pandas workflows, SQLAlchemy remains an option:

```python
import os
from sqlalchemy import create_engine

engine = create_engine(os.environ["SNOWFLAKE_SQLALCHEMY_URL"])
df.to_sql("SYNTHETIC_CUSTOMERS", con=engine, if_exists="replace", index=False)
```

Install and configure the appropriate Snowflake SQLAlchemy connector separately.

### Write PySpark or Databricks Data to Azure SQL with JDBC

```python
server = dbutils.secrets.get(scope="great-generator", key="azure-sql-server")
database = dbutils.secrets.get(scope="great-generator", key="azure-sql-database")
jdbc_url = (
    f"jdbc:sqlserver://{server}:1433;"
    f"databaseName={database};"
    "encrypt=true;"
    "trustServerCertificate=false;"
    "hostNameInCertificate=*.database.windows.net;"
    "loginTimeout=30;"
)

(
    spark_df.coalesce(4)
    .write.format("jdbc")
    .mode("overwrite")
    .option("url", jdbc_url)
    .option("dbtable", "dbo.synthetic_customers")
    .option("user", dbutils.secrets.get(scope="great-generator", key="azure-sql-user"))
    .option("password", dbutils.secrets.get(scope="great-generator", key="azure-sql-password"))
    .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")
    .option("batchsize", "1000")
    .save()
)
```

The Microsoft SQL Server JDBC driver must be available to the Spark runtime. Limit partitions so the cluster does not overwhelm Azure SQL with concurrent connections.

For local Pandas workflows, SQLAlchemy remains an option:

```python
import os
from sqlalchemy import create_engine

engine = create_engine(os.environ["SQLSERVER_SQLALCHEMY_URL"])
df.to_sql("synthetic_customers", con=engine, if_exists="replace", index=False)
```

See [Spark database writes](docs/SPARK_DATABASE_WRITES.md) for connector setup, secrets, authentication alternatives, and production notes.

### Write to PostgreSQL

```python
import os
from sqlalchemy import create_engine

engine = create_engine(os.environ["POSTGRESQL_SQLALCHEMY_URL"])
df.to_sql("synthetic_customers", con=engine, if_exists="replace", index=False)
```

### Write to SQLite

```python
from sqlalchemy import create_engine

engine = create_engine("sqlite:///synthetic_data.db")
df.to_sql("synthetic_customers", con=engine, if_exists="replace", index=False)
```

### Write to Cloud Storage

Pandas can write cloud URLs when the matching filesystem package and authentication are configured:

```python
df.to_parquet("s3://my-bucket/synthetic/customers.parquet")
df.to_parquet("gs://my-bucket/synthetic/customers.parquet")
df.to_parquet(
    "abfss://container@account.dfs.core.windows.net/synthetic/customers.parquet"
)
```

Spark uses its runtime connectors and identity configuration:

```python
spark_df.write.mode("overwrite").parquet("s3a://my-bucket/synthetic/customers")
spark_df.write.mode("overwrite").parquet("gs://my-bucket/synthetic/customers")
spark_df.write.mode("overwrite").parquet(
    "abfss://container@account.dfs.core.windows.net/synthetic/customers"
)
```

Great Generator does not configure credentials, filesystem connectors, IAM roles, managed identities, service accounts, secrets, catalogs, or external locations. Use environment variables, managed identities, workload identities, or secret managers. Do not hardcode credentials.

## Real-World Data Engineering Use Cases

### Lower-Environment Data Generation

Generate fake but realistic customer, account, order, claim, employee, transaction, or operational data for dev, QA, SIT, UAT, sandbox, and demo environments.

### ETL and ELT Pipeline Testing

Test ingestion, type handling, transformations, schema checks, data quality rules, and downstream loads without waiting for production extracts.

### Lakehouse and Warehouse Testing

Return DataFrames that can be written to Delta Lake, Databricks, Microsoft Fabric, Snowflake, Synapse, BigQuery, Redshift, PostgreSQL, SQL Server, or other supported targets using their normal connectors.

### Data Model Validation

Use `generate_from_schema` for individual tables or `generate_relational` for related tables. Test keys, joins, null behavior, facts, dimensions, and lifecycle logic.

### Dashboard and BI Testing

Create realistic datasets for Power BI, Tableau, Looker, notebooks, and internal analytics applications when production data cannot be shared.

### API and Application Testing

Generate DataFrame-backed payloads for API contracts, application services, integration tests, and database fixtures.

### Performance and Volume Testing

Great Generator is designed to support small to large datasets. It can generate one row to millions of rows depending on memory, compute, schema complexity, engine, and environment. For very large datasets, use chunking, test carefully, or use Spark-native domain generation. Do not treat a row-count setting as a performance guarantee.

### AI and ML Experimentation

Create starter datasets for feature engineering, model prototyping, tutorials, and demonstrations when real data is unavailable. Generated data is not a substitute for representative training data or formal statistical synthesis.

## `generate_from_schema` API Reference

Current signature:

```python
generate_from_schema(
    schema,
    rows=100,
    seed=None,
    engine="auto",
    spark=None,
    table_name="sample",
    realism="realistic",
    domain=None,
    custom_rules=None,
    realistic=None,
    validate=False,
    return_report=False,
)
```

| Parameter | Description |
|---|---|
| `schema` | Supported schema object or definition |
| `rows` | Integer row count for one table; mapping or integer for `DomainSchema` |
| `seed` | Optional integer for reproducible generation |
| `engine` | `"auto"`, `"pandas"`, or `"spark"` |
| `spark` | Optional SparkSession when it cannot be inferred or discovered |
| `table_name` | Logical name used for a single-table schema |
| `realism` | `"realistic"` or `"placeholder"`, including documented aliases |
| `domain` | Optional semantic preset such as `banking`, `retail`, `healthcare`, `insurance`, `hr`, or `education` |
| `custom_rules` | Per-column semantic, range, category, pattern, date, prefix, and null rules |
| `realistic` | Backward-compatible boolean override; prefer `realism` in new code |
| `validate` | Run post-generation validation where supported |
| `return_report` | Return `(data, report)` instead of only data |

Return behavior:

- Python mappings, compact DDL, Pandas inputs, and `TableSchema` return a Pandas DataFrame by default.
- `engine="spark"`, an explicit SparkSession, or a PySpark DataFrame returns a Spark DataFrame.
- A PySpark `StructType` returns Spark when an active or explicit SparkSession is available; otherwise auto mode resolves to Pandas.
- `DomainSchema` returns a dictionary of table-name to DataFrame.

## `generate_domain`: Prebuilt Learning and Demo Datasets

Use domain packs when you want a complete ready-made dataset rather than data shaped around your own schema.

```python
from great_generator import generate_domain, list_domains

print(list_domains())

data = generate_domain("ecommerce", scale="small")

customers = data["customers"]
orders = data["orders"]
order_items = data["order_items"]
```

Available domain packs include ecommerce, banking, healthcare, insurance, telecom, automotive, energy, manufacturing, logistics, media, public sector, hospitality, and SaaS.

Domain packs include relationships and domain behaviors. They are useful for demonstrations, tutorials, SQL learning, architecture prototypes, benchmarks, and examples where the user does not already have a schema.

## `generate_from_schema` vs `generate_domain`

| Use Case | Recommended Function | Why |
|---|---|---|
| I already have a table schema | `generate_from_schema` | Uses your actual structure |
| I need lower-environment test data | `generate_from_schema` | Aligns generated fields to the expected contract |
| I need data for ETL or QA testing | `generate_from_schema` | Matches pipeline input columns and types |
| I have several related custom tables | `generate_relational` | Adds primary-key and foreign-key relationships |
| I need a quick enterprise demo dataset | `generate_domain` | Prebuilt related tables are immediately available |
| I am learning SQL or data modeling | `generate_domain` | Domain packs provide understandable examples |
| I need data for my project's schema | `generate_from_schema` | This is the primary industry workflow |

For industry projects, start with `generate_from_schema`. For ready-made learning and demos, use `generate_domain`.

## Custom Relational Schemas

```python
from great_generator import generate_relational

data = generate_relational(
    tables={
        "customers": {
            "schema": "customer_id int primary key, customer_name string, email string",
            "rows": 1000,
        },
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id, order_amount double, order_date date",
            "rows": 5000,
        },
    },
    engine="pandas",
)

customers_df = data["customers"]
orders_df = data["orders"]
```

The dictionary output keeps each table as a DataFrame. Write each table using Pandas, Spark, database, or cloud APIs without forcing a storage decision inside the generator.

## Additional Capabilities

| Capability | API |
|---|---|
| CDC records | `generate_cdc` |
| Controlled anomalies | `generate_domain(..., anomalies=...)` |
| SCD2 history | `generate_history` |
| Dimensional facts and dimensions | `generate_dimensional_model` |
| Data Vault hubs, links, and satellites | `generate_data_vault_model` |
| JSON, TOML, and simple YAML recipes | `generate_from_recipe` |
| CSV, JSON, Parquet, Delta convenience exports | `export_data` or `generate_domain(..., output_format=...)` |

See the [documentation site](https://ravikiranpagidi.github.io/great-generator/), [Wiki](https://github.com/ravikiranpagidi/great-generator/wiki), and [`docs/`](docs/) for focused guides.

## Planned Schema Input Types

The following are roadmap items and are not accepted by `generate_from_schema` today:

- inline rich schema metadata
- full dialect-aware SQL `CREATE TABLE` parsing
- JSON Schema and JSON Schema files
- YAML schema profiles
- column-name-only lists with type inference
- SQLAlchemy models
- Pydantic models
- Python dataclasses
- richer nested Spark and JSON structures
- Spark-native distributed generation for arbitrary schemas

Tracking these as explicit roadmap items keeps the current API trustworthy while leaving a clear path for contributors.

## Limitations

- Generated data is synthetic and may not reproduce every rule or distribution in a real system.
- The library does not provide privacy guarantees or transform production data.
- Semantic inference depends on recognizable field names and declared data types. Use `custom_rules` when intent is ambiguous.
- Single-table Spark schema generation currently creates values locally before creating a Spark DataFrame.
- Nested complex Spark types have limited generation support.
- Cloud storage and database access require separate connectors, credentials, permissions, and runtime configuration.
- Domain packs are engineered simulations, not statistical models fitted to source data.

## Roadmap

Priorities include richer schema ingestion, nested contracts, native distributed schema generation, stronger generation manifests and quality reports, additional domain packs, streaming output, and expanded lifecycle behavior. See [`docs/OPEN_SOURCE_STRATEGY.md`](docs/OPEN_SOURCE_STRATEGY.md) and the [Wiki roadmap](https://github.com/ravikiranpagidi/great-generator/wiki/Roadmap).

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), run the test suite, and include focused tests for user-visible behavior.

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
black --check .
```

## Author

Created and maintained by Ravi Kiran Pagidi.

- [PyPI](https://pypi.org/project/great-generator/)
- [GitHub](https://github.com/ravikiranpagidi/great-generator)
- [Documentation](https://ravikiranpagidi.github.io/great-generator/)
- [Wiki](https://github.com/ravikiranpagidi/great-generator/wiki)
- [Contact](mailto:ravikiran.pagidi@gmail.com)

## Disclaimer

Great Generator helps teams create fake, non-production synthetic data. It does not guarantee compliance, privacy preservation, statistical equivalence, or fitness for a regulated use case. Review generated data and follow your organization's data governance, privacy, security, and compliance requirements.

## License

[MIT](LICENSE)

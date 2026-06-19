# Advanced Capabilities

Great Generator is built around a simple idea: generate systems, not isolated fake values.
This guide covers the advanced capabilities added for richer demos, quality benchmarks, data modeling education, and lakehouse proof-of-concepts.

All features on this page keep the core lightweight. They use the existing pandas, numpy, pyarrow, and Faker based runtime unless Spark is explicitly requested.

## What is included now

| Capability | API | Output |
| --- | --- | --- |
| Labeled anomaly ground truth | `generate_domain(..., return_labels=True)` | Normal generated tables plus `_anomaly_labels` |
| SCD2 temporal history | `generate_domain(..., history="scd2")`, `generate_history(...)` | Current-state tables plus `<table>_history`, or one history table |
| CLI | `great-generator ...` | Files written to CSV, JSON, Parquet, or Delta where supported |
| Dataset recipes | `generate_from_recipe(path)`, `great-generator run recipe.yaml` | Reproducible generated datasets from JSON, TOML, or simple YAML |
| Dimensional models | `generate_dimensional_model(...)` | Fact and dimension tables |
| Data Vault models | `generate_data_vault_model(...)` | Hubs, links, satellites, and model metadata |

## Labeled anomaly ground truth

Use this when you want dirty data plus an answer key for validation, data-quality demos, or anomaly detection benchmarks.

```python
from great_generator import generate_domain

data = generate_domain(
    "ecommerce",
    scale="small",
    anomalies={
        "null_rate": 0.02,
        "duplicate_rate": 0.01,
        "orphan_fk_rate": 0.001,
        "invalid_status_rate": 0.005,
    },
    return_labels=True,
)

orders = data["orders"]
labels = data["_anomaly_labels"]

print(labels.head())
```

The label table includes:

- `table`
- `row_index`
- `primary_key`
- `primary_key_value`
- `column`
- `anomaly_type`
- `original_value`
- `corrupted_value`

By default, anomalies are not injected. Labels appear only when `return_labels=True`.

## SCD2 temporal history

Use this for dbt snapshots, Delta merge demos, time-travel examples, dimensional history, and audit-style tests.

```python
from great_generator import generate_domain, generate_history

banking = generate_domain(
    "banking",
    scale="small",
    history="scd2",
    history_window="2y",
)

customers_current = banking["customers"]
customers_history = banking["customers_history"]

single_history = generate_history(
    "ecommerce",
    table="customers",
    scale="small",
    history_window="180d",
)
```

History tables include:

- `scd_id`
- all source columns
- `effective_from`
- `effective_to`
- `is_current`

The generated history guarantees at most one current row per natural key and avoids overlapping validity intervals.

## Command line interface

The CLI helps notebook users, shell users, and demo builders generate data without writing Python code.

```bash
great-generator list-domains
great-generator describe banking
great-generator describe ecommerce --json

great-generator gen banking   --scale medium   --realism realistic   --out ./data/banking   --format parquet
```

The CLI writes table-per-folder outputs. Python users can still prefer the DataFrame-first API when they want to decide how to write the output themselves.

## Dataset recipes

Recipes make datasets reproducible and citable. They are useful for demos, blog posts, papers, training labs, and benchmark runs.

### YAML recipe

```yaml
kind: domain
domain: banking
engine: pandas
scale: small
realism: realistic
anomalies:
  null_rate: 0.01
  duplicate_rate: 0.005
output:
  path: ./generated/banking
  format: parquet
```

Run it from Python:

```python
from great_generator import generate_from_recipe

data = generate_from_recipe("banking_recipe.yaml")
```

Run it from the CLI:

```bash
great-generator run banking_recipe.yaml
```

JSON and TOML recipes are supported too. The built-in YAML parser intentionally supports simple key/value recipe files so the core can remain dependency-free. For complex YAML features, use JSON or TOML.

## Dimensional model generation

Use this when you want generated facts and dimensions for SQL learning, BI demos, dbt examples, star-schema teaching, or analytics engineering tests.

```python
from great_generator import generate_dimensional_model

model = generate_dimensional_model("ecommerce", scale="small")

customers = model["dim_customer"]
products = model["dim_product"]
sales = model["fact_sales"]
```

Ecommerce currently produces:

- `dim_customer`
- `dim_product`
- `dim_date`
- `fact_sales`
- `fact_payments`
- `_model_metadata`

Banking currently produces:

- `dim_customer`
- `dim_account`
- `dim_merchant`
- `dim_date`
- `fact_transactions`
- `fact_fraud`
- `_model_metadata`

Facts use keys from the generated dimensions. Other domains use a generic fact/dimension split based on table names so users still get a useful starting point.

### Spark dimensional output

```python
from great_generator import generate_dimensional_model

model = generate_dimensional_model(
    "banking",
    engine="spark",
    scale="medium",
)

model["fact_transactions"].write.mode("overwrite").parquet("s3://my-bucket/demo/fact_transactions")
```

In most Spark notebooks, the active SparkSession can be detected. If your environment does not expose an active session, pass `spark=spark` explicitly.

## Data Vault model generation

Use this when you want generated hubs, links, and satellites for lakehouse modeling demos, Data Vault training, lineage conversations, and architecture proof-of-concepts.

```python
from great_generator import generate_data_vault_model

vault = generate_data_vault_model("ecommerce", scale="small")

hub_customer = vault["hub_customer"]
hub_order = vault["hub_order"]
link_order_customer = vault["link_order_customer"]
sat_customer_details = vault["sat_customer_details"]
```

The generator derives:

- one hub per keyed domain table
- one satellite per keyed domain table
- one link per foreign-key relationship
- stable hash keys
- `load_date`
- `record_source`
- `_model_metadata`

The Data Vault output is relational and generated from the same domain schema used by normal domain generation.

## DataFrame-first design

Advanced model functions return a dictionary of DataFrames. That is intentional.

```python
model = generate_dimensional_model("banking", scale="small")

# Pandas write choice
model["fact_transactions"].to_parquet("fact_transactions.parquet")

# Spark write choice when engine="spark"
# model["fact_transactions"].write.format("delta").mode("overwrite").save(path)
```

This keeps Great Generator flexible. Users can write to CSV, JSON, Parquet, Delta, database tables, managed catalog tables, object storage, or any destination their pandas or Spark runtime supports.

## Planned advanced layers

The heavier layers are intentionally RFC-first. See `docs/rfcs/` for the design notes before implementation:

- schema-source ingestion
- streaming generation
- quality integrations and pytest fixtures
- medallion plus catalog-native output
- vector and embedding columns
- RAG document generation
- fit-from-sample statistical fidelity
- differential privacy on the fit path
- ML training data with drift
- provenance and freshness propagation

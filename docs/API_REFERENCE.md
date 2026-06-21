# API Reference

## `generate_domain(...)`

Generates a built-in enterprise domain pack and returns a dictionary of DataFrames.

Important parameters:

- `domain`: built-in domain name, for example `banking`, `ecommerce`, `healthcare`, `telecom`, or `saas`
- `engine`: `"pandas"` or `"spark"`
- `scale`: `"tiny"`, `"small"`, `"medium"`, or `"large"`
- `rows`: optional per-table row-count overrides
- `realism`: `"realistic"` or `"placeholder"`
- `seed`: optional integer for reproducible output
- `anomalies`: opt-in data quality issues
- `return_labels`: optional pandas anomaly label table named `_anomaly_labels`
- `history`: optional `"scd2"` history generation for pandas domains
- `output_path` and `output_format`: optional convenience exports

```python
data = generate_domain("ecommerce", scale="small", realism="realistic", seed=42)
```

## `generate_from_schema(...)`

Generates a single DataFrame or domain-shaped dictionary from schema metadata. Single-table schema generation is semantic-field based: it normalizes column names, expands common abbreviations, combines column-name intent with data type, and generates realistic values where possible.

Supported inputs:

- compact DDL strings such as `"id int, name string"`
- Python mappings such as `{ "customer_name": "string", "age": "int" }`
- empty pandas DataFrames with dtypes
- PySpark `StructType`
- PySpark DataFrames
- `TableSchema`
- `DomainSchema`

```python
df = generate_from_schema(
    {"customer_name": "string", "email_id": "string", "age": "int"},
    rows=100,
    domain="retail",
)
```

Important optional parameters:

- `domain`: optional preset such as `banking`, `retail`, `healthcare`, `insurance`, `hr`, or `education`
- `custom_rules`: per-column overrides for values, min/max ranges, semantic type, prefixes, uniqueness, and date ranges
- `realistic`: set `False` for older placeholder-style values
- `realism`: string mode, `"realistic"` or `"placeholder"`

## `generate_relational(...)`

Generates user-defined parent/child tables with valid primary-key and foreign-key relationships.

```python
data = generate_relational(
    tables={
        "customers": {"schema": "customer_id int primary key, customer_name string", "rows": 1000},
        "orders": {"schema": "order_id int primary key, customer_id int references customers.customer_id", "rows": 10000},
    },
    engine="pandas",
    realism="realistic",
)
```

## `generate_cdc(...)`

Generates CDC-style records with operation type, before/after payloads, event timestamp, ingestion timestamp, sequence number, source system, late-arrival flag, and duplicate flag.

```python
cdc = generate_cdc("banking", table="customers", rows=10000, seed=42)
```

## `export_data(...)`

Writes a dictionary of tables to CSV, JSON, Parquet, or Delta.

Returned DataFrames are always preserved, so users can also write with native pandas or Spark APIs.


## `generate_from_recipe(...)`

Generates a domain or relational dataset from a declarative JSON, TOML, or simple YAML recipe.

```python
from great_generator import generate_from_recipe

data = generate_from_recipe("banking_recipe.yaml")
```

Recipes are useful when a dataset needs to be reproduced for a demo, benchmark, lab, or paper.

## `generate_history(...)`

Generates an SCD2 history table for a single domain table.

```python
from great_generator import generate_history

history = generate_history("banking", table="customers", history_window="2y")
```

The result includes `effective_from`, `effective_to`, and `is_current`.

## `generate_dimensional_model(...)`

Generates a relational dimensional model from a domain pack.

```python
from great_generator import generate_dimensional_model

model = generate_dimensional_model("ecommerce", scale="small")
fact_sales = model["fact_sales"]
dim_customer = model["dim_customer"]
```

Ecommerce and banking include domain-aware fact and dimension tables. Other domains receive a generic fact/dimension split.

## `generate_data_vault_model(...)`

Generates a relational Data Vault model from a domain pack.

```python
from great_generator import generate_data_vault_model

vault = generate_data_vault_model("banking", scale="small")
hub_customer = vault["hub_customer"]
```

The output includes hubs, links, satellites, stable hash keys, load dates, record source values, and model metadata.


## `validate_generated_data(...)`

Validates generated schema data for common quality expectations.

```python
from great_generator import generate_from_schema, validate_generated_data

schema = {"email": "string", "age": "int", "customer_id": "string"}
df = generate_from_schema(schema, rows=100)
result = validate_generated_data(df, schema)
```

Returns a dictionary with `passed`, `errors`, and `warnings`.

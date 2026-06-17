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
- `output_path` and `output_format`: optional convenience exports

```python
data = generate_domain("ecommerce", scale="small", realism="realistic", seed=42)
```

## `generate_from_schema(...)`

Generates a single DataFrame or domain-shaped dictionary from schema metadata.

Supported inputs:

- compact DDL strings such as `"id int, name string"`
- empty pandas DataFrames with dtypes
- PySpark `StructType`
- PySpark DataFrames
- `TableSchema`
- `DomainSchema`

```python
df = generate_from_schema("id int, customer_name string, email string", rows=100)
```

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

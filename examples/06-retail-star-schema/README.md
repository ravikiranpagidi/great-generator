# Retail Star Schema Example

This is the flagship schema-first demo for Great Generator. It starts from SQL DDL, generates related dimension and fact tables, applies deterministic retail behavior, validates referential integrity, and writes table-per-folder outputs plus a provenance manifest.

It is designed for demos, analytics engineering examples, warehouse/lakehouse prototypes, BI dashboard samples, and relational pipeline tests.

## What it generates

```text
retail_star_schema/
  dim_customer
  dim_product
  dim_store
  dim_date
  fact_sales
```

Relationships:

```text
dim_customer.customer_key -> fact_sales.customer_key
dim_product.product_key   -> fact_sales.product_key
dim_store.store_key       -> fact_sales.store_key
dim_date.date_key         -> fact_sales.date_key
```

## Run locally with Pandas

From the repository root:

```bash
python examples/06-retail-star-schema/generate.py
python examples/06-retail-star-schema/validate.py
```

The script writes Parquet outputs under:

```text
examples/06-retail-star-schema/outputs/retail_star_schema/
```

and creates:

```text
manifest.json
```

## Use the DataFrames directly

```python
import importlib.util
from pathlib import Path

example_path = Path("examples/06-retail-star-schema/generate.py")
spec = importlib.util.spec_from_file_location("retail_star_generate", example_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

data = module.generate_dataset(
    rows={
        "dim_customer": 1000,
        "dim_product": 250,
        "dim_store": 50,
        "dim_date": 365,
        "fact_sales": 25000,
    }
)

customers_df = data["dim_customer"]
sales_df = data["fact_sales"]
```

This is intentionally DataFrame-first. You can write the returned frames with native Pandas or Spark APIs to CSV, JSON, Parquet, Delta, Snowflake, Azure SQL, PostgreSQL, SQLite, or another destination supported by your environment.

## Use in Spark or Databricks

See [`databricks_notebook.py`](databricks_notebook.py) for the notebook pattern:

1. generate Pandas tables from the contract,
2. convert to Spark DataFrames,
3. write Parquet or Delta using Spark,
4. optionally register tables in the metastore/catalog.

For very large datasets, prefer Spark-native generation or chunked generation rather than assuming local Pandas memory is enough.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | SQL DDL contract for the retail star schema |
| `generation.yml` | Example generation parameters |
| `generate.py` | Runnable generator, business rules, validation, and manifest output |
| `validate.py` | Standalone validation script |
| `databricks_notebook.py` | Spark/Databricks usage pattern |
| `sample_manifest.json` | Example provenance manifest shape |
| `expected_structure.md` | Expected tables, columns, and checks |

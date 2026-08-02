# Recipe Authoring Guide

Recipes are a convenient way to keep generation parameters in a file rather than hardcoding them in notebooks or scripts.

## When to use a recipe

Use a recipe when you want to share or repeat:

- domain generation settings
- row-count overrides
- output format and path
- anomaly settings
- deterministic seeds
- table-per-folder exports

Use direct Python calls when you need custom business logic or a generated DataFrame returned directly to application code.

## Minimal domain recipe

```json
{
  "kind": "domain",
  "domain": "ecommerce",
  "engine": "pandas",
  "scale": "tiny",
  "output_path": "./synthetic/ecommerce",
  "output_format": "parquet"
}
```

Run:

```bash
great-generator run ecommerce-recipe.json
```

## DataFrame-first recommendation

For notebooks, Spark jobs, and application tests, prefer direct API calls when you need to keep writing flexible:

```python
from great_generator import generate_relational

data = generate_relational(
    tables={
        "customers": {"schema": "customer_id int primary key, name string", "rows": 100},
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id",
            "rows": 500,
        },
    }
)

# Choose your own destination later.
data["customers"].to_parquet("customers.parquet", index=False)
```

## Star-schema example

See [`examples/06-retail-star-schema`](../examples/06-retail-star-schema/README.md) for a more complete generation recipe with DDL, validation, and manifest output.

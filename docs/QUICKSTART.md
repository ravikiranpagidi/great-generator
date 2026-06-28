# Quickstart with `generate_from_schema`

Install:

```bash
pip install great-generator
```

Import with an underscore and start from the schema you already have:

```python
from great_generator import generate_from_schema
```

Generate realistic lower-environment data:

```python
schema = {
    "customer_id": "string",
    "customer_name": "string",
    "email": "string",
    "age": "int",
    "balance": "float",
    "created_at": "datetime",
    "account_status": "string",
}

customers = generate_from_schema(schema, rows=1000)
```

Use pandas write APIs when you want full control:

```python
customers.to_csv("customers.csv", index=False)
customers.to_parquet("customers.parquet", index=False)
```

Use compact DDL when that is closer to your source definition:

```python
df = generate_from_schema(
    "id int, customer_name string, email string, amount double",
    rows=1000,
    realism="realistic",
)
```

Use `realism="placeholder"` when you want simple deterministic test values.

Use `generate_domain("banking")` later when you want a ready-made multi-table demonstration dataset rather than data for your own schema.

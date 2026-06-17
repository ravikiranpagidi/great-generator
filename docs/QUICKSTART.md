# Quickstart

Install:

```bash
pip install great-generator
```

Import with an underscore:

```python
from great_generator import generate_domain, generate_from_schema
```

Generate a realistic banking dataset:

```python
data = generate_domain("banking", scale="small", realism="realistic", seed=42)

customers = data["customers"]
accounts = data["accounts"]
transactions = data["transactions"]
```

Use pandas write APIs when you want full control:

```python
customers.to_csv("customers.csv", index=False)
transactions.to_parquet("transactions.parquet", index=False)
```

Generate a one-off table from a schema:

```python
df = generate_from_schema(
    "id int, customer_name string, email string, amount double",
    rows=1000,
    realism="realistic",
)
```

Use `realism="placeholder"` when you want simple deterministic test values.

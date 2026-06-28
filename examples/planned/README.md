# Planned Schema Inputs

The snippets below describe valuable future APIs. They are intentionally not executable with the current release.

## Rich inline metadata

```python
# Planned
schema = {
    "age": {"type": "int", "min": 18, "max": 85},
    "status": {"type": "string", "values": ["Active", "Inactive"]},
}
```

Today, use a simple dtype mapping plus `custom_rules`.

## Full SQL DDL

```python
# Planned: full CREATE TABLE parsing
ddl = """
CREATE TABLE customers (
    customer_id VARCHAR(50),
    customer_name VARCHAR(100),
    age INT,
    created_at TIMESTAMP
);
"""
```

Today, use compact DDL: `"customer_id string, customer_name string, age int"`.

## JSON Schema

```python
# Planned
schema = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string"},
        "age": {"type": "integer", "minimum": 18},
    },
}
```

## YAML, SQLAlchemy, Pydantic, dataclass, and column lists

These input adapters are planned. JSON, TOML, and simple YAML dataset recipes are supported by `generate_from_recipe`, but they are not schema inputs to `generate_from_schema`.

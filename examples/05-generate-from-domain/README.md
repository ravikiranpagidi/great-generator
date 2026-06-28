# Prebuilt Domain Examples

Use `generate_domain` when you need a ready-made related dataset for a demonstration, tutorial, benchmark, or learning exercise.

```python
from great_generator import generate_domain

data = generate_domain("ecommerce", scale="small")
print(data["customers"].head())
print(data["orders"].head())
```

For an actual project schema, start with `generate_from_schema` instead. Existing domain demos remain in the parent `examples` folder.

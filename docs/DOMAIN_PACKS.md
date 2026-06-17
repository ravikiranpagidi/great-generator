# Domain Packs

Great Generator ships with domain packs that model enterprise-style systems rather than isolated fake columns.

Current domains include:

- `banking`
- `ecommerce`
- `healthcare`
- `insurance`
- `telecom`
- `automotive`
- `energy`
- `manufacturing`
- `logistics`
- `media`
- `public_sector`
- `hospitality`
- `saas`

Each domain includes table metadata, primary keys, foreign keys, realistic distributions, and scale profiles.

```python
from great_generator import get_domain_schema

schema = get_domain_schema("banking")
print(schema.as_dict())
```

Use domain packs when you want connected enterprise datasets for demos, BI dashboards, Spark pipelines, CDC validation, or data-quality tools.

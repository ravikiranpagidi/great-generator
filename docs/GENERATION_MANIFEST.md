# Generation Manifest

A generation manifest is a lightweight provenance document that records how a synthetic dataset was produced.

It is not a data catalog, lineage platform, privacy guarantee, or statistical-quality certificate. It is a practical JSON record for demos, CI fixtures, experiments, support tickets, and enterprise review.

## Why manifests matter

Generated data is most useful when teams can answer:

- Which schema was used?
- Which row counts were requested?
- Which seed was used?
- Which engine generated the data?
- Did the run ingest any real data?
- Were validation checks run?
- Which optional advisor or plan influenced generation?

## Basic usage

```python
from great_generator import generate_from_schema, parse_ddl
from great_generator.io import build_generation_manifest

contract = parse_ddl("""
CREATE TABLE customers (
  customer_id BIGINT PRIMARY KEY,
  customer_name STRING,
  email STRING
);
""")

data = generate_from_schema(contract, rows=1000, seed=42)

manifest = build_generation_manifest(
    dataset_name="customer_demo",
    tables=data if isinstance(data, dict) else {"customers": data},
    engine="pandas",
    seed=42,
    schema_fingerprint=contract.fingerprint(),
    parameters={"rows": 1000, "realism": "realistic"},
    validation={"primary_key_unique": True},
    real_data_ingested=False,
)
```

## Manifest shape

```json
{
  "manifest_version": "1.0",
  "dataset_name": "customer_demo",
  "generated_at": "2026-01-01T00:00:00+00:00",
  "engine": "pandas",
  "seed": 42,
  "schema_fingerprint": "sha256:...",
  "real_data_ingested": false,
  "privacy_note": "Great Generator creates synthetic data and does not anonymize, mask, de-identify, or transform production records.",
  "parameters": {
    "rows": 1000,
    "realism": "realistic"
  },
  "tables": {
    "customers": {
      "row_count": 1000,
      "columns": ["customer_id", "customer_name", "email"]
    }
  },
  "validation": {
    "primary_key_unique": true
  },
  "warnings": []
}
```

## Advisor metadata compatibility

The optional advisor layer already has manifest enrichment helpers. General manifests can be enriched without changing the base shape:

```python
from great_generator.io import enrich_manifest

manifest = enrich_manifest(manifest, plan=plan, cache_hit=True)
```

This adds an `advisor` section while preserving existing manifest fields.

## Spark row-count note

Spark row counts require an action. The manifest helper records Spark columns and dtypes without automatically calling `.count()`. For Spark datasets, put requested counts in `parameters` or validated counts in `validation` after you intentionally run those checks.

## Recommended manifest fields for enterprise demos

- `manifest_version`
- `dataset_name`
- `generated_at`
- `engine`
- `seed`
- `schema_fingerprint`
- `real_data_ingested`
- `parameters`
- `tables`
- `validation`
- `warnings`

For regulated or sensitive environments, add your organization's own approval metadata outside the generated-data library rather than treating synthetic generation as a compliance control.

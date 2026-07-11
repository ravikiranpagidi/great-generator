# Plans and tags

This page documents the JSON artifacts used by the advisor layer.

## GenerationPlan

`GenerationPlan` describes how schema columns should be generated. It is inspectable, editable, and serializable.

| Field | Type | Description |
|---|---|---|
| `plan_version` | string | Plan schema version. Current value is `1.0`. |
| `schema_fingerprint` | string | `sha256:` fingerprint of the canonical schema. |
| `advisor` | string | Advisor name, such as `none`, `anthropic:<model>`, or `ollama:<model>`. |
| `model_id` | string or null | Exact model id used by the advisor. Null for `none`. |
| `generated_at` | string | UTC timestamp in ISO 8601 format. |
| `human_reviewed` | boolean | False by default. True after a plan edit or explicit review. |
| `columns` | list | List of `ColumnStrategy` objects. |
| `inter_column_rules` | list | Optional rule hints that describe column coupling. |
| `notes` | string or null | Human-readable notes. |

## ColumnStrategy

| Field | Type | Description |
|---|---|---|
| `column` | string | Column name. Domain plans may use `table.column`. |
| `dtype` | string | Declared data type. |
| `strategy` | string | Strategy name, such as `semantic.full_name`, `numeric.normal`, or `date_range`. |
| `parameters` | object | Strategy-specific parameters, such as ranges, values, patterns, or date windows. |
| `rationale` | string or null | Human-readable reason for the strategy. |
| `confidence` | number | Confidence from 0.0 to 1.0. |
| `source` | string | One of `advisor`, `user_edit`, or `default`. |

Common strategy names:

| Strategy | Meaning |
|---|---|
| `semantic.full_name` | Person name style values |
| `semantic.email` | Email style values |
| `semantic.phone` | Phone style values |
| `semantic.address` | Address style values |
| `numeric.integer` | Integer values |
| `numeric.normal` | Numeric values around a center |
| `categorical` | Values selected from categories |
| `date_range` | Dates in a date window |
| `timestamp_range` | Timestamps in a time window |
| `string.pattern` | Strings from a deterministic pattern |
| `boolean` | Boolean values |

## ColumnTags

`ColumnTags` stores advisory metadata for schema review.

| Field | Type | Description |
|---|---|---|
| `tag_version` | string | Tag schema version. Current value is `1.0`. |
| `schema_fingerprint` | string | `sha256:` fingerprint of the canonical schema. |
| `advisor` | string | Advisor name. |
| `model_id` | string or null | Exact model id used by the advisor. |
| `generated_at` | string | UTC timestamp in ISO 8601 format. |
| `human_reviewed` | boolean | False by default. True after edits. |
| `columns` | list | List of `ColumnTag` objects. |
| `notes` | string or null | Human-readable notes. |

## ColumnTag

| Field | Type | Allowed values |
|---|---|---|
| `column` | string | Column name |
| `pii_class` | string or null | `none`, `direct_identifier`, `quasi_identifier`, `sensitive_attribute`, or null |
| `business_semantic` | string or null | Free text semantic, such as `customer_email` |
| `suggested_masking` | string or null | Free text masking suggestion |
| `confidence` | number | 0.0 to 1.0 |
| `source` | string | `advisor`, `user_edit`, or `default` |
| `rationale` | string or null | Human-readable reason |

## RealismReport

`RealismReport` is a design-time review of generated sample data against a plan.

| Field | Type | Description |
|---|---|---|
| `report_version` | string | Report schema version. Current value is `1.0`. |
| `advisor` | string | Advisor name. |
| `model_id` | string or null | Exact model id used by the advisor. |
| `generated_at` | string | UTC timestamp in ISO 8601 format. |
| `sample_size` | integer | Requested sample size. |
| `warnings` | list of strings | Potential quality issues. |
| `suggestions` | list of strings | Optional improvement suggestions. |
| `notes` | string or null | Human-readable notes. |
| `score` | number or null | Optional reviewer score. |

## Complete example plan

```json
{
  "advisor": "none",
  "columns": [
    {
      "column": "customer_id",
      "confidence": 0.0,
      "dtype": "int",
      "parameters": {},
      "rationale": "Default dtype strategy.",
      "source": "default",
      "strategy": "numeric.integer"
    },
    {
      "column": "customer_name",
      "confidence": 1.0,
      "dtype": "string",
      "parameters": {},
      "rationale": "Reviewed as a customer name field.",
      "source": "user_edit",
      "strategy": "semantic.full_name"
    }
  ],
  "generated_at": "2026-07-10T00:00:00Z",
  "human_reviewed": true,
  "inter_column_rules": [],
  "model_id": null,
  "notes": "Reviewed by data team.",
  "plan_version": "1.0",
  "schema_fingerprint": "sha256:..."
}
```

## Using a plan

```python
from great_generator import generate_from_schema, infer_generation_plan

schema = "customer_id int, customer_name string"
plan = infer_generation_plan(schema)
reviewed = plan.with_edit(
    "customer_name",
    strategy="semantic.full_name",
    confidence=1.0,
)

df = generate_from_schema(schema, rows=1000, plan=reviewed)
```

## Version compatibility

`plan_version` follows semantic version rules.

- Patch changes fix documentation or validation details without changing artifact meaning.
- Minor changes add optional fields or new strategy names.
- Major changes can change required fields or field meaning.

Readers should ignore unknown optional fields when possible and fail clearly on unsupported major versions.

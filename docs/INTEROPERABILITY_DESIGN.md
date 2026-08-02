# Data Quality Integration Design Notes

This document is a design note, not a committed runtime dependency plan.

Great Generator already returns Pandas and Spark DataFrames, which means users can validate generated data with their preferred quality tools without the library owning those dependencies.

## Candidate integrations

- Great Expectations examples for row-count checks, null checks, uniqueness, and foreign-key-like validations.
- Pandera examples for Pandas schema validation.
- Spark-native validation examples for Databricks, Microsoft Fabric, EMR, Glue, and Synapse Spark.
- dbt-style seed/model examples for analytics engineering demos.

## Recommended first implementation

Start with examples and documentation before adding optional dependencies.

Why:

- keeps the base install lightweight
- avoids forcing one data quality framework on users
- lets users copy patterns into their own stacks
- reduces maintenance surface for the initial release series

## Example Great Expectations flow

1. Generate schema-based or relational data.
2. Save DataFrames or register temporary Spark views.
3. Run expectations for uniqueness, not-null constraints, ranges, and allowed statuses.
4. Save validation output beside the generation manifest.

## Example Pandera flow

1. Define a Pandera schema for generated Pandas data.
2. Generate data with `generate_from_schema` or `generate_relational`.
3. Validate the returned DataFrame before writing it.

## Deferred decision

A future `quality` extra can be considered after the examples prove useful:

```bash
pip install "great-generator[quality]"
```

Until then, documentation-first integration keeps the core library clean.

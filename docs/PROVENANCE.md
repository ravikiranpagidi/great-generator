# Provenance and Safety Notes

Great Generator creates synthetic data from user-provided schemas, built-in domain packs, and deterministic rules.

## Important privacy boundary

Great Generator does not anonymize, mask, de-identify, tokenize, or transform production records.

If you provide a schema, it uses the schema. If you provide a DataFrame as a schema source, it reads the structure, not the production rows, for normal schema-based generation paths.

Teams should still follow internal governance rules for:

- PII
- PHI
- PCI
- confidential business data
- regulated workloads
- lower-environment access controls
- retention policies

## Recommended safe workflow

1. Start from a schema, DDL contract, empty DataFrame, or Spark `StructType`.
2. Generate synthetic data without passing real records.
3. Save a generation manifest.
4. Validate keys, nulls, ranges, and business rules.
5. Review sample output before using it in demos, tests, or shared environments.
6. Keep generated data clearly labeled as synthetic.

## What to record

- package version
- schema or contract fingerprint
- seed, row counts, and realism mode
- execution engine
- optional custom rules
- validation results
- whether any real data was ingested

See [Generation Manifest](GENERATION_MANIFEST.md) for a practical JSON shape.

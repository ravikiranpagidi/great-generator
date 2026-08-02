# Suggested Issue Backlog

These are strong starter issues for future contributors and release planning.

## Good first issues

- Add one more schema-first notebook with Pandas output and validation.
- Add examples for JSON-lines output from generated DataFrames.
- Add more semantic aliases for common enterprise columns.
- Add additional domain reference values for telecom, insurance, healthcare, logistics, and public-sector schemas.
- Add docs for using generated Spark DataFrames with Microsoft Fabric Lakehouse tables.

## Documentation issues

- Add a Great Expectations example without adding it as a core dependency.
- Add a Pandera validation example without adding it as a core dependency.
- Add a dbt-style analytics engineering demo using generated dimension/fact tables.
- Add cloud-specific storage notes for ADLS, S3, GCS, and DBFS.

## Engineering issues

- Improve optional advisor mypy typing with extras-aware checks.
- Add composite-key relational generation strategy after the DDL parser milestone.
- Add chunked Pandas writing helpers for very large local datasets.
- Add Spark-native contract generation for multi-table schemas at larger scale.
- Add optional catalog registration helpers for Spark runtimes.

## Research-oriented issues

- Define statistical quality metrics that are appropriate for schema-generated synthetic data.
- Add reproducibility reports comparing seeds, schema fingerprints, and manifests.
- Add anomaly ground-truth evaluation examples for data quality tools.

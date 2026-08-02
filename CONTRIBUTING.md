# Contributing

Thanks for helping make `great-generator` more useful.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Development workflow

1. Create a focused branch.
2. Add or update tests with every behavior change.
3. Run:

```bash
ruff check .
black --check .
pytest
python -m build
python -m twine check dist/*
```

4. Keep domain packs realistic, deterministic, and dependency-light.
5. Prefer small public APIs with excellent examples over clever internals.

## Good contributions

- New domain packs with documented relationships and behaviors
- Additional realistic reference values for existing domains
- Additional anomaly types that are opt-in and testable
- Spark generation improvements that preserve deterministic behavior
- Exporters, schema utilities, and documentation examples
- Bug fixes with regression tests

## Contribution tracks

Choose one focused track per pull request when possible:

| Track | Good examples | Required proof |
|---|---|---|
| Schema realism | semantic aliases, better column inference, safer defaults | tests showing realistic values are generated for multiple column names |
| Relational generation | primary-key/foreign-key behavior, DDL contracts, star-schema examples | relationship-integrity tests |
| Spark and storage | Spark DataFrame output, partitioning, cloud path docs, Delta examples | optional Spark tests or clear runtime notes |
| Data quality | validation examples, anomaly labels, quality-tool examples | tests or runnable docs examples |
| Documentation | demos, recipes, migration guides, benchmark notes | commands that were run or screenshots when relevant |
| Domain packs | new industry domains or richer existing domains | table, column, relationship, and seed-reproducibility tests |

## Reproducibility expectations

- Use `seed` in tests and examples when exact reproducibility matters.
- Document whether an example is Pandas-local, Spark-local, or cluster Spark.
- Do not claim a fixed maximum row count or throughput unless it was tested in the target environment.
- Include a generation manifest or enough parameters for another user to reproduce the run.
- Keep examples synthetic-only. Do not add real customer, employee, patient, payment, or production records.

## Adding a domain pack

A good domain pack should include:

1. table schemas with primary keys and foreign keys
2. deterministic pandas generation
3. Spark support through either a domain-specific generator or schema-driven fallback
4. realistic distributions, skew, and time behavior
5. tests for tables, columns, relationships, and seed reproducibility
6. README or docs examples showing why the domain is useful

## Adding realistic values

Add reusable business values to `great_generator/core/reference_values.py` when they can help more than one domain or user-provided schema. Keep lists realistic, dependency-light, and safe for public demos. Add tests that prove realistic mode is not returning placeholder-only values.

## Suggested starter issues

- Add realistic values for telecom plans and device models
- Add ecommerce dashboard demo notebook
- Add Spark benchmark script for cluster runs
- Improve API reference docs with more examples
- Add Great Expectations integration example
- Add Microsoft Fabric demo using generated Parquet data
- Add more healthcare provider and facility reference values
- Add tests for realistic optional-null distribution
- Add Pandera validation examples for schema-generated Pandas data
- Add chunked Pandas write examples for large local datasets
- Add Spark catalog-registration examples for Databricks and Fabric
- Add issue templates for domain packs, realism rules, and examples

## Releases

Release work should follow [docs/PYPI_RELEASE.md](docs/PYPI_RELEASE.md).

## Community and security

- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)

## Design principles

- Referential integrity by default
- Anomalies only when explicitly requested
- Seeds should make experiments reproducible
- Optional Spark/Delta dependencies must remain optional
- A newcomer should succeed in under a minute

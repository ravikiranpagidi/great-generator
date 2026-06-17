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

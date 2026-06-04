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
- Additional anomaly types that are opt-in and testable
- Spark generation improvements that preserve deterministic behavior
- Exporters, schema utilities, and documentation examples
- Bug fixes with regression tests

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

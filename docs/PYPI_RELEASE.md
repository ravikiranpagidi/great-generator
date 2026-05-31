# PyPI release checklist

This project is prepared for PyPI release through GitHub Actions and PyPI Trusted Publishing.

## One-time setup

Configure trusted publishers in PyPI and TestPyPI.

### PyPI

- Project name: `enterprise-synth`
- Owner/repository: `ravikiranpagidi/data-genie`
- Workflow: `release-pypi.yml`
- Environment: `pypi`

### TestPyPI

- Project name: `enterprise-synth`
- Owner/repository: `ravikiranpagidi/data-genie`
- Workflow: `release-testpypi.yml`
- Environment: `testpypi`

GitHub environments named `pypi` and `testpypi` should exist before publishing. They can optionally require manual approval.

## Before every release

1. Update the version in:
   - `pyproject.toml`
   - `enterprise_synth/__init__.py`
2. Update `CHANGELOG.md`.
3. Run:

```bash
ruff check .
black --check .
pytest
python -m build
python -m twine check dist/*
```

4. Install the built wheel in a clean environment:

```bash
python -m venv .release-smoke
.release-smoke\Scripts\activate
python -m pip install --upgrade pip
python -m pip install dist\enterprise_synth-*.whl
python - <<'PY'
from enterprise_synth import generate_domain

data = generate_domain("ecommerce", scale="tiny", seed=42)
assert len(data["customers"]) == 25
print("smoke test passed")
PY
```

On macOS/Linux, activate the environment with:

```bash
source .release-smoke/bin/activate
```

## TestPyPI dry run

Run the `publish-testpypi` workflow manually from GitHub Actions.

After it succeeds, test install from TestPyPI:

```bash
python -m venv .testpypi-smoke
.testpypi-smoke\Scripts\activate
python -m pip install --upgrade pip
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ enterprise-synth
python - <<'PY'
from enterprise_synth import generate_domain

data = generate_domain("banking", scale="tiny", seed=42)
assert len(data["customers"]) == 25
print("TestPyPI install passed")
PY
```

## Production PyPI release

1. Commit all release changes.
2. Push `main`.
3. Create and publish a GitHub release tagged with the version, for example `v0.1.0`.
4. The `publish-pypi` workflow publishes the wheel and source distribution to PyPI.

## Post-release

- Verify the PyPI project page renders the README correctly.
- Install from PyPI in a clean environment.
- Open a tracking issue for the next release.

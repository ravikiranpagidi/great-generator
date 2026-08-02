"""Validate the generated retail star schema.

Run after generate.py:

    python examples/06-retail-star-schema/validate.py

The validation logic is intentionally simple and transparent so users can adapt
it to their own data quality framework.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

EXAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXAMPLE_DIR / "outputs" / "retail_star_schema"


def _load_generate_module():
    spec = importlib.util.spec_from_file_location(
        "retail_star_generate", EXAMPLE_DIR / "generate.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generated_tables(output_dir: Path = OUTPUT_DIR) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table_dir in sorted(output_dir.iterdir()):
        if not table_dir.is_dir():
            continue
        parquet_files = list(table_dir.glob("*.parquet"))
        csv_files = list(table_dir.glob("*.csv"))
        json_files = list(table_dir.glob("*.json"))
        if parquet_files:
            tables[table_dir.name] = pd.read_parquet(table_dir)
        elif csv_files:
            tables[table_dir.name] = pd.concat(pd.read_csv(path) for path in csv_files)
        elif json_files:
            tables[table_dir.name] = pd.concat(
                pd.read_json(path, lines=True) for path in json_files
            )
    return tables


def main() -> None:
    generator = _load_generate_module()
    data = generator.generate_dataset() if not OUTPUT_DIR.exists() else load_generated_tables()
    results = generator.validate_dataset(data)
    print(json.dumps(results, indent=2))
    if not all(results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

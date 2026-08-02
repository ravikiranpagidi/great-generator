from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

EXAMPLE_PATH = Path("examples/06-retail-star-schema/generate.py")
ROWS = {
    "dim_customer": 25,
    "dim_product": 10,
    "dim_store": 4,
    "dim_date": 31,
    "fact_sales": 100,
}


def _load_example_module():
    spec = importlib.util.spec_from_file_location("retail_star_generate", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None, "retail star example should load"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retail_star_schema_contract_generates_expected_tables():
    module = _load_example_module()

    data = module.generate_dataset(rows=ROWS, seed=2026)

    assert set(data) == set(ROWS), "retail star schema should return all dimension and fact tables"
    assert data["fact_sales"].shape[0] == ROWS["fact_sales"]
    assert data["dim_customer"].shape[0] == ROWS["dim_customer"]


def test_retail_star_schema_relationships_and_amounts_validate():
    module = _load_example_module()
    data = module.generate_dataset(rows=ROWS, seed=2026)

    validation = module.validate_dataset(data)

    assert all(validation.values()), f"retail star schema validation failed: {validation}"


def test_retail_star_schema_is_deterministic_for_same_seed():
    module = _load_example_module()

    first = module.generate_dataset(rows=ROWS, seed=2026)
    second = module.generate_dataset(rows=ROWS, seed=2026)

    for table_name in ROWS:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])


def test_retail_star_schema_manifest_records_provenance():
    module = _load_example_module()
    data = module.generate_dataset(rows=ROWS, seed=2026)

    manifest = module.build_manifest(data, seed=2026, rows=ROWS, realism="realistic")

    assert manifest["manifest_version"] == "1.0"
    assert manifest["dataset_name"] == "retail_star_schema"
    assert manifest["seed"] == 2026
    assert manifest["real_data_ingested"] is False
    assert manifest["schema_fingerprint"].startswith("sha256:")
    assert manifest["tables"]["fact_sales"]["row_count"] == ROWS["fact_sales"]
    assert manifest["validation"]["foreign_keys_valid"] is True

from pathlib import Path

import pytest

from enterprise_synth import generate_domain


def test_csv_export_writes_expected_files(tmp_path: Path):
    generate_domain("ecommerce", scale="tiny", seed=42, output_path=tmp_path, output_format="csv")
    assert (tmp_path / "customers" / "customers.csv").exists()
    assert (tmp_path / "orders" / "orders.csv").exists()


def test_json_export_writes_expected_files(tmp_path: Path):
    generate_domain("ecommerce", scale="tiny", seed=42, output_path=tmp_path, output_format="json")
    assert (tmp_path / "customers" / "customers.json").exists()
    assert (tmp_path / "orders" / "orders.json").exists()


def test_parquet_export_writes_expected_files(tmp_path: Path):
    pytest.importorskip("pyarrow")
    generate_domain("banking", scale="tiny", seed=42, output_path=tmp_path, output_format="parquet")
    assert (tmp_path / "customers" / "customers.parquet").exists()
    assert (tmp_path / "transactions" / "transactions.parquet").exists()

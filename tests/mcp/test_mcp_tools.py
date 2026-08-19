from __future__ import annotations

import json

import pandas as pd
import pytest

from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import GreatGeneratorMCPError
from great_generator.mcp.tools.export_dataset_tool import export_dataset_tool
from great_generator.mcp.tools.generate_from_schema_tool import generate_from_schema_tool
from great_generator.mcp.tools.generate_relational_tool import generate_relational_tool
from great_generator.mcp.tools.parse_ddl_tool import parse_ddl_tool
from great_generator.mcp.tools.validate_query_coverage_tool import validate_query_coverage_tool


def test_generate_from_schema_writes_output_manifest_and_preview(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)

    result = generate_from_schema_tool(
        "customer_id int, customer_name string, account_status string",
        20,
        "customers",
        seed=42,
        required_values={"account_status": ["Active"]},
        overwrite=False,
        config=config,
    )

    output_path = tmp_path / "customers" / "dataset.csv"
    manifest_path = tmp_path / "customers" / "manifest.json"
    coverage_path = tmp_path / "customers" / "query_coverage.json"

    assert result["status"] == "ok"
    assert result["row_count"] == 20
    assert result["output_files"] == [str(output_path)]
    assert output_path.exists()
    assert manifest_path.exists()
    assert coverage_path.exists()
    assert len(result["preview"]) <= 5
    assert "account_status" in result["columns"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["generated_by"] == "Great Generator MCP"
    assert "not production data" in manifest["synthetic_data_notice"]


def test_generate_from_schema_is_deterministic_with_seed(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    first = generate_from_schema_tool(
        "customer_id int, customer_name string, email string",
        10,
        "first",
        seed=123,
        config=config,
    )
    second = generate_from_schema_tool(
        "customer_id int, customer_name string, email string",
        10,
        "second",
        seed=123,
        config=config,
    )

    first_frame = pd.read_csv(first["output_files"][0])
    second_frame = pd.read_csv(second["output_files"][0])

    pd.testing.assert_frame_equal(first_frame, second_frame)


def test_generate_from_schema_rejects_overwrite_by_default(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    generate_from_schema_tool("id int, name string", 3, "data", config=config)

    with pytest.raises(GreatGeneratorMCPError, match="overwrite=True"):
        generate_from_schema_tool("id int, name string", 3, "data", config=config)

    result = generate_from_schema_tool(
        "id int, name string", 3, "data", overwrite=True, config=config
    )
    assert result["row_count"] == 3


def test_generate_relational_writes_one_file_per_table(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    result = generate_relational_tool(
        schemas={
            "customers": "customer_id int primary key, customer_name string",
            "orders": "order_id int primary key, customer_id int references customers.customer_id, order_amount double",
        },
        rows={"customers": 5, "orders": 12},
        output_dir="relational",
        relationships=["orders.customer_id -> customers.customer_id"],
        seed=7,
        config=config,
    )

    assert result["row_counts"] == {"customers": 5, "orders": 12}
    assert len(result["output_files"]) == 2
    assert all(
        (tmp_path / "relational" / name).exists() for name in ["customers.csv", "orders.csv"]
    )
    assert set(result["preview"]) == {"customers", "orders"}


def test_parse_ddl_returns_contract_summary():
    result = parse_ddl_tool(
        "CREATE TABLE sales.customers (customer_id BIGINT PRIMARY KEY, customer_name STRING)",
        dialect="databricks",
    )

    assert result["status"] == "ok"
    assert result["contract"]["table_count"] == 1
    assert result["contract"]["fingerprint"].startswith("sha256:")
    assert "sales.customers" in result["contract"]["tables"]


def test_validate_query_coverage_loads_local_file(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    generated = generate_from_schema_tool(
        "account_id int, account_status string",
        12,
        "accounts",
        required_values={"account_status": ["Active"]},
        seed=8,
        config=config,
    )

    result = validate_query_coverage_tool(
        generated["output_files"][0],
        required_values={"account_status": ["Active"]},
        config=config,
    )

    assert result["status"] == "ok"
    assert result["report"]["passed"] is True


def test_export_dataset_writes_requested_format(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    generated = generate_from_schema_tool("id int, name string", 4, "source", seed=9, config=config)

    result = export_dataset_tool(
        generated["output_files"][0],
        "exported",
        format="jsonl",
        config=config,
    )

    output_path = tmp_path / "exported" / "dataset.jsonl"
    assert result["status"] == "ok"
    assert result["output_files"] == [str(output_path)]
    assert output_path.exists()
    assert result["row_counts"] == 4

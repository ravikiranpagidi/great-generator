from __future__ import annotations

import pytest

from great_generator.mcp.config import MCPConfig
from great_generator.mcp.safety import (
    GreatGeneratorMCPError,
    resolve_input_path,
    resolve_output_dir,
    safe_file_stem,
    validate_format,
    validate_row_count,
)


def test_rejects_output_dir_outside_allowed_root(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    outside = tmp_path.parent / "outside"

    with pytest.raises(GreatGeneratorMCPError, match="allowed root"):
        resolve_output_dir(outside, config=config)


def test_rejects_input_path_outside_allowed_root(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)
    outside_file = tmp_path.parent / "outside.csv"
    outside_file.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(GreatGeneratorMCPError, match="allowed root"):
        resolve_input_path(outside_file, config=config)


def test_rejects_row_counts_above_configured_max(tmp_path):
    config = MCPConfig(allowed_root=tmp_path, max_rows=10, hard_max_rows=100)

    with pytest.raises(GreatGeneratorMCPError, match="exceeds the MCP row limit"):
        validate_row_count(11, config=config)

    assert validate_row_count(11, allow_large=True, config=config) == 11

    with pytest.raises(GreatGeneratorMCPError, match="hard MCP row limit"):
        validate_row_count(101, allow_large=True, config=config)


def test_rejects_unsupported_format():
    with pytest.raises(GreatGeneratorMCPError, match="Unsupported format"):
        validate_format("delta")


def test_rejects_missing_output_dir(tmp_path):
    config = MCPConfig(allowed_root=tmp_path)

    with pytest.raises(GreatGeneratorMCPError, match="output_dir is required"):
        resolve_output_dir("", config=config)


def test_rejects_unsafe_file_names():
    with pytest.raises(GreatGeneratorMCPError, match="Unsafe file name"):
        safe_file_stem("../customers")

    assert safe_file_stem("sales.customers table") == "sales.customers_table"

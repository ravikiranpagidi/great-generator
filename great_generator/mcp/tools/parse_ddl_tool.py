"""parse_ddl MCP tool."""

from __future__ import annotations

from typing import Any

from great_generator import parse_ddl
from great_generator.mcp.safety import GreatGeneratorMCPError
from great_generator.mcp.serializers import contract_summary

_SUPPORTED_DIALECTS = {"ansi", "spark", "databricks", "generic"}


def parse_ddl_tool(
    ddl: str,
    *,
    dialect: str = "ansi",
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    """Parse SQL CREATE TABLE DDL and return a normalized contract summary."""

    if not str(ddl or "").strip():
        raise GreatGeneratorMCPError("ddl is required.")
    normalized_dialect = str(dialect or "ansi").strip().lower()
    if normalized_dialect not in _SUPPORTED_DIALECTS:
        supported = ", ".join(sorted(_SUPPORTED_DIALECTS))
        raise GreatGeneratorMCPError(f"Unsupported dialect '{dialect}'. Use one of: {supported}.")
    parser_dialect = "ansi" if normalized_dialect == "generic" else normalized_dialect
    contract = parse_ddl(
        ddl,
        dialect=parser_dialect,
        strict=not include_diagnostics,
    )
    summary = contract_summary(contract, include_diagnostics=include_diagnostics)
    return {
        "status": "ok",
        "tool": "parse_ddl",
        "dialect": parser_dialect,
        "contract": summary,
        "warnings": summary.get("diagnostics", []) if include_diagnostics else [],
    }

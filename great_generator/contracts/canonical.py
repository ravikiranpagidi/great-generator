"""Stable canonical serialization for dataset contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from great_generator.schemas.models import (
    CheckConstraint,
    ColumnSpec,
    ContractSchema,
    ForeignKey,
    TableSchema,
    UniqueConstraint,
)

CANONICAL_CONTRACT_VERSION = "1.0"


def canonical_contract_dict(contract: ContractSchema) -> dict[str, Any]:
    """Return a deterministic JSON-safe representation of a contract."""

    return {
        "canonical_contract_version": CANONICAL_CONTRACT_VERSION,
        "kind": "contract",
        "name": _clean_string(contract.name),
        "namespace": _clean_optional(contract.namespace),
        "description": _clean_string(contract.description),
        "source_format": _clean_string(contract.source_format),
        "source_dialect": _clean_optional(contract.source_dialect),
        "tags": sorted(_clean_string(tag) for tag in contract.tags),
        "metadata": _canonical_metadata(contract.metadata),
        "tables": {
            key: _table_payload(table)
            for key, table in sorted(
                contract.tables.items(), key=lambda item: _clean_string(item[0])
            )
        },
    }


def canonical_contract_json(contract: ContractSchema) -> str:
    """Return stable canonical JSON for a contract."""

    return json.dumps(
        _canonical_value(canonical_contract_dict(contract)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def contract_hash(contract: ContractSchema) -> str:
    """Return a stable SHA-256 hash over canonical contract JSON."""

    return "sha256:" + hashlib.sha256(canonical_contract_json(contract).encode("utf-8")).hexdigest()


def _table_payload(table: TableSchema) -> dict[str, Any]:
    return {
        "name": _clean_string(table.name),
        "namespace": _clean_optional(table.namespace),
        "qualified_name": _clean_string(table.qualified_name),
        "description": _clean_string(table.description),
        "primary_key_columns": [_clean_string(column) for column in table.primary_key_columns],
        "tags": sorted(_clean_string(tag) for tag in table.tags),
        "metadata": _canonical_metadata(table.metadata),
        "columns": [_column_payload(column) for column in table.columns],
        "unique_constraints": sorted(
            (_unique_payload(constraint) for constraint in table.unique_constraints),
            key=lambda item: (item.get("name") or "", tuple(item["columns"])),
        ),
        "checks": sorted(
            (_check_payload(check) for check in table.checks),
            key=lambda item: (item.get("name") or "", item["expression"]),
        ),
        "foreign_keys": sorted(
            (_foreign_key_payload(fk) for fk in table.foreign_keys),
            key=lambda item: (
                item.get("constraint_name") or "",
                item.get("child_table") or "",
                tuple(item["child_columns"]),
                item["parent_table"],
                tuple(item["parent_columns"]),
            ),
        ),
    }


def _column_payload(column: ColumnSpec) -> dict[str, Any]:
    return {
        "name": _clean_string(column.name),
        "dtype": _clean_string(column.dtype).lower(),
        "nullable": bool(column.nullable),
        "description": _clean_string(column.description),
        "original_type": _canonical_type_text(column.original_type),
        "logical_type": _clean_optional(column.logical_type),
        "semantic_type": _clean_optional(column.semantic_type),
        "default_expression": _clean_optional(column.default_expression),
        "precision": column.precision,
        "scale": column.scale,
        "max_length": column.max_length,
        "min_value": _canonical_value(column.min_value),
        "max_value": _canonical_value(column.max_value),
        "accepted_values": [_canonical_value(value) for value in column.accepted_values],
        "tags": sorted(_clean_string(tag) for tag in column.tags),
        "metadata": _canonical_metadata(column.metadata),
    }


def _unique_payload(constraint: UniqueConstraint) -> dict[str, Any]:
    return {
        "name": _clean_optional(constraint.name),
        "columns": [_clean_string(column) for column in constraint.columns],
        "metadata": _canonical_metadata(constraint.metadata),
    }


def _check_payload(check: CheckConstraint) -> dict[str, Any]:
    return {
        "name": _clean_optional(check.name),
        "expression": _clean_string(check.expression),
        "columns": [_clean_string(column) for column in check.columns],
        "metadata": _canonical_metadata(check.metadata),
    }


def _foreign_key_payload(fk: ForeignKey) -> dict[str, Any]:
    return {
        "constraint_name": _clean_optional(fk.constraint_name),
        "child_table": _clean_optional(fk.child_table),
        "child_columns": [_clean_string(column) for column in fk.child_columns],
        "parent_table": _clean_string(fk.parent_table),
        "parent_columns": [_clean_string(column) for column in fk.parent_columns],
        "nullable": fk.nullable,
        "on_update": _clean_optional(fk.on_update),
        "on_delete": _clean_optional(fk.on_delete),
        "metadata": _canonical_metadata(fk.metadata),
    }


def _canonical_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    # Diagnostics are parser observations, not contract semantics, so they are excluded from the
    # reproducibility hash. Contract-affecting options should be stored under explicit metadata keys.
    return {
        _clean_string(str(key)): _canonical_value(value)
        for key, value in sorted(metadata.items(), key=lambda pair: str(pair[0]))
        if str(key) not in {"diagnostics", "parse_warnings"}
    }


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            _clean_string(str(key)): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, str):
        return _clean_string(value)
    return value


def _clean_string(value: str) -> str:
    return " ".join(str(value).strip().split())


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = _clean_string(str(value))
    return text or None


def _canonical_type_text(value: Any) -> str | None:
    if value is None:
        return None
    text = "".join(str(value).strip().lower().split())
    return text or None

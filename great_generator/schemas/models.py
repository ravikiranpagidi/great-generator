"""Lightweight schema metadata used by domains, validation, and extensions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ForeignKey:
    """A directed foreign-key relationship."""

    column: str
    parent_table: str
    parent_column: str


@dataclass(frozen=True)
class ColumnSpec:
    """Column metadata for human-readable schema introspection."""

    name: str
    dtype: str
    nullable: bool = False
    description: str = ""


@dataclass(frozen=True)
class TableSchema:
    """Metadata for a generated table."""

    name: str
    columns: tuple[ColumnSpec, ...]
    primary_key: str | None = None
    foreign_keys: tuple[ForeignKey, ...] = ()
    description: str = ""

    def column_names(self) -> list[str]:
        return [column.name for column in self.columns]


@dataclass(frozen=True)
class DomainSchema:
    """Metadata for a domain pack."""

    name: str
    tables: Mapping[str, TableSchema]
    description: str
    behaviors: tuple[str, ...] = field(default_factory=tuple)

    def dependencies(self) -> dict[str, set[str]]:
        return {
            table_name: {fk.parent_table for fk in table.foreign_keys}
            for table_name, table in self.tables.items()
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "behaviors": list(self.behaviors),
            "tables": {
                table_name: {
                    "primary_key": table.primary_key,
                    "description": table.description,
                    "columns": [
                        {
                            "name": column.name,
                            "dtype": column.dtype,
                            "nullable": column.nullable,
                            "description": column.description,
                        }
                        for column in table.columns
                    ],
                    "foreign_keys": [
                        {
                            "column": fk.column,
                            "parent_table": fk.parent_table,
                            "parent_column": fk.parent_column,
                        }
                        for fk in table.foreign_keys
                    ],
                }
                for table_name, table in self.tables.items()
            },
        }

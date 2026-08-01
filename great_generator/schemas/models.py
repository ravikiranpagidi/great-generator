"""Lightweight schema and contract metadata used by generation and planning."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


class FrozenDict(Mapping[str, Any]):
    """Small immutable mapping for hashable schema extension metadata."""

    __slots__ = ("_data", "_hash")

    def __init__(self, value: Mapping[str, Any] | None = None, **items: Any) -> None:
        raw: dict[str, Any] = {}
        if value:
            raw.update({str(key): _freeze_value(item) for key, item in value.items()})
        if items:
            raw.update({str(key): _freeze_value(item) for key, item in items.items()})
        self._data = dict(sorted(raw.items(), key=lambda pair: pair[0]))
        self._hash: int | None = None

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash(tuple((key, _hashable_value(value)) for key, value in self.items()))
        return self._hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return False
        return dict(self.items()) == dict(other.items())

    def __repr__(self) -> str:
        return f"FrozenDict({self._data!r})"


def freeze_metadata(value: Mapping[str, Any] | None) -> FrozenDict:
    """Return extension metadata as an immutable mapping."""

    if isinstance(value, FrozenDict):
        return value
    return FrozenDict(value or {})


@dataclass(frozen=True)
class UniqueConstraint:
    """Unique constraint over one or more ordered columns."""

    columns: tuple[str, ...]
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(str(column) for column in self.columns))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))


@dataclass(frozen=True)
class CheckConstraint:
    """Table or column check expression preserved from a contract source."""

    expression: str
    name: str | None = None
    columns: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "expression", str(self.expression).strip())
        object.__setattr__(self, "columns", tuple(str(column) for column in self.columns))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))


@dataclass(frozen=True)
class ForeignKey:
    """A directed foreign-key relationship.

    The first three fields preserve the original public constructor:
    ``ForeignKey(column, parent_table, parent_column)``. Additional fields carry
    contract-grade metadata such as composite columns and actions.
    """

    column: str
    parent_table: str
    parent_column: str
    constraint_name: str | None = None
    child_table: str | None = None
    child_columns: tuple[str, ...] = ()
    parent_columns: tuple[str, ...] = ()
    nullable: bool | None = None
    on_update: str | None = None
    on_delete: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        child_columns = tuple(str(column) for column in (self.child_columns or (self.column,)))
        parent_columns = tuple(
            str(column) for column in (self.parent_columns or (self.parent_column,))
        )
        if not child_columns:
            raise ValueError("ForeignKey requires at least one child column.")
        if not parent_columns:
            raise ValueError("ForeignKey requires at least one parent column.")
        if len(child_columns) != len(parent_columns):
            raise ValueError(
                "ForeignKey child_columns and parent_columns must have the same length."
            )
        object.__setattr__(self, "column", str(child_columns[0]))
        object.__setattr__(self, "parent_column", str(parent_columns[0]))
        object.__setattr__(self, "parent_table", str(self.parent_table))
        object.__setattr__(self, "child_table", _optional_string(self.child_table))
        object.__setattr__(self, "child_columns", child_columns)
        object.__setattr__(self, "parent_columns", parent_columns)
        object.__setattr__(self, "constraint_name", _optional_string(self.constraint_name))
        object.__setattr__(self, "on_update", _optional_string(self.on_update))
        object.__setattr__(self, "on_delete", _optional_string(self.on_delete))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))


@dataclass(frozen=True)
class ColumnSpec:
    """Column metadata for schema introspection and contract-driven generation."""

    name: str
    dtype: str
    nullable: bool = False
    description: str = ""
    original_type: str | None = None
    logical_type: str | None = None
    semantic_type: str | None = None
    default_expression: str | None = None
    precision: int | None = None
    scale: int | None = None
    max_length: int | None = None
    min_value: Any | None = None
    max_value: Any | None = None
    accepted_values: tuple[Any, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name))
        object.__setattr__(self, "dtype", str(self.dtype))
        object.__setattr__(self, "original_type", _optional_string(self.original_type))
        object.__setattr__(self, "logical_type", _optional_string(self.logical_type))
        object.__setattr__(self, "semantic_type", _optional_string(self.semantic_type))
        object.__setattr__(self, "default_expression", _optional_string(self.default_expression))
        object.__setattr__(
            self, "accepted_values", tuple(_freeze_value(value) for value in self.accepted_values)
        )
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))


@dataclass(frozen=True)
class TableSchema:
    """Metadata for a generated or parsed table."""

    name: str
    columns: tuple[ColumnSpec, ...]
    primary_key: str | None = None
    foreign_keys: tuple[ForeignKey, ...] = ()
    description: str = ""
    namespace: str | None = None
    primary_key_columns: tuple[str, ...] = ()
    unique_constraints: tuple[UniqueConstraint, ...] = ()
    checks: tuple[CheckConstraint, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        columns = tuple(self.columns)
        primary_columns = tuple(str(column) for column in self.primary_key_columns)
        primary_key = _optional_string(self.primary_key)
        if primary_columns and primary_key is None:
            primary_key = primary_columns[0]
        if primary_key is not None and not primary_columns:
            primary_columns = (primary_key,)
        object.__setattr__(self, "name", str(self.name))
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "primary_key", primary_key)
        object.__setattr__(self, "foreign_keys", tuple(self.foreign_keys))
        object.__setattr__(self, "namespace", _optional_string(self.namespace))
        object.__setattr__(self, "primary_key_columns", primary_columns)
        object.__setattr__(self, "unique_constraints", tuple(self.unique_constraints))
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))

    def column_names(self) -> list[str]:
        return [column.name for column in self.columns]

    @property
    def qualified_name(self) -> str:
        """Return ``namespace.name`` when a namespace is available."""

        return f"{self.namespace}.{self.name}" if self.namespace else self.name


@dataclass(frozen=True)
class DomainSchema:
    """Metadata for a generated domain pack or user-defined relational schema."""

    name: str
    tables: Mapping[str, TableSchema]
    description: str
    behaviors: tuple[str, ...] = field(default_factory=tuple)
    namespace: str | None = None
    source_format: str = "domain_pack"
    source_dialect: str | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tables", dict(self.tables))
        object.__setattr__(self, "behaviors", tuple(str(item) for item in self.behaviors))
        object.__setattr__(self, "namespace", _optional_string(self.namespace))
        object.__setattr__(self, "source_format", str(self.source_format))
        object.__setattr__(self, "source_dialect", _optional_string(self.source_dialect))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))

    def dependencies(self) -> dict[str, set[str]]:
        return {
            table_name: {fk.parent_table for fk in table.foreign_keys}
            for table_name, table in self.tables.items()
        }

    def as_dict(self) -> dict[str, Any]:
        return _domain_payload(self)


@dataclass(frozen=True)
class ContractSchema:
    """Canonical dataset contract independent of Pandas and Spark."""

    name: str
    tables: Mapping[str, TableSchema]
    description: str = ""
    namespace: str | None = None
    source_format: str = "internal"
    source_dialect: str | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=FrozenDict)

    def __post_init__(self) -> None:
        tables = dict(self.tables)
        if not tables:
            raise ValueError("ContractSchema requires at least one table.")
        object.__setattr__(self, "name", str(self.name))
        object.__setattr__(self, "tables", tables)
        object.__setattr__(self, "namespace", _optional_string(self.namespace))
        object.__setattr__(self, "source_format", str(self.source_format))
        object.__setattr__(self, "source_dialect", _optional_string(self.source_dialect))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))

    def dependencies(self) -> dict[str, set[str]]:
        return {
            table_name: {fk.parent_table for fk in table.foreign_keys}
            for table_name, table in self.tables.items()
        }

    def as_dict(self) -> dict[str, Any]:
        return _contract_payload(self)

    def to_domain_schema(self, *, name: str | None = None) -> DomainSchema:
        """Convert the contract into the existing DomainSchema container."""

        return DomainSchema(
            name=name or self.name,
            tables=self.tables,
            description=self.description or "Generated from canonical contract.",
            behaviors=("contract-first schema", "parsed relationships"),
            namespace=self.namespace,
            source_format=self.source_format,
            source_dialect=self.source_dialect,
            tags=self.tags,
            metadata=self.metadata,
        )

    def canonical_dict(self) -> dict[str, Any]:
        """Return the deterministic canonical representation used for hashing."""

        from great_generator.contracts.canonical import canonical_contract_dict

        return canonical_contract_dict(self)

    def canonical_json(self) -> str:
        """Return stable canonical JSON for the contract."""

        from great_generator.contracts.canonical import canonical_contract_json

        return canonical_contract_json(self)

    def fingerprint(self) -> str:
        """Return a stable SHA-256 fingerprint for the contract."""

        from great_generator.contracts.canonical import contract_hash

        return contract_hash(self)


# Backward-friendly alias for users who prefer the product vocabulary.
Contract = ContractSchema


def _domain_payload(schema: DomainSchema) -> dict[str, Any]:
    return {
        "name": schema.name,
        "description": schema.description,
        "namespace": schema.namespace,
        "source_format": schema.source_format,
        "source_dialect": schema.source_dialect,
        "behaviors": list(schema.behaviors),
        "tags": list(schema.tags),
        "metadata": _jsonable(schema.metadata),
        "tables": {
            table_name: _table_payload(table)
            for table_name, table in sorted(schema.tables.items(), key=lambda item: item[0])
        },
    }


def _contract_payload(schema: ContractSchema) -> dict[str, Any]:
    return {
        "name": schema.name,
        "description": schema.description,
        "namespace": schema.namespace,
        "source_format": schema.source_format,
        "source_dialect": schema.source_dialect,
        "tags": list(schema.tags),
        "metadata": _jsonable(schema.metadata),
        "tables": {
            table_name: _table_payload(table)
            for table_name, table in sorted(schema.tables.items(), key=lambda item: item[0])
        },
    }


def _table_payload(table: TableSchema) -> dict[str, Any]:
    return {
        "name": table.name,
        "qualified_name": table.qualified_name,
        "namespace": table.namespace,
        "primary_key": table.primary_key,
        "primary_key_columns": list(table.primary_key_columns),
        "description": table.description,
        "tags": list(table.tags),
        "metadata": _jsonable(table.metadata),
        "columns": [_column_payload(column) for column in table.columns],
        "unique_constraints": [
            {"name": constraint.name, "columns": list(constraint.columns)}
            for constraint in table.unique_constraints
        ],
        "checks": [
            {
                "name": check.name,
                "expression": check.expression,
                "columns": list(check.columns),
            }
            for check in table.checks
        ],
        "foreign_keys": [_foreign_key_payload(fk) for fk in table.foreign_keys],
    }


def _column_payload(column: ColumnSpec) -> dict[str, Any]:
    return {
        "name": column.name,
        "dtype": column.dtype,
        "nullable": column.nullable,
        "description": column.description,
        "original_type": column.original_type,
        "logical_type": column.logical_type,
        "semantic_type": column.semantic_type,
        "default_expression": column.default_expression,
        "precision": column.precision,
        "scale": column.scale,
        "max_length": column.max_length,
        "min_value": _jsonable(column.min_value),
        "max_value": _jsonable(column.max_value),
        "accepted_values": [_jsonable(value) for value in column.accepted_values],
        "tags": list(column.tags),
        "metadata": _jsonable(column.metadata),
    }


def _foreign_key_payload(fk: ForeignKey) -> dict[str, Any]:
    return {
        "constraint_name": fk.constraint_name,
        "column": fk.column,
        "parent_table": fk.parent_table,
        "parent_column": fk.parent_column,
        "child_table": fk.child_table,
        "child_columns": list(fk.child_columns),
        "parent_columns": list(fk.parent_columns),
        "nullable": fk.nullable,
        "on_update": fk.on_update,
        "on_delete": fk.on_delete,
        "metadata": _jsonable(fk.metadata),
    }


def _freeze_value(value: Any) -> Any:
    if isinstance(value, FrozenDict):
        return value
    if isinstance(value, Mapping):
        return FrozenDict(value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze_value(item) for item in value), key=repr))
    return value


def _hashable_value(value: Any) -> Any:
    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

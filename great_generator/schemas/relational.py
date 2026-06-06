"""Custom relational schema parsing for user-defined multi-table datasets."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from great_generator.schemas.generation import (
    _infer_primary_key,
    _split_top_level,
    normalize_single_table_schema,
)
from great_generator.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema

_RELATIONSHIP_RE = re.compile(
    r"^\s*(?P<table>[A-Za-z_][\w]*)\.(?P<column>[A-Za-z_][\w]*)\s*"
    r"(?:->|references)\s*"
    r"(?P<parent_table>[A-Za-z_][\w]*)"
    r"(?:\.(?P<parent_column>[A-Za-z_][\w]*)|\(\s*(?P<paren_column>[A-Za-z_][\w]*)\s*\))"
    r"\s*$",
    re.IGNORECASE,
)

_INLINE_REFERENCE_RE = re.compile(
    r"\breferences\s+"
    r"(?P<parent_table>[A-Za-z_][\w]*)"
    r"(?:\s*\.\s*(?P<parent_column>[A-Za-z_][\w]*)|\s*\(\s*(?P<paren_column>[A-Za-z_][\w]*)\s*\))",
    re.IGNORECASE,
)


def relational_schema_from_specs(
    tables: Mapping[str, Any],
    rows: Mapping[str, int] | int | None = None,
    relationships: Sequence[str | Mapping[str, str]] | None = None,
    name: str = "custom_relational",
) -> tuple[DomainSchema, dict[str, int]]:
    """Build a DomainSchema and row-count map from user-provided table specs.

    Supported table forms:
    - ``{"customers": "customer_id int primary key, name string"}``
    - ``{"customers": {"schema": "...", "rows": 1000}}``
    - ``{"customers": {"schema": pandas_dataframe, "rows": 1000}}``
    - ``{"customers": TableSchema(...)}``

    Relationships can be supplied inline with ``references`` in schema strings or
    separately as strings like ``"orders.customer_id -> customers.customer_id"``.
    """

    if not tables:
        raise ValueError("generate_relational requires at least one table.")

    default_rows, row_overrides = _normalize_rows(rows)
    parsed_tables: dict[str, TableSchema] = {}
    parsed_counts: dict[str, int] = {}
    parsed_foreign_keys: dict[str, list[ForeignKey]] = {}

    for table_name, spec in tables.items():
        if not table_name or not str(table_name).strip():
            raise ValueError("Table names cannot be empty.")
        normalized_name = str(table_name).strip()
        table, inline_fks, table_rows = _parse_table_spec(normalized_name, spec)
        parsed_tables[normalized_name] = table
        parsed_foreign_keys[normalized_name] = list(inline_fks)
        parsed_counts[normalized_name] = _resolve_table_rows(
            normalized_name,
            table_rows=table_rows,
            row_overrides=row_overrides,
            default_rows=default_rows,
        )

    for relationship in relationships or ():
        child_table, foreign_key = _parse_relationship(relationship)
        if child_table not in parsed_tables:
            raise ValueError(
                f"Relationship references unknown child table '{child_table}'. "
                f"Available tables: {sorted(parsed_tables)}."
            )
        parsed_foreign_keys[child_table].append(foreign_key)

    resolved_tables = {
        table_name: _with_validated_foreign_keys(
            table_name,
            table,
            parsed_foreign_keys.get(table_name, []),
            parsed_tables,
        )
        for table_name, table in parsed_tables.items()
    }

    return (
        DomainSchema(
            name=name,
            tables=resolved_tables,
            description="User-defined relational schema.",
            behaviors=(
                "custom table schemas",
                "valid primary keys",
                "valid foreign keys",
                "table-per-name DataFrame output",
            ),
        ),
        parsed_counts,
    )


def _normalize_rows(rows: Mapping[str, int] | int | None) -> tuple[int, Mapping[str, int]]:
    if rows is None:
        return 100, {}
    if isinstance(rows, Mapping):
        return 100, rows
    return _validate_row_count("rows", rows), {}


def _resolve_table_rows(
    table_name: str,
    table_rows: int | None,
    row_overrides: Mapping[str, int],
    default_rows: int,
) -> int:
    if table_rows is not None:
        return _validate_row_count(f"tables['{table_name}']['rows']", table_rows)
    if table_name in row_overrides:
        return _validate_row_count(f"rows['{table_name}']", row_overrides[table_name])
    return default_rows


def _validate_row_count(label: str, value: Any) -> int:
    count = int(value)
    if count < 0:
        raise ValueError(f"{label} must be greater than or equal to zero.")
    return count


def _parse_table_spec(
    table_name: str,
    spec: Any,
) -> tuple[TableSchema, tuple[ForeignKey, ...], int | None]:
    rows: int | None = None
    primary_key_override: str | None = None

    if isinstance(spec, Mapping):
        schema_input = spec.get("schema", spec.get("columns"))
        if schema_input is None:
            raise ValueError(
                f"Table '{table_name}' must provide a 'schema' value when using a mapping spec."
            )
        if "rows" in spec:
            rows = _validate_row_count(f"tables['{table_name}']['rows']", spec["rows"])
        elif "num_rows" in spec:
            rows = _validate_row_count(f"tables['{table_name}']['num_rows']", spec["num_rows"])
        primary_key_override = _optional_string(spec.get("primary_key", spec.get("pk")))
    else:
        schema_input = spec

    if isinstance(schema_input, str):
        table, inline_fks = _table_schema_from_relational_ddl(schema_input, table_name)
    else:
        table, _source = normalize_single_table_schema(schema_input, table_name=table_name)
        inline_fks = ()

    if primary_key_override is not None:
        _ensure_column(table_name, table, primary_key_override)
        table = TableSchema(
            name=table_name,
            columns=table.columns,
            primary_key=primary_key_override,
            foreign_keys=table.foreign_keys,
            description=table.description,
        )

    return _rename_table(table, table_name), inline_fks, rows


def _table_schema_from_relational_ddl(
    schema: str,
    table_name: str,
) -> tuple[TableSchema, tuple[ForeignKey, ...]]:
    text = schema.strip()
    if not text:
        raise ValueError(f"Schema for table '{table_name}' cannot be empty.")
    lower = text.lower()
    if lower.startswith("struct<") and text.endswith(">"):
        text = text[len("struct<") : -1]

    columns: list[ColumnSpec] = []
    inline_fks: list[ForeignKey] = []
    primary_key: str | None = None

    for part in _split_top_level(text):
        column, is_primary_key, foreign_key = _parse_relational_column_spec(part)
        columns.append(column)
        if is_primary_key:
            if primary_key is not None:
                raise ValueError(
                    f"Table '{table_name}' defines multiple primary keys: "
                    f"'{primary_key}' and '{column.name}'."
                )
            primary_key = column.name
        if foreign_key is not None:
            inline_fks.append(foreign_key)

    if not columns:
        raise ValueError(f"Schema for table '{table_name}' must define at least one column.")

    primary_key = primary_key or _infer_primary_key([column.name for column in columns])
    columns = [
        ColumnSpec(
            name=column.name,
            dtype=column.dtype,
            nullable=False if column.name == primary_key else column.nullable,
            description=column.description,
        )
        for column in columns
    ]

    return (
        TableSchema(
            name=table_name,
            columns=tuple(columns),
            primary_key=primary_key,
            foreign_keys=tuple(inline_fks),
            description="Parsed from relational schema string.",
        ),
        tuple(inline_fks),
    )


def _parse_relational_column_spec(part: str) -> tuple[ColumnSpec, bool, ForeignKey | None]:
    cleaned = part.strip()
    if not cleaned:
        raise ValueError("Schema string contains an empty column definition.")

    pieces = cleaned.split(None, 1)
    if len(pieces) != 2:
        raise ValueError(f"Invalid column definition '{part}'. Expected '<name> <type>'.")

    name = pieces[0].strip().strip('`"')
    rest = pieces[1].strip()
    if not name or not rest:
        raise ValueError(f"Invalid column definition '{part}'.")

    is_primary_key = bool(re.search(r"\bprimary\s+key\b", rest, flags=re.IGNORECASE))
    nullable = "not null" not in rest.lower() and not is_primary_key

    reference_match = _INLINE_REFERENCE_RE.search(rest)
    foreign_key = None
    if reference_match is not None:
        foreign_key = ForeignKey(
            column=name,
            parent_table=reference_match.group("parent_table"),
            parent_column=reference_match.group("parent_column")
            or reference_match.group("paren_column"),
        )

    dtype = _clean_dtype(rest)
    if not dtype:
        raise ValueError(f"Column '{name}' has no type after removing constraints.")
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable), is_primary_key, foreign_key


def _clean_dtype(value: str) -> str:
    cleaned = re.sub(r"\bprimary\s+key\b", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bforeign\s+key\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = _INLINE_REFERENCE_RE.sub("", cleaned)
    cleaned = re.sub(r"\bnot\s+null\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnullable\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnull\b", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip()


def _parse_relationship(relationship: str | Mapping[str, str]) -> tuple[str, ForeignKey]:
    if isinstance(relationship, str):
        match = _RELATIONSHIP_RE.match(relationship)
        if match is None:
            raise ValueError(
                "Relationship strings must look like "
                "'orders.customer_id -> customers.customer_id'."
            )
        return match.group("table"), ForeignKey(
            column=match.group("column"),
            parent_table=match.group("parent_table"),
            parent_column=match.group("parent_column") or match.group("paren_column"),
        )

    if isinstance(relationship, Mapping):
        child_table = _required_string(relationship, "table", fallback="child_table")
        column = _required_string(relationship, "column", fallback="child_column")
        parent_table = _required_string(relationship, "parent_table")
        parent_column = _required_string(relationship, "parent_column")
        return child_table, ForeignKey(
            column=column,
            parent_table=parent_table,
            parent_column=parent_column,
        )

    raise TypeError("relationships must be strings or mapping objects.")


def _with_validated_foreign_keys(
    table_name: str,
    table: TableSchema,
    foreign_keys: Sequence[ForeignKey],
    all_tables: Mapping[str, TableSchema],
) -> TableSchema:
    seen: set[tuple[str, str, str]] = set()
    valid_fks: list[ForeignKey] = []

    for fk in foreign_keys:
        _ensure_column(table_name, table, fk.column)
        if fk.parent_table not in all_tables:
            raise ValueError(
                f"Foreign key '{table_name}.{fk.column}' references unknown parent table "
                f"'{fk.parent_table}'. Available tables: {sorted(all_tables)}."
            )
        parent = all_tables[fk.parent_table]
        _ensure_column(fk.parent_table, parent, fk.parent_column)
        identity = (fk.column, fk.parent_table, fk.parent_column)
        if identity not in seen:
            valid_fks.append(fk)
            seen.add(identity)

    return TableSchema(
        name=table.name,
        columns=table.columns,
        primary_key=table.primary_key,
        foreign_keys=tuple(valid_fks),
        description=table.description,
    )


def _rename_table(table: TableSchema, table_name: str) -> TableSchema:
    if table.name == table_name:
        return table
    return TableSchema(
        name=table_name,
        columns=table.columns,
        primary_key=table.primary_key,
        foreign_keys=table.foreign_keys,
        description=table.description,
    )


def _ensure_column(table_name: str, table: TableSchema, column_name: str) -> None:
    if column_name not in table.column_names():
        raise ValueError(
            f"Column '{column_name}' does not exist in table '{table_name}'. "
            f"Available columns: {table.column_names()}."
        )


def _required_string(mapping: Mapping[str, str], key: str, fallback: str | None = None) -> str:
    value = mapping.get(key)
    if value is None and fallback is not None:
        value = mapping.get(fallback)
    text = _optional_string(value)
    if text is None:
        expected = f"'{key}'" if fallback is None else f"'{key}' or '{fallback}'"
        raise ValueError(f"Relationship mapping must include {expected}.")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

"""SQL CREATE TABLE ingestion for canonical contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from great_generator.contracts.diagnostics import (
    ContractDiagnostic,
    ContractParseError,
    SourceLocation,
)
from great_generator.contracts.parsers import ParseResult
from great_generator.schemas.models import (
    CheckConstraint,
    ColumnSpec,
    ContractSchema,
    ForeignKey,
    TableSchema,
    UniqueConstraint,
)

SUPPORTED_DIALECTS = {"ansi", "spark", "databricks"}
CONTRACT_FORMAT = "sql_ddl"


class SQLDDLParser:
    """Parse a tested SQL ``CREATE TABLE`` subset into a canonical contract."""

    source_format = CONTRACT_FORMAT

    def parse(
        self,
        source: str,
        *,
        dialect: str | None = "ansi",
        strict: bool = True,
        name: str = "ddl_contract",
    ) -> ParseResult:
        """Parse SQL DDL into a canonical contract."""

        ddl = str(source or "").strip()
        if not ddl:
            diagnostic = self._diagnostic(
                statement="",
                dialect=dialect,
                construct="empty_source",
                message="DDL text cannot be empty.",
                severity="error",
                recommendation="Pass one or more CREATE TABLE statements.",
            )
            raise ContractParseError("DDL parsing failed.", [diagnostic])

        normalized_dialect = _normalize_dialect(dialect)
        read_dialect = _sqlglot_read_dialect(normalized_dialect)
        statements = _split_sql_statements(ddl)
        diagnostics: list[ContractDiagnostic] = []

        try:
            expressions = sqlglot.parse(ddl, read=read_dialect)
        except ParseError as exc:
            diagnostic = self._diagnostic(
                statement=ddl,
                dialect=normalized_dialect,
                construct="parse_error",
                message=f"SQL parser could not parse the DDL: {exc}",
                severity="error",
                recommendation=(
                    "Check SQL syntax or choose dialect='spark' or dialect='databricks' "
                    "for Spark-style DDL."
                ),
            )
            raise ContractParseError("DDL parsing failed.", [diagnostic]) from exc

        tables: dict[str, TableSchema] = {}
        contract_namespace: str | None = None
        for index, expression in enumerate(expressions):
            statement = statements[index] if index < len(statements) else str(expression or "")
            if expression is None:
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=normalized_dialect,
                        construct="empty_statement",
                        message="SQL parser returned an empty statement.",
                        severity="error",
                        recommendation="Remove empty SQL statements from the DDL text.",
                    )
                )
                continue
            if not isinstance(expression, exp.Create):
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=normalized_dialect,
                        construct=expression.__class__.__name__,
                        message="Only CREATE TABLE statements are supported in M1A DDL ingestion.",
                        severity="error",
                        recommendation="Remove non-CREATE TABLE statements or parse them separately.",
                    )
                )
                continue
            table = self._parse_create_table(
                expression,
                statement=statement,
                dialect=normalized_dialect,
                read_dialect=read_dialect,
                strict=strict,
                diagnostics=diagnostics,
            )
            if table is None:
                continue
            table_key = table.qualified_name
            if table_key in tables:
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=normalized_dialect,
                        construct="duplicate_table",
                        message=f"DDL defines table '{table_key}' more than once.",
                        severity="error",
                        table=table_key,
                        recommendation="Keep one CREATE TABLE statement per table in a contract.",
                    )
                )
                continue
            tables[table_key] = table
            contract_namespace = _merge_namespace(contract_namespace, table.namespace)

        errors = [item for item in diagnostics if item.severity == "error"]
        if errors:
            raise ContractParseError("DDL parsing failed.", errors)
        if not tables:
            diagnostic = self._diagnostic(
                statement=ddl,
                dialect=normalized_dialect,
                construct="no_tables",
                message="No supported CREATE TABLE statements were found.",
                severity="error",
                recommendation="Pass one or more CREATE TABLE statements.",
            )
            raise ContractParseError("DDL parsing failed.", [diagnostic])

        metadata: dict[str, Any] = {"statement_count": len(tables)}
        if diagnostics:
            metadata["diagnostics"] = [diagnostic.to_dict() for diagnostic in diagnostics]
        contract = ContractSchema(
            name=name,
            namespace=contract_namespace,
            tables=tables,
            description="Parsed from SQL CREATE TABLE DDL.",
            source_format=self.source_format,
            source_dialect=normalized_dialect,
            metadata=metadata,
        )
        return ParseResult(
            contract=contract,
            diagnostics=tuple(diagnostics),
            source_format=self.source_format,
            dialect=normalized_dialect,
        )

    def _parse_create_table(
        self,
        create: exp.Create,
        *,
        statement: str,
        dialect: str,
        read_dialect: str | None,
        strict: bool,
        diagnostics: list[ContractDiagnostic],
    ) -> TableSchema | None:
        kind = str(create.args.get("kind") or "").upper()
        if kind and kind != "TABLE":
            diagnostics.append(
                self._diagnostic(
                    statement=statement,
                    dialect=dialect,
                    construct=f"CREATE {kind}",
                    message="Only CREATE TABLE statements are supported.",
                    severity="error",
                    recommendation="Use CREATE TABLE DDL for contract ingestion.",
                )
            )
            return None
        if create.args.get("expression") is not None:
            diagnostics.append(
                self._diagnostic(
                    statement=statement,
                    dialect=dialect,
                    construct="create_table_as_select",
                    message=(
                        "CREATE TABLE AS SELECT is not supported because it does not provide "
                        "a stable column contract."
                    ),
                    severity="error",
                    recommendation="Provide explicit column definitions in CREATE TABLE syntax.",
                )
            )
            return None

        schema_expr = create.args.get("this")
        if not isinstance(schema_expr, exp.Schema) or not isinstance(schema_expr.this, exp.Table):
            diagnostics.append(
                self._diagnostic(
                    statement=statement,
                    dialect=dialect,
                    construct="create_table_target",
                    message="Could not identify the CREATE TABLE target and column list.",
                    severity="error",
                    recommendation="Use CREATE TABLE table_name (column type, ...).",
                )
            )
            return None

        table_ref = _table_reference(schema_expr.this)
        raw_type_map = _raw_column_type_map(statement)
        columns: list[ColumnSpec] = []
        primary_key_columns: list[str] = []
        unique_constraints: list[UniqueConstraint] = []
        checks: list[CheckConstraint] = []
        pending_foreign_keys: list[ForeignKey] = []
        table_metadata: dict[str, Any] = {}
        table_description = "Parsed from SQL CREATE TABLE DDL."

        for item in schema_expr.expressions:
            if isinstance(item, exp.ColumnDef):
                (
                    column,
                    inline_primary_key,
                    inline_unique,
                    inline_checks,
                    inline_fks,
                ) = self._parse_column(
                    item,
                    table_ref=table_ref,
                    statement=statement,
                    dialect=dialect,
                    read_dialect=read_dialect,
                    strict=strict,
                    raw_type_map=raw_type_map,
                    diagnostics=diagnostics,
                )
                columns.append(column)
                if inline_primary_key:
                    primary_key_columns.append(column.name)
                unique_constraints.extend(inline_unique)
                checks.extend(inline_checks)
                pending_foreign_keys.extend(inline_fks)
                continue
            self._parse_table_constraint(
                item,
                table_ref=table_ref,
                statement=statement,
                dialect=dialect,
                read_dialect=read_dialect,
                strict=strict,
                primary_key_columns=primary_key_columns,
                unique_constraints=unique_constraints,
                checks=checks,
                foreign_keys=pending_foreign_keys,
                diagnostics=diagnostics,
            )

        if not columns:
            diagnostics.append(
                self._diagnostic(
                    statement=statement,
                    dialect=dialect,
                    construct="empty_table",
                    message=f"Table '{table_ref.qualified_name}' does not define any columns.",
                    severity="error",
                    table=table_ref.qualified_name,
                    recommendation="Add at least one column definition.",
                )
            )
            return None

        column_names = {column.name for column in columns}
        for pk_column in primary_key_columns:
            if pk_column not in column_names:
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=dialect,
                        construct="primary_key",
                        message=(
                            f"Primary key column '{pk_column}' is not defined on table "
                            f"'{table_ref.qualified_name}'."
                        ),
                        severity="error",
                        table=table_ref.qualified_name,
                        recommendation="Ensure all primary key columns appear in the table definition.",
                    )
                )
        for duplicate in _duplicates([column.name for column in columns]):
            diagnostics.append(
                self._diagnostic(
                    statement=statement,
                    dialect=dialect,
                    construct="duplicate_column",
                    message=(
                        f"Column '{duplicate}' is defined more than once on table "
                        f"'{table_ref.qualified_name}'."
                    ),
                    severity="error",
                    table=table_ref.qualified_name,
                    column=duplicate,
                    recommendation="Keep one definition per column.",
                )
            )

        pk_set = set(primary_key_columns)
        if pk_set:
            columns = [
                _replace_column(column, nullable=False) if column.name in pk_set else column
                for column in columns
            ]

        nullable_by_column = {column.name: column.nullable for column in columns}
        foreign_keys = tuple(
            _replace_foreign_key(
                fk,
                nullable=any(nullable_by_column.get(column, True) for column in fk.child_columns),
            )
            for fk in pending_foreign_keys
        )

        description = _parse_table_properties(
            create,
            table_metadata=table_metadata,
            current_description=table_description,
            statement=statement,
            dialect=dialect,
            diagnostics=diagnostics,
        )

        return TableSchema(
            name=table_ref.name,
            namespace=table_ref.namespace,
            columns=tuple(columns),
            primary_key=primary_key_columns[0] if primary_key_columns else None,
            primary_key_columns=tuple(primary_key_columns),
            foreign_keys=foreign_keys,
            unique_constraints=tuple(unique_constraints),
            checks=tuple(checks),
            description=description,
            metadata=table_metadata,
        )

    def _parse_column(
        self,
        column_def: exp.ColumnDef,
        *,
        table_ref: TableReference,
        statement: str,
        dialect: str,
        read_dialect: str | None,
        strict: bool,
        raw_type_map: Mapping[str, str],
        diagnostics: list[ContractDiagnostic],
    ) -> tuple[ColumnSpec, bool, list[UniqueConstraint], list[CheckConstraint], list[ForeignKey]]:
        column_name = _identifier_name(column_def.this)
        original_type = raw_type_map.get(column_name) or _data_type_sql(
            column_def.args.get("kind"), read_dialect
        )
        dtype, precision, scale, max_length = _normalize_type(
            column_def.args.get("kind"),
            original_type=original_type,
            statement=statement,
            dialect=dialect,
            table=table_ref.qualified_name,
            column=column_name,
            diagnostics=diagnostics,
        )
        nullable = True
        default_expression: str | None = None
        description = ""
        is_primary_key = False
        unique_constraints: list[UniqueConstraint] = []
        checks: list[CheckConstraint] = []
        foreign_keys: list[ForeignKey] = []

        for constraint in column_def.args.get("constraints") or []:
            kind = constraint.args.get("kind")
            kind_name = (
                kind.__class__.__name__ if kind is not None else constraint.__class__.__name__
            )
            if kind_name == "PrimaryKeyColumnConstraint":
                is_primary_key = True
                nullable = False
            elif kind_name == "NotNullColumnConstraint":
                nullable = bool(kind.args.get("allow_null"))
            elif kind_name == "DefaultColumnConstraint":
                default_expression = _expression_sql(kind.args.get("this"), read_dialect)
            elif kind_name == "UniqueColumnConstraint":
                unique_constraints.append(UniqueConstraint(columns=(column_name,)))
            elif kind_name == "Reference":
                foreign_keys.append(
                    _foreign_key_from_reference(
                        kind,
                        child_table=table_ref,
                        child_columns=(column_name,),
                        constraint_name=None,
                    )
                )
            elif kind_name == "CheckColumnConstraint":
                expression = _expression_sql(kind.args.get("this"), read_dialect)
                checks.append(CheckConstraint(expression=expression, columns=(column_name,)))
            elif kind_name == "CommentColumnConstraint":
                description = _literal_text(kind.args.get("this")) or ""
            else:
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=dialect,
                        construct=kind_name,
                        message=(
                            f"Column constraint '{kind_name}' on "
                            f"'{table_ref.qualified_name}.{column_name}' is not supported "
                            "in the canonical contract subset."
                        ),
                        severity="error" if strict else "warning",
                        table=table_ref.qualified_name,
                        column=column_name,
                        location=_location(column_def),
                        recommendation=(
                            "Remove the unsupported constraint or parse with strict=False if "
                            "the base column contract is sufficient."
                        ),
                    )
                )

        column = ColumnSpec(
            name=column_name,
            dtype=dtype,
            nullable=nullable,
            description=description,
            original_type=original_type,
            precision=precision,
            scale=scale,
            max_length=max_length,
            default_expression=default_expression,
            metadata={"source_type_sql": _data_type_sql(column_def.args.get("kind"), read_dialect)},
        )
        return column, is_primary_key, unique_constraints, checks, foreign_keys

    def _parse_table_constraint(
        self,
        item: exp.Expression,
        *,
        table_ref: TableReference,
        statement: str,
        dialect: str,
        read_dialect: str | None,
        strict: bool,
        primary_key_columns: list[str],
        unique_constraints: list[UniqueConstraint],
        checks: list[CheckConstraint],
        foreign_keys: list[ForeignKey],
        diagnostics: list[ContractDiagnostic],
    ) -> None:
        constraint_name: str | None = None
        expressions: list[exp.Expression]
        if isinstance(item, exp.Constraint):
            constraint_name = (
                _identifier_name(item.args.get("this"))
                if item.args.get("this") is not None
                else None
            )
            expressions = list(item.expressions)
        else:
            expressions = [item]

        for expression in expressions:
            kind_name = expression.__class__.__name__
            if isinstance(expression, exp.Identifier):
                column_name = _identifier_name(expression)
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=dialect,
                        construct="missing_type",
                        message=(
                            f"Column '{table_ref.qualified_name}.{column_name}' does not have "
                            "a supported SQL type."
                        ),
                        severity="error",
                        table=table_ref.qualified_name,
                        column=column_name,
                        location=_location(expression),
                        recommendation="Use '<column_name> <scalar_type>' in CREATE TABLE.",
                    )
                )
                continue
            if isinstance(expression, exp.PrimaryKey):
                primary_key_columns.extend(_identifier_list(expression.expressions))
            elif isinstance(expression, exp.ForeignKey):
                child_columns = tuple(_identifier_list(expression.expressions))
                reference = expression.args.get("reference")
                if not isinstance(reference, exp.Reference):
                    diagnostics.append(
                        self._diagnostic(
                            statement=statement,
                            dialect=dialect,
                            construct="foreign_key_reference",
                            message=(
                                f"Foreign key on '{table_ref.qualified_name}' does not include "
                                "a supported REFERENCES target."
                            ),
                            severity="error",
                            table=table_ref.qualified_name,
                            recommendation="Use FOREIGN KEY (...) REFERENCES parent_table(...).",
                        )
                    )
                    continue
                foreign_keys.append(
                    _foreign_key_from_reference(
                        reference,
                        child_table=table_ref,
                        child_columns=child_columns,
                        constraint_name=constraint_name,
                    )
                )
            elif isinstance(expression, exp.UniqueColumnConstraint):
                unique_constraints.append(
                    UniqueConstraint(
                        name=constraint_name,
                        columns=tuple(_constraint_columns(expression)),
                    )
                )
            elif kind_name == "CheckColumnConstraint":
                checks.append(
                    CheckConstraint(
                        name=constraint_name,
                        expression=_expression_sql(expression.args.get("this"), read_dialect),
                        columns=tuple(_columns_in_expression(expression.args.get("this"))),
                    )
                )
            else:
                diagnostics.append(
                    self._diagnostic(
                        statement=statement,
                        dialect=dialect,
                        construct=kind_name,
                        message=(
                            f"Table constraint '{kind_name}' on '{table_ref.qualified_name}' "
                            "is not supported in the canonical contract subset."
                        ),
                        severity="error" if strict else "warning",
                        table=table_ref.qualified_name,
                        location=_location(expression),
                        recommendation=(
                            "Use PRIMARY KEY, FOREIGN KEY, UNIQUE, or CHECK constraints "
                            "for M1A DDL ingestion."
                        ),
                    )
                )

    def _diagnostic(
        self,
        *,
        statement: str,
        dialect: str | None,
        construct: str,
        message: str,
        severity: str,
        table: str | None = None,
        column: str | None = None,
        location: SourceLocation | None = None,
        recommendation: str | None = None,
    ) -> ContractDiagnostic:
        return ContractDiagnostic(
            statement=statement.strip(),
            dialect=dialect,
            construct=construct,
            message=message,
            severity=severity,
            table=table,
            column=column,
            location=location,
            recommendation=recommendation,
        )


def parse_ddl(
    ddl_text: str,
    *,
    dialect: str | None = "ansi",
    strict: bool = True,
    name: str = "ddl_contract",
) -> ContractSchema:
    """Parse SQL ``CREATE TABLE`` DDL into a canonical contract."""

    return SQLDDLParser().parse(ddl_text, dialect=dialect, strict=strict, name=name).contract


class TableReference:
    """Normalized table name pieces from sqlglot."""

    def __init__(self, name: str, namespace: str | None) -> None:
        self.name = name
        self.namespace = namespace

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.name}" if self.namespace else self.name


_TYPE_ALIASES = {
    "INT": "int",
    "INTEGER": "int",
    "SMALLINT": "int",
    "TINYINT": "int",
    "BYTE": "int",
    "SHORT": "int",
    "BIGINT": "bigint",
    "LONG": "bigint",
    "STRING": "string",
    "TEXT": "string",
    "VARCHAR": "string",
    "CHAR": "string",
    "CHARACTER": "string",
    "NCHAR": "string",
    "NVARCHAR": "string",
    "DECIMAL": "decimal",
    "DEC": "decimal",
    "NUMERIC": "decimal",
    "NUMBER": "decimal",
    "DOUBLE": "double",
    "FLOAT": "double",
    "REAL": "double",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
    "TIMESTAMPTZ": "timestamp",
    "TIMESTAMPNTZ": "timestamp",
    "TIMESTAMP_NTZ": "timestamp",
    "TIMESTAMP_LTZ": "timestamp",
    "DATETIME": "timestamp",
    "BINARY": "binary",
    "VARBINARY": "binary",
}


def _normalize_dialect(dialect: str | None) -> str:
    normalized = (dialect or "ansi").strip().lower()
    if normalized not in SUPPORTED_DIALECTS:
        supported = ", ".join(sorted(SUPPORTED_DIALECTS))
        raise ValueError(f"Unsupported DDL dialect '{dialect}'. Supported dialects: {supported}.")
    return normalized


def _sqlglot_read_dialect(dialect: str) -> str | None:
    return None if dialect == "ansi" else dialect


def _merge_namespace(current: str | None, candidate: str | None) -> str | None:
    if current is None:
        return candidate
    if candidate is None or candidate == current:
        return current
    return None


def _table_reference(table: exp.Table) -> TableReference:
    parts = [_identifier_name(part) for part in table.parts]
    if not parts:
        raise ValueError("Table expression did not contain a table name.")
    return TableReference(name=parts[-1], namespace=".".join(parts[:-1]) or None)


def _identifier_name(identifier: Any) -> str:
    if isinstance(identifier, exp.Column):
        return _identifier_name(identifier.this)
    if isinstance(identifier, exp.Identifier):
        text = str(identifier.this)
        return text if bool(identifier.args.get("quoted")) else text.lower()
    if isinstance(identifier, exp.Var):
        return str(identifier.this).lower()
    if isinstance(identifier, exp.Dot):
        return identifier.sql().lower()
    return str(identifier).strip('`"').lower()


def _identifier_list(expressions: list[exp.Expression] | tuple[exp.Expression, ...]) -> list[str]:
    return [_identifier_name(expression) for expression in expressions]


def _constraint_columns(expression: exp.UniqueColumnConstraint) -> list[str]:
    target = expression.args.get("this")
    if isinstance(target, exp.Schema):
        return _identifier_list(list(target.expressions))
    if target is not None:
        return [_identifier_name(target)]
    return []


def _foreign_key_from_reference(
    reference: exp.Reference,
    *,
    child_table: TableReference,
    child_columns: tuple[str, ...],
    constraint_name: str | None,
) -> ForeignKey:
    schema_expr = reference.args.get("this")
    if not isinstance(schema_expr, exp.Schema) or not isinstance(schema_expr.this, exp.Table):
        raise ValueError("Unsupported foreign-key REFERENCES target.")
    parent_ref = _table_reference(schema_expr.this)
    if parent_ref.namespace is None and child_table.namespace is not None:
        parent_ref = TableReference(parent_ref.name, child_table.namespace)
    parent_columns = tuple(_identifier_list(list(schema_expr.expressions)))
    on_update, on_delete = _reference_actions(reference)
    return ForeignKey(
        column=child_columns[0] if child_columns else "",
        child_table=child_table.qualified_name,
        child_columns=child_columns,
        parent_table=parent_ref.qualified_name,
        parent_column=parent_columns[0] if parent_columns else "",
        parent_columns=parent_columns,
        constraint_name=constraint_name,
        on_update=on_update,
        on_delete=on_delete,
    )


def _reference_actions(reference: exp.Reference) -> tuple[str | None, str | None]:
    on_update: str | None = None
    on_delete: str | None = None
    for option in reference.args.get("options") or []:
        text = str(option).strip().upper()
        if text.startswith("ON UPDATE "):
            on_update = text.removeprefix("ON UPDATE ").strip()
        elif text.startswith("ON DELETE "):
            on_delete = text.removeprefix("ON DELETE ").strip()
    return on_update, on_delete


def _parse_table_properties(
    create: exp.Create,
    *,
    table_metadata: dict[str, Any],
    current_description: str,
    statement: str,
    dialect: str,
    diagnostics: list[ContractDiagnostic],
) -> str:
    description = current_description
    properties = create.args.get("properties")
    if properties is None:
        return description
    for property_expr in properties.expressions:
        kind_name = property_expr.__class__.__name__
        if kind_name == "FileFormatProperty":
            value = property_expr.args.get("this")
            table_metadata["storage_format"] = _expression_sql(
                value, _sqlglot_read_dialect(dialect)
            )
        elif kind_name == "PartitionedByProperty":
            target = property_expr.args.get("this")
            if isinstance(target, exp.Schema):
                table_metadata["partitioned_by"] = _identifier_list(list(target.expressions))
            else:
                table_metadata["partitioned_by"] = _expression_sql(
                    target, _sqlglot_read_dialect(dialect)
                )
        elif kind_name == "SchemaCommentProperty":
            description = _literal_text(property_expr.args.get("this")) or description
        else:
            diagnostics.append(
                ContractDiagnostic(
                    statement=statement.strip(),
                    dialect=dialect,
                    construct=kind_name,
                    message=(
                        f"Table property '{kind_name}' is preserved as a warning but is not "
                        "part of M1A generation semantics."
                    ),
                    severity="warning",
                    recommendation=(
                        "Store non-generation storage options outside the contract or keep them "
                        "in metadata."
                    ),
                )
            )
            table_metadata.setdefault("unsupported_properties", []).append(property_expr.sql())
    return description


def _normalize_type(
    data_type: Any,
    *,
    original_type: str,
    statement: str,
    dialect: str,
    table: str,
    column: str,
    diagnostics: list[ContractDiagnostic],
) -> tuple[str, int | None, int | None, int | None]:
    if not isinstance(data_type, exp.DataType):
        diagnostics.append(
            ContractDiagnostic(
                statement=statement.strip(),
                dialect=dialect,
                construct="missing_type",
                message=f"Column '{table}.{column}' does not have a supported SQL type.",
                severity="error",
                table=table,
                column=column,
                recommendation="Provide an explicit scalar SQL type.",
            )
        )
        return "string", None, None, None

    base = _base_type_name(data_type, original_type)
    normalized = _TYPE_ALIASES.get(base)
    if normalized is None:
        diagnostics.append(
            ContractDiagnostic(
                statement=statement.strip(),
                dialect=dialect,
                construct="unsupported_type",
                message=f"Column '{table}.{column}' uses unsupported type '{original_type}'.",
                severity="error",
                table=table,
                column=column,
                location=_location(data_type),
                recommendation=(
                    "Use a supported scalar type such as INT, BIGINT, STRING, DECIMAL, "
                    "DOUBLE, BOOLEAN, DATE, TIMESTAMP, or BINARY."
                ),
            )
        )
        return "string", None, None, None

    parameters = _type_parameters(data_type)
    precision: int | None = None
    scale: int | None = None
    max_length: int | None = None
    if normalized == "decimal":
        precision = parameters[0] if len(parameters) >= 1 else None
        scale = parameters[1] if len(parameters) >= 2 else None
    elif normalized == "string" and base in {"CHAR", "CHARACTER", "VARCHAR", "NCHAR", "NVARCHAR"}:
        max_length = parameters[0] if parameters else None
    return normalized, precision, scale, max_length


def _base_type_name(data_type: exp.DataType, original_type: str) -> str:
    original = original_type.strip().upper().replace("`", "").replace('"', "")
    token = []
    for char in original:
        if char.isalnum() or char == "_":
            token.append(char)
        else:
            break
    if token:
        return "".join(token)
    value = getattr(data_type.this, "value", None)
    return str(value or data_type.this).split(".")[-1].upper()


def _type_parameters(data_type: exp.DataType) -> list[int]:
    values: list[int] = []
    for parameter in data_type.expressions:
        raw = parameter.args.get("this")
        if raw is None:
            continue
        text = getattr(raw, "this", raw)
        try:
            values.append(int(str(text)))
        except ValueError:
            continue
    return values


def _data_type_sql(data_type: Any, dialect: str | None) -> str:
    if isinstance(data_type, exp.Expression):
        return data_type.sql(dialect=dialect) if dialect else data_type.sql()
    return ""


def _expression_sql(expression: Any, dialect: str | None) -> str:
    if isinstance(expression, exp.Expression):
        return expression.sql(dialect=dialect) if dialect else expression.sql()
    if expression is None:
        return ""
    return str(expression)


def _literal_text(expression: Any) -> str | None:
    if isinstance(expression, exp.Literal):
        return str(expression.this)
    if expression is None:
        return None
    return str(expression).strip().strip("'") or None


def _columns_in_expression(expression: Any) -> list[str]:
    if not isinstance(expression, exp.Expression):
        return []
    return sorted({_identifier_name(column) for column in expression.find_all(exp.Column)})


def _replace_column(column: ColumnSpec, **changes: Any) -> ColumnSpec:
    values: dict[str, Any] = {
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
        "min_value": column.min_value,
        "max_value": column.max_value,
        "accepted_values": column.accepted_values,
        "tags": column.tags,
        "metadata": column.metadata,
    }
    values.update(changes)
    return ColumnSpec(**values)


def _replace_foreign_key(fk: ForeignKey, **changes: Any) -> ForeignKey:
    values: dict[str, Any] = {
        "column": fk.column,
        "parent_table": fk.parent_table,
        "parent_column": fk.parent_column,
        "constraint_name": fk.constraint_name,
        "child_table": fk.child_table,
        "child_columns": fk.child_columns,
        "parent_columns": fk.parent_columns,
        "nullable": fk.nullable,
        "on_update": fk.on_update,
        "on_delete": fk.on_delete,
        "metadata": fk.metadata,
    }
    values.update(changes)
    return ForeignKey(**values)


def _location(expression: Any) -> SourceLocation | None:
    meta = getattr(expression, "meta", None) or {}
    if not meta:
        return None
    return SourceLocation(
        line=meta.get("line"),
        column=meta.get("col"),
        start=meta.get("start"),
        end=meta.get("end"),
    )


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _split_sql_statements(source: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    single = False
    double = False
    backtick = False
    paren_depth = 0
    for char in source:
        if char == "'" and not double and not backtick:
            single = not single
        elif char == '"' and not single and not backtick:
            double = not double
        elif char == "`" and not single and not double:
            backtick = not backtick
        elif not single and not double and not backtick:
            if char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
        if char == ";" and not single and not double and not backtick and paren_depth == 0:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def _raw_column_type_map(statement: str) -> dict[str, str]:
    body = _create_table_body(statement)
    if body is None:
        return {}
    result: dict[str, str] = {}
    for part in _split_top_level(body):
        stripped = part.strip()
        if not stripped or _looks_like_table_constraint(stripped):
            continue
        parsed = _consume_identifier(stripped)
        if parsed is None:
            continue
        name, rest = parsed
        dtype = _leading_type(rest)
        if dtype:
            result[name] = dtype
    return result


def _create_table_body(statement: str) -> str | None:
    start = statement.find("(")
    if start == -1:
        return None
    depth = 0
    single = False
    double = False
    backtick = False
    for index in range(start, len(statement)):
        char = statement[index]
        if char == "'" and not double and not backtick:
            single = not single
        elif char == '"' and not single and not backtick:
            double = not double
        elif char == "`" and not single and not double:
            backtick = not backtick
        elif not single and not double and not backtick:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return statement[start + 1 : index]
    return None


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    single = False
    double = False
    backtick = False
    for char in text:
        if char == "'" and not double and not backtick:
            single = not single
        elif char == '"' and not single and not backtick:
            double = not double
        elif char == "`" and not single and not double:
            backtick = not backtick
        elif not single and not double and not backtick:
            if char == "<":
                angle_depth += 1
            elif char == ">" and angle_depth:
                angle_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
        if (
            char == ","
            and not single
            and not double
            and not backtick
            and angle_depth == 0
            and paren_depth == 0
        ):
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _looks_like_table_constraint(part: str) -> bool:
    lowered = part.lstrip().lower()
    return lowered.startswith(("constraint ", "primary key", "foreign key", "unique", "check"))


def _consume_identifier(text: str) -> tuple[str, str] | None:
    stripped = text.lstrip()
    if not stripped:
        return None
    quote = stripped[0]
    if quote in {'"', "`"}:
        end = 1
        while end < len(stripped):
            if stripped[end] == quote:
                name = stripped[1:end]
                return name, stripped[end + 1 :].lstrip()
            end += 1
        return None
    pieces = stripped.split(None, 1)
    if not pieces:
        return None
    name = pieces[0].strip().lower()
    rest = pieces[1] if len(pieces) > 1 else ""
    return name, rest.lstrip()


def _leading_type(rest: str) -> str:
    keywords = {
        "not",
        "null",
        "default",
        "primary",
        "references",
        "unique",
        "check",
        "comment",
        "collate",
        "generated",
        "identity",
        "constraint",
    }
    tokens: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    single = False
    double = False
    backtick = False
    index = 0
    while index < len(rest):
        char = rest[index]
        if char == "'" and not double and not backtick:
            single = not single
        elif char == '"' and not single and not backtick:
            double = not double
        elif char == "`" and not single and not double:
            backtick = not backtick
        elif not single and not double and not backtick:
            if char == "<":
                angle_depth += 1
            elif char == ">" and angle_depth:
                angle_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
            if char.isspace() and angle_depth == 0 and paren_depth == 0:
                token = "".join(current).strip()
                if token:
                    if token.lower() in keywords:
                        break
                    tokens.append(token)
                current = []
                index += 1
                continue
        current.append(char)
        index += 1
    token = "".join(current).strip()
    if token and token.lower() not in keywords:
        tokens.append(token)
    return " ".join(tokens).strip()

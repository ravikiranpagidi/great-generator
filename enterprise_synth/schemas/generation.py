"""Schema-driven sample generation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from enterprise_synth.relationships.graph import topological_sort
from enterprise_synth.schemas.models import ColumnSpec, DomainSchema, TableSchema
from enterprise_synth.utils.random import get_rng


def generate_domain_schema_pandas(
    schema: DomainSchema,
    rows: Mapping[str, int] | int,
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate a lightweight relational pandas dataset from DomainSchema metadata."""

    row_counts = _domain_row_counts(schema, rows)
    order = topological_sort(schema.dependencies())
    rng = get_rng(seed, "schema")
    generated: dict[str, pd.DataFrame] = {}

    for table_name in order:
        table = schema.tables[table_name]
        count = int(row_counts.get(table_name, 0))
        frame: dict[str, Any] = {}
        for column in table.columns:
            if column.name == table.primary_key:
                frame[column.name] = np.arange(1, count + 1, dtype=np.int64)
            elif any(fk.column == column.name for fk in table.foreign_keys):
                fk = next(fk for fk in table.foreign_keys if fk.column == column.name)
                parent_values = generated[fk.parent_table][fk.parent_column].to_numpy()
                frame[column.name] = (
                    rng.choice(parent_values, size=count, replace=True)
                    if len(parent_values)
                    else []
                )
            else:
                frame[column.name] = generate_column_values(column, count, rng)
        generated[table_name] = pd.DataFrame(frame)
    return generated


def generate_single_table_pandas(
    schema: TableSchema | pd.DataFrame | str | Any,
    rows: int,
    seed: int | None = None,
    table_name: str = "sample",
) -> pd.DataFrame:
    """Generate a pandas DataFrame from a single-table schema input."""

    table, source = normalize_single_table_schema(schema, table_name=table_name)
    rng = get_rng(seed, f"schema:{table.name}")
    values = {
        column.name: generate_column_values(column, rows, rng, primary_key=table.primary_key)
        for column in table.columns
    }
    frame = pd.DataFrame(values, columns=[column.name for column in table.columns])
    if isinstance(source, pd.DataFrame):
        frame = _cast_like_pandas_schema(frame, source)
    return frame


def generate_single_table_spark(
    schema: TableSchema | pd.DataFrame | str | Any,
    rows: int,
    spark: Any,
    seed: int | None = None,
    table_name: str = "sample",
) -> Any:
    """Generate a Spark DataFrame from a single-table schema input."""

    if spark is None:
        raise ValueError("Spark schema generation requires a SparkSession via spark=...")
    table, source = normalize_single_table_schema(schema, table_name=table_name)
    frame = generate_single_table_pandas(table, rows=rows, seed=seed, table_name=table.name)

    if is_pyspark_struct_type(source):
        records = _records_for_spark_schema(frame, source)
        return spark.createDataFrame(records, schema=source)
    return spark.createDataFrame(frame)


def normalize_single_table_schema(
    schema: TableSchema | pd.DataFrame | str | Any,
    table_name: str = "sample",
) -> tuple[TableSchema, Any]:
    """Normalize supported single-table schema inputs to TableSchema metadata."""

    if isinstance(schema, TableSchema):
        return schema, schema
    if isinstance(schema, pd.DataFrame):
        return table_schema_from_pandas(schema, table_name=table_name), schema
    if isinstance(schema, str):
        return table_schema_from_ddl(schema, table_name=table_name), schema
    if is_pyspark_struct_type(schema):
        return table_schema_from_pyspark(schema, table_name=table_name), schema
    raise TypeError(
        "schema must be a DomainSchema, TableSchema, pandas DataFrame, DDL string, "
        "or PySpark StructType."
    )


def table_schema_from_pandas(frame: pd.DataFrame, table_name: str = "sample") -> TableSchema:
    """Infer TableSchema metadata from a pandas DataFrame, including empty frames."""

    return TableSchema(
        name=table_name,
        columns=tuple(
            ColumnSpec(name=str(column), dtype=str(dtype), nullable=True)
            for column, dtype in frame.dtypes.items()
        ),
        primary_key=_infer_primary_key(frame.columns),
        description="Inferred from pandas DataFrame schema.",
    )


def table_schema_from_pyspark(schema: Any, table_name: str = "sample") -> TableSchema:
    """Infer TableSchema metadata from a PySpark StructType without requiring Spark at import time."""

    return TableSchema(
        name=table_name,
        columns=tuple(
            ColumnSpec(
                name=str(field.name),
                dtype=_spark_type_string(field.dataType),
                nullable=bool(field.nullable),
            )
            for field in schema.fields
        ),
        primary_key=_infer_primary_key([field.name for field in schema.fields]),
        description="Inferred from PySpark StructType schema.",
    )


def table_schema_from_ddl(schema: str, table_name: str = "sample") -> TableSchema:
    """Parse a compact DDL-like schema string such as ``id int, name string``."""

    text = schema.strip()
    if not text:
        raise ValueError("Schema string cannot be empty.")
    lower = text.lower()
    if lower.startswith("struct<") and text.endswith(">"):
        text = text[len("struct<") : -1]

    columns: list[ColumnSpec] = []
    for part in _split_top_level(text):
        column = _parse_column_spec(part)
        columns.append(column)
    if not columns:
        raise ValueError("Schema string must define at least one column.")

    return TableSchema(
        name=table_name,
        columns=tuple(columns),
        primary_key=_infer_primary_key([column.name for column in columns]),
        description="Parsed from schema string.",
    )


def generate_column_values(
    column: ColumnSpec,
    rows: int,
    rng: np.random.Generator,
    primary_key: str | None = None,
) -> list[Any] | np.ndarray | pd.DatetimeIndex:
    """Generate deterministic sample values for one column."""

    if rows < 0:
        raise ValueError("rows must be greater than or equal to zero.")

    dtype = column.dtype.lower()
    kind = _dtype_kind(dtype)
    if column.name == primary_key:
        if kind in {"int", "long"}:
            return np.arange(1, rows + 1, dtype=np.int64)
        return [f"{column.name}_{index:06d}" for index in range(1, rows + 1)]
    if _looks_like_identifier(column.name) and kind in {"int", "long"}:
        return np.arange(1, rows + 1, dtype=np.int64)

    if kind in {"int", "long"}:
        return rng.integers(0, 1000, size=rows)
    if kind in {"float", "decimal"}:
        return np.round(rng.normal(100, 15, size=rows), 2)
    if kind == "date":
        start = date(2025, 1, 1)
        return [start + timedelta(days=index) for index in range(rows)]
    if kind == "timestamp":
        return pd.date_range("2025-01-01", periods=rows, freq="h")
    if kind == "bool":
        return rng.random(rows) < 0.5
    if kind == "binary":
        return [f"{column.name}_{index}".encode() for index in range(1, rows + 1)]
    if kind == "array":
        return [[f"{column.name}_{index}"] for index in range(1, rows + 1)]
    if kind == "map":
        return [{"key": f"{column.name}_{index}"} for index in range(1, rows + 1)]
    if kind == "struct":
        return [{"value": f"{column.name}_{index}"} for index in range(1, rows + 1)]
    return [f"{column.name}_{index}" for index in range(1, rows + 1)]


def is_pyspark_struct_type(schema: Any) -> bool:
    """Return true for PySpark StructType objects without importing PySpark eagerly."""

    return schema.__class__.__name__ == "StructType" and hasattr(schema, "fields")


def _domain_row_counts(schema: DomainSchema, rows: Mapping[str, int] | int) -> Mapping[str, int]:
    if isinstance(rows, Mapping):
        return rows
    count = int(rows)
    return {table_name: count for table_name in schema.tables}


def _infer_primary_key(columns: Any) -> str | None:
    names = [str(column) for column in columns]
    lowered = {name.lower(): name for name in names}
    if "id" in lowered:
        return lowered["id"]
    for name in names:
        lowered_name = name.lower()
        if lowered_name.endswith("_id") and not lowered_name.startswith("parent_"):
            return name
    return None


def _looks_like_identifier(name: str) -> bool:
    lowered = name.lower()
    return lowered == "id" or lowered.endswith("_id")


def _spark_type_string(data_type: Any) -> str:
    if hasattr(data_type, "simpleString"):
        return str(data_type.simpleString())
    return data_type.__class__.__name__


def _dtype_kind(dtype: str) -> str:
    normalized = dtype.lower().strip()
    if normalized.startswith("array"):
        return "array"
    if normalized.startswith("map"):
        return "map"
    if normalized.startswith("struct"):
        return "struct"
    if "bool" in normalized:
        return "bool"
    if "timestamp" in normalized or "datetime" in normalized:
        return "timestamp"
    if normalized == "date" or normalized.endswith("date"):
        return "date"
    if "decimal" in normalized or "numeric" in normalized:
        return "decimal"
    if any(token in normalized for token in ("double", "float", "real")):
        return "float"
    if "bigint" in normalized or "long" in normalized:
        return "long"
    if "int" in normalized and "interval" not in normalized:
        return "int"
    if "binary" in normalized or "bytes" in normalized:
        return "binary"
    return "string"


def _cast_like_pandas_schema(frame: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    casted = frame.copy()
    for column in schema.columns:
        dtype = schema[column].dtype
        try:
            if pd.api.types.is_datetime64_any_dtype(dtype):
                casted[column] = pd.to_datetime(casted[column])
            else:
                casted[column] = casted[column].astype(dtype)
        except (TypeError, ValueError):
            # Some pandas extension/object combinations are intentionally permissive.
            pass
    return casted


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    for char in text:
        if char == "<":
            angle_depth += 1
        elif char == ">" and angle_depth:
            angle_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth:
            paren_depth -= 1

        if char == "," and angle_depth == 0 and paren_depth == 0:
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


def _parse_column_spec(part: str) -> ColumnSpec:
    cleaned = part.strip()
    if not cleaned:
        raise ValueError("Schema string contains an empty column definition.")

    if ":" in cleaned and (" " not in cleaned.split(":", 1)[0].strip()):
        name, dtype = cleaned.split(":", 1)
    else:
        pieces = cleaned.split(None, 1)
        if len(pieces) != 2:
            raise ValueError(f"Invalid column definition '{part}'. Expected '<name> <type>'.")
        name, dtype = pieces

    name = name.strip().strip('`"')
    dtype = dtype.strip()
    nullable = "not null" not in dtype.lower()
    dtype = _strip_nullability(dtype)
    if not name or not dtype:
        raise ValueError(f"Invalid column definition '{part}'.")
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable)


def _strip_nullability(dtype: str) -> str:
    lowered = dtype.lower()
    for marker in (" not null", " nullable", " null"):
        index = lowered.find(marker)
        if index != -1:
            return dtype[:index].strip()
    return dtype.strip()


def _records_for_spark_schema(frame: pd.DataFrame, schema: Any) -> list[dict[str, Any]]:
    raw_records = frame.to_dict(orient="records")
    return [
        {
            field.name: _coerce_value_for_spark(
                raw.get(field.name), _spark_type_string(field.dataType)
            )
            for field in schema.fields
        }
        for raw in raw_records
    ]


def _coerce_value_for_spark(value: Any, dtype: str) -> Any:
    kind = _dtype_kind(dtype)
    if pd.isna(value) if not isinstance(value, (list, dict, bytes, bytearray)) else False:
        return None
    if kind in {"int", "long"}:
        return int(value)
    if kind == "float":
        return float(value)
    if kind == "decimal":
        return Decimal(str(value))
    if kind == "bool":
        return bool(value)
    if kind == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, pd.Timestamp):
            return value.date()
        return value
    if kind == "timestamp":
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime.combine(value, datetime.min.time())
        return value
    if kind == "binary":
        return bytes(value)
    return value

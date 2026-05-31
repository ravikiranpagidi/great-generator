"""Public API surface."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from enterprise_synth.cdc.generator import generate_cdc as _generate_cdc
from enterprise_synth.config import resolve_row_counts
from enterprise_synth.domains import DOMAIN_MODULES
from enterprise_synth.exporters.csv_exporter import export_csv
from enterprise_synth.exporters.delta_exporter import export_delta
from enterprise_synth.exporters.json_exporter import export_json
from enterprise_synth.exporters.parquet_exporter import export_parquet
from enterprise_synth.schemas.generation import (
    generate_domain_schema_pandas,
    generate_single_table_pandas,
    generate_single_table_spark,
)
from enterprise_synth.schemas.models import DomainSchema, TableSchema
from enterprise_synth.utils.validation import validate_engine, validate_output_format


def list_domains() -> list[str]:
    """Return available domain-pack names."""

    return sorted(DOMAIN_MODULES)


def get_domain_schema(domain: str) -> DomainSchema:
    """Return schema metadata for a domain pack."""

    try:
        module = DOMAIN_MODULES[domain]
    except KeyError as exc:
        raise ValueError(f"Unknown domain '{domain}'. Available domains: {list_domains()}") from exc
    return module.schema()


def generate_domain(
    domain: str,
    engine: str = "pandas",
    scale: str = "tiny",
    rows: Mapping[str, int] | None = None,
    spark: Any | None = None,
    seed: int | None = None,
    anomalies: Mapping[str, float] | None = None,
    output_path: str | Path | None = None,
    output_format: str | None = None,
    partition_by: list[str] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> dict[str, Any]:
    """Generate a complete synthetic domain."""

    validate_engine(engine)
    validate_output_format(output_format)
    schema = get_domain_schema(domain)
    row_counts = resolve_row_counts(domain, scale, rows)
    module = DOMAIN_MODULES[domain]

    if engine == "pandas":
        from enterprise_synth.engines.pandas_engine import generate_domain as generate_with_pandas

        data = generate_with_pandas(module, schema, row_counts, seed=seed, anomalies=anomalies)
    else:
        from enterprise_synth.engines.spark_engine import generate_domain as generate_with_spark

        data = generate_with_spark(
            domain, schema, row_counts, spark=spark, seed=seed, anomalies=anomalies
        )

    if output_path is not None:
        if output_format is None:
            raise ValueError("output_format is required when output_path is provided.")
        export_data(
            data,
            output_path=output_path,
            output_format=output_format,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    return data


def export_data(
    data: Mapping[str, Any],
    output_path: str | Path,
    output_format: str,
    engine: str = "pandas",
    partition_by: list[str] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> None:
    """Export generated tables to table-per-folder outputs."""

    validate_engine(engine)
    validate_output_format(output_format)
    if output_format == "csv":
        export_csv(
            data,
            output_path,
            engine=engine,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "json":
        export_json(
            data,
            output_path,
            engine=engine,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "parquet":
        export_parquet(
            data,
            output_path,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "delta":
        export_delta(
            data,
            output_path,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    else:  # pragma: no cover - safeguarded by validate_output_format
        raise ValueError(f"Unsupported output format '{output_format}'.")


def generate_cdc(
    domain: str,
    table: str,
    rows: int,
    operations: list[str] | None = None,
    late_arrival_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate CDC-style records for supported domain/table pairs."""

    return _generate_cdc(
        domain=domain,
        table=table,
        rows=rows,
        operations=operations,
        late_arrival_rate=late_arrival_rate,
        duplicate_rate=duplicate_rate,
        seed=seed,
    )


def generate_from_schema(
    schema: DomainSchema | TableSchema | pd.DataFrame | str | Any,
    rows: Mapping[str, int] | int = 100,
    seed: int | None = None,
    engine: str = "pandas",
    spark: Any | None = None,
    table_name: str = "sample",
) -> dict[str, pd.DataFrame] | pd.DataFrame | Any:
    """Generate sample data from domain metadata, DataFrames, DDL strings, or Spark schemas.

    Supported inputs:
    - ``DomainSchema``: returns a dictionary of pandas tables, preserving relationships.
    - ``TableSchema``: returns a single pandas or Spark DataFrame.
    - empty pandas ``DataFrame`` with dtypes: returns a pandas or Spark DataFrame.
    - DDL-like string such as ``"id int, name string"``: returns a pandas or Spark DataFrame.
    - PySpark ``StructType``: returns pandas by default, or Spark when ``engine="spark"``.
    """

    validate_engine(engine)
    if isinstance(schema, DomainSchema):
        if engine != "pandas":
            raise ValueError("DomainSchema generation currently supports engine='pandas'.")
        return generate_domain_schema_pandas(schema, rows=rows, seed=seed)

    if isinstance(rows, Mapping):
        raise ValueError("Single-table schema generation expects rows to be an integer.")
    row_count = int(rows)
    if row_count < 0:
        raise ValueError("rows must be greater than or equal to zero.")

    if engine == "spark":
        return generate_single_table_spark(
            schema,
            rows=row_count,
            spark=spark,
            seed=seed,
            table_name=table_name,
        )
    return generate_single_table_pandas(
        schema,
        rows=row_count,
        seed=seed,
        table_name=table_name,
    )

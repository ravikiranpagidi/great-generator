"""Public API surface."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from enterprise_synth.cdc.generator import generate_cdc as _generate_cdc
from enterprise_synth.config import resolve_row_counts
from enterprise_synth.domains import DOMAIN_MODULES
from enterprise_synth.exporters.csv_exporter import export_csv
from enterprise_synth.exporters.delta_exporter import export_delta
from enterprise_synth.exporters.json_exporter import export_json
from enterprise_synth.exporters.parquet_exporter import export_parquet
from enterprise_synth.relationships.graph import topological_sort
from enterprise_synth.schemas.models import DomainSchema
from enterprise_synth.utils.random import get_rng
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
    schema: DomainSchema,
    rows: Mapping[str, int],
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate a simple pandas dataset from schema metadata.

    This utility is intentionally generic: it is useful for lightweight custom test
    fixtures, while richer business realism belongs in domain packs.
    """

    order = topological_sort(schema.dependencies())
    rng = get_rng(seed, "schema")
    generated: dict[str, pd.DataFrame] = {}

    for table_name in order:
        table = schema.tables[table_name]
        count = int(rows.get(table_name, 0))
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
            elif "int" in column.dtype.lower():
                frame[column.name] = rng.integers(0, 1000, size=count)
            elif "float" in column.dtype.lower():
                frame[column.name] = np.round(rng.normal(100, 15, size=count), 2)
            elif "date" in column.dtype.lower():
                frame[column.name] = pd.date_range("2025-01-01", periods=count, freq="D").date
            elif "bool" in column.dtype.lower():
                frame[column.name] = rng.random(count) < 0.5
            else:
                frame[column.name] = [f"{column.name}_{index}" for index in range(1, count + 1)]
        generated[table_name] = pd.DataFrame(frame)
    return generated

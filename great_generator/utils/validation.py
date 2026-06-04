"""Validation helpers for public APIs and generated datasets."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from great_generator.schemas.models import DomainSchema

VALID_ENGINES = {"pandas", "spark"}
VALID_OUTPUT_FORMATS = {"csv", "json", "parquet", "delta"}


def validate_engine(engine: str) -> None:
    if engine not in VALID_ENGINES:
        raise ValueError(f"Invalid engine '{engine}'. Expected one of {sorted(VALID_ENGINES)}.")


def validate_output_format(output_format: str | None) -> None:
    if output_format is not None and output_format not in VALID_OUTPUT_FORMATS:
        raise ValueError(
            f"Invalid output format '{output_format}'. Expected one of {sorted(VALID_OUTPUT_FORMATS)}."
        )


def validate_foreign_keys(data: Mapping[str, pd.DataFrame], schema: DomainSchema) -> dict[str, int]:
    """Return orphan counts per foreign key for pandas datasets."""

    violations: dict[str, int] = {}
    for table_name, table_schema in schema.tables.items():
        if table_name not in data:
            continue
        frame = data[table_name]
        for fk in table_schema.foreign_keys:
            if fk.column not in frame or fk.parent_table not in data:
                continue
            parent_values = set(data[fk.parent_table][fk.parent_column].dropna().tolist())
            orphan_count = int(
                (~frame[fk.column].isin(parent_values) & frame[fk.column].notna()).sum()
            )
            violations[f"{table_name}.{fk.column}"] = orphan_count
    return violations

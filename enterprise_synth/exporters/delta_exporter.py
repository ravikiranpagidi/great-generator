"""Delta Lake export support."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from enterprise_synth.exporters.pathing import spark_table_path
from enterprise_synth.exporters.spark_options import apply_writer_options, prepare_spark_frame


def export_delta(
    data: Mapping[str, Any],
    output_path: str | Path,
    engine: str,
    partition_by: Sequence[str] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> None:
    if engine != "spark":
        raise ValueError("Delta export requires engine='spark'.")
    for table_name, frame in data.items():
        frame = prepare_spark_frame(frame, num_partitions, partition_strategy)
        writer = apply_writer_options(frame.write.format("delta").mode(mode), writer_options)
        if partition_by:
            existing = [column for column in partition_by if column in frame.columns]
            if existing:
                writer = writer.partitionBy(*existing)
        writer.save(spark_table_path(output_path, table_name))

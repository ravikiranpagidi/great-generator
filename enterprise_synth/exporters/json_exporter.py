"""JSON export support."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from enterprise_synth.exporters.pathing import local_pandas_base_path, spark_table_path
from enterprise_synth.exporters.spark_options import apply_writer_options, prepare_spark_frame


def export_json(
    data: Mapping[str, Any],
    output_path: str | Path,
    engine: str,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> None:
    if engine == "pandas":
        base = local_pandas_base_path(output_path)
        base.mkdir(parents=True, exist_ok=True)
        for table_name, frame in data.items():
            table_path = base / table_name
            table_path.mkdir(parents=True, exist_ok=True)
            frame.to_json(
                table_path / f"{table_name}.json", orient="records", lines=True, date_format="iso"
            )
        return

    for table_name, frame in data.items():
        frame = prepare_spark_frame(frame, num_partitions, partition_strategy)
        writer = apply_writer_options(frame.write.mode(mode), writer_options)
        writer.json(spark_table_path(output_path, table_name))

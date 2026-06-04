"""Shared Spark export controls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def prepare_spark_frame(
    frame: Any,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> Any:
    """Return a Spark frame with optional output partition shaping applied."""

    if num_partitions is None:
        return frame
    if num_partitions <= 0:
        raise ValueError("num_partitions must be a positive integer.")
    if partition_strategy == "repartition":
        return frame.repartition(num_partitions)
    if partition_strategy == "coalesce":
        return frame.coalesce(num_partitions)
    raise ValueError("partition_strategy must be either 'repartition' or 'coalesce'.")


def apply_writer_options(writer: Any, writer_options: Mapping[str, str] | None = None) -> Any:
    """Apply arbitrary Spark writer options in a small, testable place."""

    if writer_options:
        return writer.options(**dict(writer_options))
    return writer

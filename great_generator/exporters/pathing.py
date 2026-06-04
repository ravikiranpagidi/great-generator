"""Engine-aware output path handling."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse


def _has_remote_scheme(path: str) -> bool:
    parsed = urlparse(path)
    # Windows drive letters such as C:\data parse as scheme="c".
    return bool(parsed.scheme) and len(parsed.scheme) > 1 and parsed.scheme != "file"


def local_pandas_base_path(output_path: str | Path) -> Path:
    """Return a local filesystem path for pandas exports.

    Pandas exports are intentionally local-first. Remote object-store paths belong
    to Spark, where the configured filesystem connector and cluster credentials
    already define access semantics.
    """

    raw = str(output_path)
    if _has_remote_scheme(raw):
        raise ValueError(
            "Pandas exports require a local filesystem path. "
            "Use engine='spark' for remote storage URIs such as s3a://, abfss://, gs://, or dbfs:/."
        )

    parsed = urlparse(raw)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    return Path(raw)


def spark_table_path(output_path: str | Path, table_name: str) -> str:
    """Return a child path without rewriting Spark-supported URI schemes."""

    raw = str(output_path)
    if _has_remote_scheme(raw) or raw.startswith(("/", "dbfs:/")):
        return f"{raw.rstrip('/')}/{table_name}"
    return str(Path(raw) / table_name)

"""Configuration for the optional Great Generator MCP server."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_ROWS = 100_000
DEFAULT_HARD_MAX_ROWS = 1_000_000
DEFAULT_PREVIEW_ROWS = 5
MAX_PREVIEW_ROWS = 25


@dataclass(frozen=True)
class MCPConfig:
    """Runtime safety configuration for MCP tool calls."""

    allowed_root: Path
    max_rows: int = DEFAULT_MAX_ROWS
    hard_max_rows: int = DEFAULT_HARD_MAX_ROWS
    default_preview_rows: int = DEFAULT_PREVIEW_ROWS
    max_preview_rows: int = MAX_PREVIEW_ROWS


def load_config(
    env: Mapping[str, str] | None = None,
    *,
    cwd: str | Path | None = None,
) -> MCPConfig:
    """Load MCP configuration from environment variables."""

    values = env or os.environ
    base_cwd = Path(cwd).expanduser() if cwd is not None else Path.cwd()
    allowed_root_raw = values.get("GREAT_GENERATOR_MCP_ALLOWED_ROOT")
    allowed_root = Path(allowed_root_raw).expanduser() if allowed_root_raw else base_cwd
    return MCPConfig(
        allowed_root=allowed_root.resolve(),
        max_rows=_positive_int(values.get("GREAT_GENERATOR_MCP_MAX_ROWS"), DEFAULT_MAX_ROWS),
        hard_max_rows=_positive_int(
            values.get("GREAT_GENERATOR_MCP_HARD_MAX_ROWS"),
            DEFAULT_HARD_MAX_ROWS,
        ),
    )


def _positive_int(raw: str | None, default: int) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"Expected a positive integer environment value, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"Expected a positive integer environment value, got {raw!r}.")
    return value

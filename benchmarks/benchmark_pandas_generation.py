"""Lightweight local pandas benchmark harness."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd

import great_generator
from great_generator import generate_domain

DEFAULT_CASES = [
    ("ecommerce", "tiny"),
    ("ecommerce", "small"),
    ("banking", "tiny"),
    ("banking", "small"),
    ("healthcare", "tiny"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark local pandas domain generation. Results are environment-specific "
            "and should not be used as universal performance claims."
        )
    )
    parser.add_argument(
        "--case",
        action="append",
        metavar="DOMAIN:SCALE",
        help="Benchmark one case such as ecommerce:small. Can be passed multiple times.",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per case.")
    parser.add_argument("--seed", type=int, default=42, help="Seed used for reproducible runs.")
    parser.add_argument("--json", type=str, help="Optional path to write JSON benchmark output.")
    return parser.parse_args()


def parse_cases(values: list[str] | None) -> list[tuple[str, str]]:
    if not values:
        return list(DEFAULT_CASES)
    cases = []
    for value in values:
        if ":" not in value:
            raise SystemExit(f"Invalid --case '{value}'. Use DOMAIN:SCALE.")
        domain, scale = value.split(":", 1)
        cases.append((domain.strip(), scale.strip()))
    return cases


def environment_metadata() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "great_generator": great_generator.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }


def run_case(domain: str, scale: str, *, seed: int) -> dict[str, Any]:
    start = perf_counter()
    data = generate_domain(domain, scale=scale, realism="realistic", seed=seed)
    elapsed = perf_counter() - start
    rows = sum(len(frame) for frame in data.values())
    rows_per_second = rows / elapsed if elapsed > 0 else None
    return {
        "domain": domain,
        "scale": scale,
        "rows": rows,
        "elapsed_seconds": elapsed,
        "rows_per_second": rows_per_second,
    }


def main() -> None:
    args = parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1.")

    results = {
        "metadata": environment_metadata(),
        "note": (
            "Benchmark results depend on machine, package versions, schema complexity, "
            "storage, and runtime configuration."
        ),
        "runs": [],
    }

    for domain, scale in parse_cases(args.case):
        for run_number in range(1, args.repeat + 1):
            record = run_case(domain, scale, seed=args.seed)
            record["run"] = run_number
            results["runs"].append(record)
            rows_per_second = record["rows_per_second"] or 0.0
            print(
                f"{domain:12s} {scale:6s} run={run_number:<2d} "
                f"{record['rows']:8d} rows {record['elapsed_seconds']:8.3f}s "
                f"{rows_per_second:10.1f} rows/s"
            )

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)


if __name__ == "__main__":
    main()

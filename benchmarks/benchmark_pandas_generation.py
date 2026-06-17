"""Lightweight local pandas benchmark harness."""

from __future__ import annotations

from time import perf_counter

from great_generator import generate_domain

CASES = [
    ("ecommerce", "tiny"),
    ("ecommerce", "small"),
    ("banking", "tiny"),
    ("banking", "small"),
    ("healthcare", "tiny"),
]


def main() -> None:
    for domain, scale in CASES:
        start = perf_counter()
        data = generate_domain(domain, scale=scale, realism="realistic", seed=42)
        elapsed = perf_counter() - start
        rows = sum(len(frame) for frame in data.values())
        print(f"{domain:12s} {scale:6s} {rows:8d} rows {elapsed:8.3f}s")


if __name__ == "__main__":
    main()

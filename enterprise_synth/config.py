"""Configuration primitives and scale profiles."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

ScaleProfile = dict[str, int]

SCALE_PROFILES: dict[str, dict[str, ScaleProfile]] = {
    "ecommerce": {
        "tiny": {
            "customers": 25,
            "products": 16,
            "orders": 60,
            "order_items": 150,
            "payments": 60,
            "shipments": 60,
            "returns": 6,
        },
        "small": {
            "customers": 500,
            "products": 200,
            "orders": 1_500,
            "order_items": 4_000,
            "payments": 1_500,
            "shipments": 1_500,
            "returns": 120,
        },
        "medium": {
            "customers": 10_000,
            "products": 2_000,
            "orders": 40_000,
            "order_items": 110_000,
            "payments": 40_000,
            "shipments": 40_000,
            "returns": 3_600,
        },
        "large": {
            "customers": 100_000,
            "products": 10_000,
            "orders": 500_000,
            "order_items": 1_400_000,
            "payments": 500_000,
            "shipments": 500_000,
            "returns": 45_000,
        },
    },
    "banking": {
        "tiny": {
            "customers": 25,
            "accounts": 40,
            "cards": 30,
            "merchants": 20,
            "transactions": 120,
            "fraud_events": 2,
            "cdc_customer_changes": 20,
        },
        "small": {
            "customers": 500,
            "accounts": 800,
            "cards": 650,
            "merchants": 180,
            "transactions": 5_000,
            "fraud_events": 45,
            "cdc_customer_changes": 400,
        },
        "medium": {
            "customers": 10_000,
            "accounts": 16_000,
            "cards": 13_000,
            "merchants": 1_200,
            "transactions": 150_000,
            "fraud_events": 1_300,
            "cdc_customer_changes": 8_000,
        },
        "large": {
            "customers": 100_000,
            "accounts": 165_000,
            "cards": 130_000,
            "merchants": 5_000,
            "transactions": 2_000_000,
            "fraud_events": 18_000,
            "cdc_customer_changes": 80_000,
        },
    },
}

VALID_SCALES = tuple(SCALE_PROFILES["ecommerce"].keys())


def resolve_row_counts(
    domain: str, scale: str, overrides: Mapping[str, int] | None = None
) -> ScaleProfile:
    """Return a copy of the configured row counts with optional user overrides."""

    if domain not in SCALE_PROFILES:
        raise ValueError(f"Unknown domain '{domain}'. Available domains: {sorted(SCALE_PROFILES)}")
    if scale not in SCALE_PROFILES[domain]:
        raise ValueError(
            f"Unknown scale '{scale}'. Available scales: {sorted(SCALE_PROFILES[domain])}"
        )

    counts = deepcopy(SCALE_PROFILES[domain][scale])
    if overrides:
        unknown = set(overrides) - set(counts)
        if unknown:
            raise ValueError(
                f"Unknown table override(s) for domain '{domain}': {sorted(unknown)}. "
                f"Known tables: {sorted(counts)}"
            )
        for table, value in overrides.items():
            if value < 0:
                raise ValueError(f"Row count for table '{table}' must be non-negative.")
            counts[table] = int(value)
    return counts

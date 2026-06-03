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
    "healthcare": {
        "tiny": {
            "patients": 30,
            "providers": 8,
            "facilities": 4,
            "encounters": 90,
            "claims": 75,
            "prescriptions": 60,
            "lab_results": 120,
        },
        "small": {
            "patients": 1_000,
            "providers": 80,
            "facilities": 20,
            "encounters": 5_000,
            "claims": 4_000,
            "prescriptions": 3_000,
            "lab_results": 7_000,
        },
        "medium": {
            "patients": 25_000,
            "providers": 800,
            "facilities": 100,
            "encounters": 150_000,
            "claims": 130_000,
            "prescriptions": 80_000,
            "lab_results": 220_000,
        },
        "large": {
            "patients": 200_000,
            "providers": 5_000,
            "facilities": 500,
            "encounters": 1_500_000,
            "claims": 1_300_000,
            "prescriptions": 900_000,
            "lab_results": 2_000_000,
        },
    },
    "telecom": {
        "tiny": {
            "customers": 30,
            "plans": 8,
            "devices": 35,
            "subscriptions": 45,
            "usage_events": 180,
            "invoices": 60,
            "support_tickets": 20,
        },
        "small": {
            "customers": 1_000,
            "plans": 24,
            "devices": 1_200,
            "subscriptions": 1_600,
            "usage_events": 50_000,
            "invoices": 8_000,
            "support_tickets": 1_200,
        },
        "medium": {
            "customers": 50_000,
            "plans": 60,
            "devices": 60_000,
            "subscriptions": 85_000,
            "usage_events": 2_500_000,
            "invoices": 420_000,
            "support_tickets": 60_000,
        },
        "large": {
            "customers": 250_000,
            "plans": 100,
            "devices": 300_000,
            "subscriptions": 450_000,
            "usage_events": 15_000_000,
            "invoices": 2_500_000,
            "support_tickets": 350_000,
        },
    },
    "logistics": {
        "tiny": {
            "shippers": 20,
            "warehouses": 6,
            "carriers": 6,
            "products": 30,
            "shipments": 80,
            "shipment_events": 240,
            "inventory_movements": 120,
        },
        "small": {
            "shippers": 500,
            "warehouses": 40,
            "carriers": 30,
            "products": 2_000,
            "shipments": 10_000,
            "shipment_events": 45_000,
            "inventory_movements": 25_000,
        },
        "medium": {
            "shippers": 10_000,
            "warehouses": 250,
            "carriers": 120,
            "products": 50_000,
            "shipments": 400_000,
            "shipment_events": 1_600_000,
            "inventory_movements": 900_000,
        },
        "large": {
            "shippers": 80_000,
            "warehouses": 1_000,
            "carriers": 300,
            "products": 250_000,
            "shipments": 3_000_000,
            "shipment_events": 12_000_000,
            "inventory_movements": 6_000_000,
        },
    },
    "saas": {
        "tiny": {
            "organizations": 20,
            "users": 80,
            "plans": 6,
            "subscriptions": 25,
            "features": 16,
            "usage_events": 240,
            "invoices": 50,
            "support_tickets": 25,
        },
        "small": {
            "organizations": 500,
            "users": 5_000,
            "plans": 12,
            "subscriptions": 700,
            "features": 60,
            "usage_events": 80_000,
            "invoices": 6_000,
            "support_tickets": 1_500,
        },
        "medium": {
            "organizations": 10_000,
            "users": 120_000,
            "plans": 20,
            "subscriptions": 14_000,
            "features": 120,
            "usage_events": 3_000_000,
            "invoices": 180_000,
            "support_tickets": 70_000,
        },
        "large": {
            "organizations": 80_000,
            "users": 1_000_000,
            "plans": 30,
            "subscriptions": 110_000,
            "features": 250,
            "usage_events": 25_000_000,
            "invoices": 1_500_000,
            "support_tickets": 600_000,
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

"""Energy, utilities, and resources domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from enterprise_synth.domains._industry import c, fk, generate_industry_pandas, table
from enterprise_synth.schemas.models import DomainSchema

CHOICES = {
    "customer_type": ["residential", "commercial", "industrial", "municipal"],
    "site_type": ["home", "office", "factory", "solar_farm", "mine", "water_treatment"],
    "meter_type": ["electric", "gas", "water", "solar", "wind"],
    "rate_plan_name": ["flat", "time_of_use", "industrial_peak", "net_metering"],
    "resource_type": ["electricity", "natural_gas", "water", "solar", "wind", "mining"],
    "outage_cause": ["weather", "equipment", "planned", "vegetation", "unknown"],
    "outage_status": ["open", "restored", "investigating", "scheduled"],
    "payment_status": ["paid", "open", "late", "disputed"],
}


def schema() -> DomainSchema:
    tables = {
        "customers": table(
            "customers",
            "customer_id",
            (
                c("customer_id", "int64"),
                c("customer_code", "string"),
                c("customer_type", "string"),
                c("region", "string"),
                c("customer_status", "string"),
                c("joined_date", "date"),
            ),
        ),
        "sites": table(
            "sites",
            "site_id",
            (
                c("site_id", "int64"),
                c("customer_id", "int64"),
                c("site_code", "string"),
                c("site_type", "string"),
                c("region", "string"),
                c("active", "bool"),
            ),
            (fk("customer_id", "customers", "customer_id"),),
            "Customer service locations and resource sites.",
        ),
        "meters": table(
            "meters",
            "meter_id",
            (
                c("meter_id", "int64"),
                c("site_id", "int64"),
                c("meter_code", "string"),
                c("meter_type", "string"),
                c("installed_date", "date"),
                c("smart_meter", "bool"),
            ),
            (fk("site_id", "sites", "site_id"),),
            "Utility meters and smart devices.",
        ),
        "rate_plans": table(
            "rate_plans",
            "rate_plan_id",
            (
                c("rate_plan_id", "int64"),
                c("rate_plan_name", "string"),
                c("resource_type", "string"),
                c("base_fee", "float64"),
                c("unit_rate", "float64"),
            ),
        ),
        "usage_readings": table(
            "usage_readings",
            "reading_id",
            (
                c("reading_id", "int64"),
                c("meter_id", "int64"),
                c("site_id", "int64"),
                c("reading_ts", "datetime64[ns]"),
                c("event_date", "date"),
                c("usage_quantity", "float64"),
                c("estimated_reading", "bool"),
            ),
            (fk("meter_id", "meters", "meter_id"), fk("site_id", "sites", "site_id")),
            "Meter interval readings for utility analytics.",
        ),
        "outages": table(
            "outages",
            "outage_id",
            (
                c("outage_id", "int64"),
                c("site_id", "int64"),
                c("meter_id", "int64"),
                c("outage_start_ts", "datetime64[ns]"),
                c("outage_end_ts", "datetime64[ns]", nullable=True),
                c("outage_cause", "string"),
                c("outage_status", "string"),
                c("customers_impacted", "int64"),
            ),
            (fk("site_id", "sites", "site_id"), fk("meter_id", "meters", "meter_id")),
            "Service interruptions and restoration events.",
        ),
        "bills": table(
            "bills",
            "bill_id",
            (
                c("bill_id", "int64"),
                c("customer_id", "int64"),
                c("site_id", "int64"),
                c("rate_plan_id", "int64"),
                c("bill_month", "date"),
                c("usage_quantity", "float64"),
                c("bill_amount", "float64"),
                c("payment_status", "string"),
            ),
            (
                fk("customer_id", "customers", "customer_id"),
                fk("site_id", "sites", "site_id"),
                fk("rate_plan_id", "rate_plans", "rate_plan_id"),
            ),
            "Bills generated from usage and tariffs.",
        ),
    }
    return DomainSchema(
        name="energy",
        tables=tables,
        description="Energy, utilities, and resources domain for customers, meters, usage, outages, and bills.",
        behaviors=(
            "Smart meter interval data",
            "Rate plans influence billing",
            "Outages model reliability and restoration",
            "Supports electricity, gas, water, renewable, and resource demos",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)

"""Telecom domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from great_generator.distributions.time_patterns import (
    random_timestamps_on_dates,
    sampled_month_starts,
    weighted_calendar_dates,
)
from great_generator.distributions.weighted import normalize
from great_generator.relationships.keys import KeyRegistry
from great_generator.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema
from great_generator.utils.random import get_rng


def _c(name: str, dtype: str, nullable: bool = False, description: str = "") -> ColumnSpec:
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable, description=description)


def schema() -> DomainSchema:
    tables = {
        "customers": TableSchema(
            name="customers",
            primary_key="customer_id",
            description="Subscriber households and business customers with churn signals.",
            columns=(
                _c("customer_id", "int64"),
                _c("customer_code", "string"),
                _c("first_name", "string"),
                _c("last_name", "string"),
                _c("customer_name", "string"),
                _c("email", "string"),
                _c("phone_number", "string", nullable=True),
                _c("customer_segment", "string"),
                _c("region", "string"),
                _c("signup_date", "date"),
                _c("customer_status", "string"),
                _c("churn_risk", "string"),
            ),
        ),
        "plans": TableSchema(
            name="plans",
            primary_key="plan_id",
            description="Mobile and broadband plans with allowance and pricing.",
            columns=(
                _c("plan_id", "int64"),
                _c("plan_name", "string"),
                _c("plan_type", "string"),
                _c("monthly_fee", "float64"),
                _c("data_gb", "float64"),
                _c("unlimited_data", "bool"),
            ),
        ),
        "devices": TableSchema(
            name="devices",
            primary_key="device_id",
            description="Customer devices and network capabilities.",
            columns=(
                _c("device_id", "int64"),
                _c("manufacturer", "string"),
                _c("model", "string"),
                _c("device_type", "string"),
                _c("supports_5g", "bool"),
            ),
        ),
        "subscriptions": TableSchema(
            name="subscriptions",
            primary_key="subscription_id",
            foreign_keys=(
                ForeignKey("customer_id", "customers", "customer_id"),
                ForeignKey("plan_id", "plans", "plan_id"),
                ForeignKey("device_id", "devices", "device_id"),
            ),
            description="Active and inactive services connecting customers, plans, and devices.",
            columns=(
                _c("subscription_id", "int64"),
                _c("customer_id", "int64"),
                _c("plan_id", "int64"),
                _c("device_id", "int64"),
                _c("start_date", "date"),
                _c("subscription_status", "string"),
                _c("churn_score", "float64"),
            ),
        ),
        "usage_events": TableSchema(
            name="usage_events",
            primary_key="usage_event_id",
            foreign_keys=(ForeignKey("subscription_id", "subscriptions", "subscription_id"),),
            description="Network usage records for data, voice, SMS, and roaming.",
            columns=(
                _c("usage_event_id", "int64"),
                _c("subscription_id", "int64"),
                _c("event_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("usage_type", "string"),
                _c("data_mb", "float64"),
                _c("call_minutes", "float64"),
                _c("sms_count", "int64"),
                _c("roaming", "bool"),
            ),
        ),
        "invoices": TableSchema(
            name="invoices",
            primary_key="invoice_id",
            foreign_keys=(ForeignKey("subscription_id", "subscriptions", "subscription_id"),),
            description="Recurring bills and payment state.",
            columns=(
                _c("invoice_id", "int64"),
                _c("subscription_id", "int64"),
                _c("invoice_month", "date"),
                _c("invoice_amount", "float64"),
                _c("paid_amount", "float64"),
                _c("payment_status", "string"),
                _c("late_fee", "float64"),
            ),
        ),
        "support_tickets": TableSchema(
            name="support_tickets",
            primary_key="ticket_id",
            foreign_keys=(
                ForeignKey("subscription_id", "subscriptions", "subscription_id"),
                ForeignKey("customer_id", "customers", "customer_id"),
            ),
            description="Customer support interactions linked to service quality and churn.",
            columns=(
                _c("ticket_id", "int64"),
                _c("subscription_id", "int64"),
                _c("customer_id", "int64"),
                _c("created_ts", "datetime64[ns]"),
                _c("category", "string"),
                _c("priority", "string"),
                _c("ticket_status", "string"),
                _c("resolution_hours", "float64"),
            ),
        ),
    }
    return DomainSchema(
        name="telecom",
        tables=tables,
        description="A telecom domain with customers, subscriptions, usage, billing, and support.",
        behaviors=(
            "Premium and unlimited plans generate more data usage",
            "Roaming and overage behavior influence invoices",
            "High churn-risk customers create more support tickets",
            "Payment issues and network tickets are correlated with churn signals",
        ),
    )


def _base_or_sample(keys: np.ndarray, rows: int, rng: np.random.Generator) -> np.ndarray:
    if rows <= len(keys):
        return rng.choice(keys, size=rows, replace=False)
    extras = rng.choice(keys, size=rows - len(keys), replace=True)
    values = np.concatenate([keys, extras])
    rng.shuffle(values)
    return values


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    registry = KeyRegistry()

    customer_rng = get_rng(seed, "telecom.customers")
    customer_count = row_counts["customers"]
    customer_ids = np.arange(1, customer_count + 1, dtype=np.int64)
    segments = customer_rng.choice(
        ["consumer", "family", "small_business", "enterprise"],
        customer_count,
        p=[0.48, 0.30, 0.16, 0.06],
    )
    churn_risk = customer_rng.choice(
        ["low", "medium", "high"], customer_count, p=[0.68, 0.24, 0.08]
    )
    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_code": [f"TEL{value:08d}" for value in customer_ids],
            "customer_segment": segments,
            "region": customer_rng.choice(
                ["northeast", "south", "midwest", "west"], customer_count
            ),
            "signup_date": weighted_calendar_dates(
                customer_rng,
                customer_count,
                start="2021-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
            "customer_status": np.where(
                churn_risk == "high",
                customer_rng.choice(
                    ["active", "past_due", "cancelled"], customer_count, p=[0.78, 0.16, 0.06]
                ),
                customer_rng.choice(
                    ["active", "past_due", "cancelled"], customer_count, p=[0.93, 0.05, 0.02]
                ),
            ),
            "churn_risk": churn_risk,
        }
    )
    registry.register("customers", customer_ids)

    plan_rng = get_rng(seed, "telecom.plans")
    plan_count = row_counts["plans"]
    plan_ids = np.arange(1, plan_count + 1, dtype=np.int64)
    plan_types = plan_rng.choice(
        ["mobile", "broadband", "family", "business"], plan_count, p=[0.42, 0.22, 0.24, 0.12]
    )
    unlimited = plan_rng.random(plan_count) < np.where(plan_types == "business", 0.72, 0.38)
    data_gb = np.where(unlimited, 999.0, plan_rng.choice([5, 10, 25, 50, 100], plan_count))
    monthly_fee = np.round(
        np.where(plan_types == "business", 85, 38)
        + data_gb.clip(0, 100) * 0.42
        + plan_rng.normal(0, 4, plan_count),
        2,
    )
    plans = pd.DataFrame(
        {
            "plan_id": plan_ids,
            "plan_name": [f"Plan {value:03d}" for value in plan_ids],
            "plan_type": plan_types,
            "monthly_fee": monthly_fee,
            "data_gb": data_gb,
            "unlimited_data": unlimited,
        }
    )
    registry.register("plans", plan_ids)

    device_rng = get_rng(seed, "telecom.devices")
    device_count = row_counts["devices"]
    device_ids = np.arange(1, device_count + 1, dtype=np.int64)
    manufacturers = device_rng.choice(
        ["Apple", "Samsung", "Google", "Motorola", "OnePlus"],
        device_count,
        p=[0.36, 0.32, 0.12, 0.12, 0.08],
    )
    devices = pd.DataFrame(
        {
            "device_id": device_ids,
            "manufacturer": manufacturers,
            "model": [f"Model {value:05d}" for value in device_ids],
            "device_type": device_rng.choice(
                ["phone", "tablet", "router", "iot"], device_count, p=[0.72, 0.10, 0.13, 0.05]
            ),
            "supports_5g": device_rng.random(device_count) < 0.68,
        }
    )
    registry.register("devices", device_ids)

    sub_rng = get_rng(seed, "telecom.subscriptions")
    sub_count = row_counts["subscriptions"]
    sub_ids = np.arange(1, sub_count + 1, dtype=np.int64)
    customer_weights = (
        pd.Series(segments)
        .map({"consumer": 1.0, "family": 1.8, "small_business": 2.4, "enterprise": 4.0})
        .to_numpy()
    )
    subscription_customer_ids = _base_or_sample(customer_ids, sub_count, sub_rng)
    if sub_count > customer_count:
        subscription_customer_ids[customer_count:] = sub_rng.choice(
            customer_ids,
            sub_count - customer_count,
            replace=True,
            p=normalize(customer_weights),
        )
    subscription_plan_ids = registry.sample("plans", sub_count, sub_rng)
    subscription_device_ids = registry.sample("devices", sub_count, sub_rng)
    customer_churn = (
        customers.set_index("customer_id").loc[subscription_customer_ids, "churn_risk"].to_numpy()
    )
    churn_score = np.round(
        sub_rng.beta(1.6, 7.5, sub_count)
        + np.where(customer_churn == "high", 0.45, np.where(customer_churn == "medium", 0.18, 0.0)),
        3,
    ).clip(0, 1)
    subscriptions = pd.DataFrame(
        {
            "subscription_id": sub_ids,
            "customer_id": subscription_customer_ids,
            "plan_id": subscription_plan_ids,
            "device_id": subscription_device_ids,
            "start_date": weighted_calendar_dates(
                sub_rng,
                sub_count,
                start="2021-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
            "subscription_status": sub_rng.choice(
                ["active", "suspended", "cancelled"], sub_count, p=[0.90, 0.06, 0.04]
            ),
            "churn_score": churn_score,
        }
    )
    registry.register("subscriptions", sub_ids)

    usage_rng = get_rng(seed, "telecom.usage")
    usage_count = row_counts["usage_events"]
    usage_ids = np.arange(1, usage_count + 1, dtype=np.int64)
    sub_plan = subscriptions.set_index("subscription_id").join(
        plans.set_index("plan_id"), on="plan_id"
    )
    sub_weights = (
        sub_plan["plan_type"]
        .map({"mobile": 1.2, "broadband": 1.7, "family": 2.0, "business": 2.4})
        .to_numpy()
    )
    usage_subscription_ids = registry.sample(
        "subscriptions", usage_count, usage_rng, normalize(sub_weights)
    )
    usage_plan = sub_plan.loc[usage_subscription_ids]
    usage_types = usage_rng.choice(["data", "voice", "sms"], usage_count, p=[0.76, 0.16, 0.08])
    usage_dates = weighted_calendar_dates(usage_rng, usage_count, weekend_multiplier=1.18)
    usage_ts = random_timestamps_on_dates(usage_rng, usage_dates, business_hours_bias=0.38)
    data_multiplier = np.where(usage_plan["unlimited_data"].to_numpy(), 2.4, 1.0)
    usage_events = pd.DataFrame(
        {
            "usage_event_id": usage_ids,
            "subscription_id": usage_subscription_ids,
            "event_ts": usage_ts,
            "event_date": usage_ts.dt.date,
            "usage_type": usage_types,
            "data_mb": np.where(
                usage_types == "data",
                np.round(usage_rng.lognormal(8.2, 0.95, usage_count) * data_multiplier, 2),
                0.0,
            ),
            "call_minutes": np.where(
                usage_types == "voice", np.round(usage_rng.gamma(2.2, 4.0, usage_count), 2), 0.0
            ),
            "sms_count": np.where(usage_types == "sms", usage_rng.integers(1, 8, usage_count), 0),
            "roaming": usage_rng.random(usage_count) < 0.035,
        }
    )

    invoice_rng = get_rng(seed, "telecom.invoices")
    invoice_count = row_counts["invoices"]
    invoice_ids = np.arange(1, invoice_count + 1, dtype=np.int64)
    invoice_subscription_ids = _base_or_sample(sub_ids, invoice_count, invoice_rng)
    invoice_plan = sub_plan.loc[invoice_subscription_ids]
    payment_status = invoice_rng.choice(
        ["paid", "open", "late", "written_off"], invoice_count, p=[0.82, 0.10, 0.06, 0.02]
    )
    invoice_amount = np.round(
        invoice_plan["monthly_fee"].to_numpy() + invoice_rng.gamma(2.0, 4.5, invoice_count), 2
    )
    invoices = pd.DataFrame(
        {
            "invoice_id": invoice_ids,
            "subscription_id": invoice_subscription_ids,
            "invoice_month": sampled_month_starts(
                invoice_rng, invoice_count, start="2024-01-01", periods=24
            ),
            "invoice_amount": invoice_amount,
            "paid_amount": np.where(payment_status == "paid", invoice_amount, 0.0),
            "payment_status": payment_status,
            "late_fee": np.where(payment_status == "late", 12.5, 0.0),
        }
    )

    ticket_rng = get_rng(seed, "telecom.tickets")
    ticket_count = row_counts["support_tickets"]
    ticket_ids = np.arange(1, ticket_count + 1, dtype=np.int64)
    ticket_weights = subscriptions["churn_score"].to_numpy() + 0.05
    ticket_subscription_ids = registry.sample(
        "subscriptions", ticket_count, ticket_rng, normalize(ticket_weights)
    )
    ticket_base = subscriptions.set_index("subscription_id").loc[ticket_subscription_ids]
    ticket_dates = weighted_calendar_dates(ticket_rng, ticket_count)
    created_ts = random_timestamps_on_dates(ticket_rng, ticket_dates, business_hours_bias=0.70)
    priorities = ticket_rng.choice(["low", "medium", "high"], ticket_count, p=[0.55, 0.34, 0.11])
    support_tickets = pd.DataFrame(
        {
            "ticket_id": ticket_ids,
            "subscription_id": ticket_subscription_ids,
            "customer_id": ticket_base["customer_id"].to_numpy(),
            "created_ts": created_ts,
            "category": ticket_rng.choice(
                ["billing", "network", "device", "plan_change", "cancellation"],
                ticket_count,
                p=[0.28, 0.34, 0.18, 0.12, 0.08],
            ),
            "priority": priorities,
            "ticket_status": ticket_rng.choice(
                ["resolved", "open", "escalated"], ticket_count, p=[0.78, 0.16, 0.06]
            ),
            "resolution_hours": np.round(
                ticket_rng.lognormal(np.where(priorities == "high", 2.0, 1.2), 0.65, ticket_count),
                2,
            ),
        }
    )

    return {
        "customers": customers,
        "plans": plans,
        "devices": devices,
        "subscriptions": subscriptions,
        "usage_events": usage_events,
        "invoices": invoices,
        "support_tickets": support_tickets,
    }

"""SaaS domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from great_generator.distributions.time_patterns import (
    random_timestamps_on_dates,
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
        "organizations": TableSchema(
            name="organizations",
            primary_key="organization_id",
            description="Customer accounts using the SaaS platform.",
            columns=(
                _c("organization_id", "int64"),
                _c("organization_name", "string"),
                _c("industry", "string"),
                _c("company_size", "string"),
                _c("region", "string"),
                _c("health_score", "float64"),
            ),
        ),
        "users": TableSchema(
            name="users",
            primary_key="user_id",
            foreign_keys=(ForeignKey("organization_id", "organizations", "organization_id"),),
            description="Platform users nested under organizations.",
            columns=(
                _c("user_id", "int64"),
                _c("organization_id", "int64"),
                _c("role", "string"),
                _c("user_status", "string"),
                _c("created_date", "date"),
                _c("last_login_ts", "datetime64[ns]"),
            ),
        ),
        "plans": TableSchema(
            name="plans",
            primary_key="plan_id",
            description="Subscription plans and price points.",
            columns=(
                _c("plan_id", "int64"),
                _c("plan_name", "string"),
                _c("billing_period", "string"),
                _c("base_price", "float64"),
                _c("included_seats", "int64"),
            ),
        ),
        "subscriptions": TableSchema(
            name="subscriptions",
            primary_key="subscription_id",
            foreign_keys=(
                ForeignKey("organization_id", "organizations", "organization_id"),
                ForeignKey("plan_id", "plans", "plan_id"),
            ),
            description="Commercial subscription state for each organization.",
            columns=(
                _c("subscription_id", "int64"),
                _c("organization_id", "int64"),
                _c("plan_id", "int64"),
                _c("start_date", "date"),
                _c("subscription_status", "string"),
                _c("mrr", "float64"),
                _c("seat_count", "int64"),
            ),
        ),
        "features": TableSchema(
            name="features",
            primary_key="feature_id",
            description="Product capabilities used in usage telemetry.",
            columns=(
                _c("feature_id", "int64"),
                _c("feature_name", "string"),
                _c("feature_area", "string"),
                _c("premium_feature", "bool"),
            ),
        ),
        "usage_events": TableSchema(
            name="usage_events",
            primary_key="usage_event_id",
            foreign_keys=(
                ForeignKey("organization_id", "organizations", "organization_id"),
                ForeignKey("user_id", "users", "user_id"),
                ForeignKey("feature_id", "features", "feature_id"),
            ),
            description="Product telemetry events by user and feature.",
            columns=(
                _c("usage_event_id", "int64"),
                _c("organization_id", "int64"),
                _c("user_id", "int64"),
                _c("feature_id", "int64"),
                _c("event_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("event_type", "string"),
                _c("session_minutes", "float64"),
            ),
        ),
        "invoices": TableSchema(
            name="invoices",
            primary_key="invoice_id",
            foreign_keys=(
                ForeignKey("subscription_id", "subscriptions", "subscription_id"),
                ForeignKey("organization_id", "organizations", "organization_id"),
            ),
            description="Billing documents for SaaS subscriptions.",
            columns=(
                _c("invoice_id", "int64"),
                _c("subscription_id", "int64"),
                _c("organization_id", "int64"),
                _c("invoice_date", "date"),
                _c("invoice_amount", "float64"),
                _c("payment_status", "string"),
            ),
        ),
        "support_tickets": TableSchema(
            name="support_tickets",
            primary_key="ticket_id",
            foreign_keys=(
                ForeignKey("organization_id", "organizations", "organization_id"),
                ForeignKey("user_id", "users", "user_id"),
            ),
            description="Support workload and customer health signals.",
            columns=(
                _c("ticket_id", "int64"),
                _c("organization_id", "int64"),
                _c("user_id", "int64"),
                _c("created_ts", "datetime64[ns]"),
                _c("ticket_category", "string"),
                _c("priority", "string"),
                _c("ticket_status", "string"),
                _c("first_response_hours", "float64"),
            ),
        ),
    }
    return DomainSchema(
        name="saas",
        tables=tables,
        description="A SaaS domain with organizations, users, subscriptions, product usage, billing, and support.",
        behaviors=(
            "Enterprise organizations have more seats and usage",
            "Low health-score accounts create more support tickets",
            "Premium features are used more often by higher-tier subscriptions",
            "Billing status and usage volume can be used for churn and revenue demos",
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

    org_rng = get_rng(seed, "saas.organizations")
    org_count = row_counts["organizations"]
    org_ids = np.arange(1, org_count + 1, dtype=np.int64)
    company_sizes = org_rng.choice(
        ["smb", "mid_market", "enterprise"], org_count, p=[0.58, 0.30, 0.12]
    )
    health_score = np.round(
        org_rng.beta(6.0, 2.4, org_count) - np.where(company_sizes == "smb", 0.06, 0.0), 3
    ).clip(0.05, 0.99)
    organizations = pd.DataFrame(
        {
            "organization_id": org_ids,
            "organization_name": [f"Organization {value:05d}" for value in org_ids],
            "industry": org_rng.choice(
                ["software", "finance", "healthcare", "retail", "education"],
                org_count,
                p=[0.30, 0.20, 0.18, 0.20, 0.12],
            ),
            "company_size": company_sizes,
            "region": org_rng.choice(
                ["NA", "EMEA", "APAC", "LATAM"], org_count, p=[0.52, 0.24, 0.18, 0.06]
            ),
            "health_score": health_score,
        }
    )
    registry.register("organizations", org_ids)

    user_rng = get_rng(seed, "saas.users")
    user_count = row_counts["users"]
    user_ids = np.arange(1, user_count + 1, dtype=np.int64)
    org_weights = (
        pd.Series(company_sizes).map({"smb": 0.8, "mid_market": 2.0, "enterprise": 5.0}).to_numpy()
    )
    user_org_ids = _base_or_sample(org_ids, user_count, user_rng)
    if user_count > org_count:
        user_org_ids[org_count:] = user_rng.choice(
            org_ids, user_count - org_count, replace=True, p=normalize(org_weights)
        )
    created_dates = weighted_calendar_dates(
        user_rng,
        user_count,
        start="2021-01-01",
        end="2025-12-31",
        weekend_multiplier=1.0,
        holiday_multiplier=1.0,
    )
    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "organization_id": user_org_ids,
            "role": user_rng.choice(
                ["admin", "analyst", "developer", "viewer"], user_count, p=[0.12, 0.34, 0.28, 0.26]
            ),
            "user_status": user_rng.choice(
                ["active", "invited", "disabled"], user_count, p=[0.86, 0.08, 0.06]
            ),
            "created_date": created_dates.date,
            "last_login_ts": random_timestamps_on_dates(
                user_rng, weighted_calendar_dates(user_rng, user_count), business_hours_bias=0.68
            ),
        }
    )
    registry.register("users", user_ids)

    plan_rng = get_rng(seed, "saas.plans")
    plan_count = row_counts["plans"]
    plan_ids = np.arange(1, plan_count + 1, dtype=np.int64)
    plan_names = plan_rng.choice(
        ["starter", "growth", "business", "enterprise"], plan_count, p=[0.28, 0.34, 0.26, 0.12]
    )
    base_prices = (
        pd.Series(plan_names)
        .map({"starter": 49, "growth": 199, "business": 799, "enterprise": 2500})
        .to_numpy(dtype=float)
    )
    plans = pd.DataFrame(
        {
            "plan_id": plan_ids,
            "plan_name": plan_names,
            "billing_period": plan_rng.choice(["monthly", "annual"], plan_count, p=[0.64, 0.36]),
            "base_price": np.round(base_prices * plan_rng.uniform(0.9, 1.15, plan_count), 2),
            "included_seats": pd.Series(plan_names)
            .map({"starter": 5, "growth": 25, "business": 100, "enterprise": 500})
            .to_numpy(),
        }
    )
    registry.register("plans", plan_ids)

    sub_rng = get_rng(seed, "saas.subscriptions")
    sub_count = row_counts["subscriptions"]
    sub_ids = np.arange(1, sub_count + 1, dtype=np.int64)
    sub_org_ids = _base_or_sample(org_ids, sub_count, sub_rng)
    sub_org_sizes = (
        organizations.set_index("organization_id").loc[sub_org_ids, "company_size"].to_numpy()
    )
    plan_weights = (
        plans["plan_name"]
        .map({"starter": 1.0, "growth": 1.2, "business": 0.9, "enterprise": 0.45})
        .to_numpy(dtype=float)
    )
    sub_plan_ids = registry.sample("plans", sub_count, sub_rng, normalize(plan_weights))
    sub_plan = plans.set_index("plan_id").loc[sub_plan_ids]
    seat_count = np.where(
        sub_org_sizes == "enterprise",
        sub_rng.integers(120, 1400, sub_count),
        np.where(
            sub_org_sizes == "mid_market",
            sub_rng.integers(25, 220, sub_count),
            sub_rng.integers(3, 60, sub_count),
        ),
    )
    subscriptions = pd.DataFrame(
        {
            "subscription_id": sub_ids,
            "organization_id": sub_org_ids,
            "plan_id": sub_plan_ids,
            "start_date": weighted_calendar_dates(
                sub_rng,
                sub_count,
                start="2021-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
            "subscription_status": sub_rng.choice(
                ["active", "trial", "past_due", "cancelled"], sub_count, p=[0.82, 0.08, 0.06, 0.04]
            ),
            "mrr": np.round(
                sub_plan["base_price"].to_numpy() + seat_count * sub_rng.uniform(4, 14, sub_count),
                2,
            ),
            "seat_count": seat_count,
        }
    )
    registry.register("subscriptions", sub_ids)

    feature_rng = get_rng(seed, "saas.features")
    feature_count = row_counts["features"]
    feature_ids = np.arange(1, feature_count + 1, dtype=np.int64)
    feature_areas = feature_rng.choice(
        ["analytics", "automation", "security", "collaboration", "admin"],
        feature_count,
        p=[0.28, 0.22, 0.18, 0.22, 0.10],
    )
    features = pd.DataFrame(
        {
            "feature_id": feature_ids,
            "feature_name": [f"Feature {value:03d}" for value in feature_ids],
            "feature_area": feature_areas,
            "premium_feature": feature_rng.random(feature_count)
            < np.where(feature_areas == "security", 0.72, 0.38),
        }
    )
    registry.register("features", feature_ids)

    event_rng = get_rng(seed, "saas.usage_events")
    event_count = row_counts["usage_events"]
    event_ids = np.arange(1, event_count + 1, dtype=np.int64)
    org_usage_weights = (
        pd.Series(company_sizes).map({"smb": 0.8, "mid_market": 2.0, "enterprise": 5.0}).to_numpy()
    )
    event_org_ids = registry.sample(
        "organizations", event_count, event_rng, normalize(org_usage_weights)
    )
    user_by_org = users.groupby("organization_id")["user_id"].apply(np.array).to_dict()
    event_user_ids = np.empty(event_count, dtype=np.int64)
    for idx, org_id in enumerate(event_org_ids):
        choices = user_by_org.get(int(org_id), user_ids)
        event_user_ids[idx] = event_rng.choice(choices)
    event_dates = weighted_calendar_dates(event_rng, event_count, weekend_multiplier=0.58)
    event_ts = random_timestamps_on_dates(event_rng, event_dates, business_hours_bias=0.76)
    usage_events = pd.DataFrame(
        {
            "usage_event_id": event_ids,
            "organization_id": event_org_ids,
            "user_id": event_user_ids,
            "feature_id": registry.sample("features", event_count, event_rng),
            "event_ts": event_ts,
            "event_date": event_ts.dt.date,
            "event_type": event_rng.choice(
                ["view", "create", "update", "export", "login"],
                event_count,
                p=[0.34, 0.20, 0.22, 0.10, 0.14],
            ),
            "session_minutes": np.round(event_rng.lognormal(1.9, 0.8, event_count), 2),
        }
    )

    invoice_rng = get_rng(seed, "saas.invoices")
    invoice_count = row_counts["invoices"]
    invoice_ids = np.arange(1, invoice_count + 1, dtype=np.int64)
    invoice_sub_ids = _base_or_sample(sub_ids, invoice_count, invoice_rng)
    invoice_base = subscriptions.set_index("subscription_id").loc[invoice_sub_ids]
    invoice_amount = np.round(
        invoice_base["mrr"].to_numpy() * invoice_rng.uniform(0.95, 1.08, invoice_count), 2
    )
    invoice_month_offsets = invoice_rng.integers(0, 12, invoice_count)
    invoices = pd.DataFrame(
        {
            "invoice_id": invoice_ids,
            "subscription_id": invoice_sub_ids,
            "organization_id": invoice_base["organization_id"].to_numpy(),
            "invoice_date": (
                pd.Timestamp("2025-01-01") + pd.to_timedelta(invoice_month_offsets * 30, unit="D")
            ).date,
            "invoice_amount": invoice_amount,
            "payment_status": invoice_rng.choice(
                ["paid", "open", "past_due", "void"], invoice_count, p=[0.84, 0.10, 0.04, 0.02]
            ),
        }
    )

    ticket_rng = get_rng(seed, "saas.support_tickets")
    ticket_count = row_counts["support_tickets"]
    ticket_ids = np.arange(1, ticket_count + 1, dtype=np.int64)
    ticket_weights = (1.0 - organizations["health_score"].to_numpy()) + 0.05
    ticket_org_ids = registry.sample(
        "organizations", ticket_count, ticket_rng, normalize(ticket_weights)
    )
    ticket_user_ids = np.empty(ticket_count, dtype=np.int64)
    for idx, org_id in enumerate(ticket_org_ids):
        choices = user_by_org.get(int(org_id), user_ids)
        ticket_user_ids[idx] = ticket_rng.choice(choices)
    ticket_priorities = ticket_rng.choice(
        ["low", "medium", "high", "urgent"], ticket_count, p=[0.46, 0.36, 0.14, 0.04]
    )
    ticket_dates = weighted_calendar_dates(ticket_rng, ticket_count)
    support_tickets = pd.DataFrame(
        {
            "ticket_id": ticket_ids,
            "organization_id": ticket_org_ids,
            "user_id": ticket_user_ids,
            "created_ts": random_timestamps_on_dates(
                ticket_rng, ticket_dates, business_hours_bias=0.72
            ),
            "ticket_category": ticket_rng.choice(
                ["how_to", "bug", "billing", "integration", "performance"],
                ticket_count,
                p=[0.30, 0.26, 0.16, 0.18, 0.10],
            ),
            "priority": ticket_priorities,
            "ticket_status": ticket_rng.choice(
                ["resolved", "open", "escalated"], ticket_count, p=[0.76, 0.18, 0.06]
            ),
            "first_response_hours": np.round(
                ticket_rng.lognormal(
                    np.where(ticket_priorities == "urgent", 0.6, 1.5), 0.7, ticket_count
                ),
                2,
            ),
        }
    )

    return {
        "organizations": organizations,
        "users": users,
        "plans": plans,
        "subscriptions": subscriptions,
        "features": features,
        "usage_events": usage_events,
        "invoices": invoices,
        "support_tickets": support_tickets,
    }

import pandas as pd
import pytest

from great_generator import generate_domain


@pytest.mark.parametrize(
    ("domain", "expected_tables"),
    [
        (
            "insurance",
            {
                "customers",
                "agents",
                "policies",
                "claims",
                "premium_payments",
                "risk_assessments",
                "reinsurance_contracts",
            },
        ),
        (
            "automotive",
            {
                "customers",
                "dealers",
                "vehicles",
                "sales",
                "service_appointments",
                "warranty_claims",
                "telematics_events",
            },
        ),
        (
            "energy",
            {
                "customers",
                "sites",
                "meters",
                "rate_plans",
                "usage_readings",
                "outages",
                "bills",
            },
        ),
        (
            "healthcare",
            {
                "patients",
                "providers",
                "facilities",
                "encounters",
                "claims",
                "prescriptions",
                "lab_results",
            },
        ),
        (
            "telecom",
            {
                "customers",
                "plans",
                "devices",
                "subscriptions",
                "usage_events",
                "invoices",
                "support_tickets",
            },
        ),
        (
            "logistics",
            {
                "shippers",
                "warehouses",
                "carriers",
                "products",
                "shipments",
                "shipment_events",
                "inventory_movements",
            },
        ),
        (
            "manufacturing",
            {
                "suppliers",
                "plants",
                "products",
                "work_orders",
                "production_runs",
                "quality_inspections",
                "inventory_movements",
            },
        ),
        (
            "media",
            {
                "users",
                "content_titles",
                "subscriptions",
                "viewing_events",
                "ad_campaigns",
                "ad_impressions",
                "game_sessions",
            },
        ),
        (
            "public_sector",
            {
                "residents",
                "agencies",
                "programs",
                "applications",
                "cases",
                "payments",
                "service_requests",
            },
        ),
        (
            "saas",
            {
                "organizations",
                "users",
                "plans",
                "subscriptions",
                "features",
                "usage_events",
                "invoices",
                "support_tickets",
            },
        ),
        (
            "hospitality",
            {
                "customers",
                "properties",
                "rooms",
                "reservations",
                "stays",
                "payments",
                "reviews",
            },
        ),
    ],
)
def test_additional_domains_generate_expected_tables(domain, expected_tables):
    data = generate_domain(domain, scale="tiny", seed=42)

    assert set(data) == expected_tables
    assert all(isinstance(frame, pd.DataFrame) for frame in data.values())
    assert all(len(frame) > 0 for frame in data.values())


def test_healthcare_high_risk_patients_have_more_encounters():
    data = generate_domain("healthcare", scale="small", seed=42)
    encounters = data["encounters"].merge(
        data["patients"][["patient_id", "risk_band"]], on="patient_id"
    )
    grouped = encounters.groupby("risk_band").size()

    assert (
        grouped["high"] / (data["patients"]["risk_band"] == "high").sum()
        > grouped["low"] / (data["patients"]["risk_band"] == "low").sum()
    )


def test_telecom_unlimited_plans_have_more_data_usage():
    data = generate_domain("telecom", scale="small", seed=42)
    usage = (
        data["usage_events"]
        .merge(data["subscriptions"][["subscription_id", "plan_id"]], on="subscription_id")
        .merge(data["plans"][["plan_id", "unlimited_data"]], on="plan_id")
    )
    data_usage = usage[usage["usage_type"] == "data"].groupby("unlimited_data")["data_mb"].mean()

    assert data_usage[True] > data_usage[False]


def test_logistics_delayed_shipments_have_delayed_status():
    data = generate_domain("logistics", scale="tiny", seed=42)
    delayed = data["shipments"][data["shipments"]["delayed"]]

    assert delayed.empty or set(delayed["delivery_status"]) == {"delayed"}


def test_saas_enterprise_organizations_have_more_users():
    data = generate_domain("saas", scale="small", seed=42)
    users = data["users"].merge(
        data["organizations"][["organization_id", "company_size"]], on="organization_id"
    )
    per_org = (
        users.groupby(["company_size", "organization_id"]).size().groupby("company_size").mean()
    )

    assert per_org["enterprise"] > per_org["smb"]

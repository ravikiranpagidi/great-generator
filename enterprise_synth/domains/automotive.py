"""Automotive domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from enterprise_synth.domains._industry import c, fk, generate_industry_pandas, table
from enterprise_synth.schemas.models import DomainSchema

CHOICES = {
    "customer_type": ["retail", "fleet", "dealer_group"],
    "vehicle_type": ["sedan", "suv", "truck", "ev", "hybrid", "commercial"],
    "fuel_type": ["gas", "diesel", "hybrid", "electric"],
    "dealer_region": ["northeast", "south", "midwest", "west"],
    "sale_channel": ["dealer", "online", "fleet", "auction"],
    "sale_status": ["completed", "financed", "cancelled", "returned"],
    "service_type": ["maintenance", "repair", "recall", "inspection", "software_update"],
    "service_status": ["completed", "scheduled", "cancelled", "parts_wait"],
    "claim_status": ["open", "approved", "denied", "paid"],
    "event_type": ["location", "battery", "diagnostic", "adas", "charging"],
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
                c("joined_date", "date"),
                c("customer_status", "string"),
            ),
            description="Retail, fleet, and dealer-group customers.",
        ),
        "dealers": table(
            "dealers",
            "dealer_id",
            (
                c("dealer_id", "int64"),
                c("dealer_name", "string"),
                c("dealer_region", "string"),
                c("dealer_type", "string"),
                c("active", "bool"),
            ),
            description="Dealership and online sales locations.",
        ),
        "vehicles": table(
            "vehicles",
            "vehicle_id",
            (
                c("vehicle_id", "int64"),
                c("vin_code", "string"),
                c("model_name", "string"),
                c("model_year", "int64"),
                c("vehicle_type", "string"),
                c("fuel_type", "string"),
                c("battery_capacity_kwh", "float64"),
            ),
            description="Vehicle inventory and connected-vehicle assets.",
        ),
        "sales": table(
            "sales",
            "sale_id",
            (
                c("sale_id", "int64"),
                c("customer_id", "int64"),
                c("dealer_id", "int64"),
                c("vehicle_id", "int64"),
                c("sale_date", "date"),
                c("sale_channel", "string"),
                c("sale_price", "float64"),
                c("sale_status", "string"),
            ),
            (
                fk("customer_id", "customers", "customer_id"),
                fk("dealer_id", "dealers", "dealer_id"),
                fk("vehicle_id", "vehicles", "vehicle_id"),
            ),
            "Vehicle sales and delivery records.",
        ),
        "service_appointments": table(
            "service_appointments",
            "service_appointment_id",
            (
                c("service_appointment_id", "int64"),
                c("customer_id", "int64"),
                c("dealer_id", "int64"),
                c("vehicle_id", "int64"),
                c("appointment_ts", "datetime64[ns]"),
                c("service_type", "string"),
                c("service_status", "string"),
                c("service_cost", "float64"),
            ),
            (
                fk("customer_id", "customers", "customer_id"),
                fk("dealer_id", "dealers", "dealer_id"),
                fk("vehicle_id", "vehicles", "vehicle_id"),
            ),
            "Maintenance, repair, recall, and software service events.",
        ),
        "warranty_claims": table(
            "warranty_claims",
            "warranty_claim_id",
            (
                c("warranty_claim_id", "int64"),
                c("vehicle_id", "int64"),
                c("dealer_id", "int64"),
                c("claim_date", "date"),
                c("claim_category", "string"),
                c("claim_status", "string"),
                c("claim_amount", "float64"),
            ),
            (fk("vehicle_id", "vehicles", "vehicle_id"), fk("dealer_id", "dealers", "dealer_id")),
            "Warranty and recall claim records.",
        ),
        "telematics_events": table(
            "telematics_events",
            "telematics_event_id",
            (
                c("telematics_event_id", "int64"),
                c("vehicle_id", "int64"),
                c("event_ts", "datetime64[ns]"),
                c("event_date", "date"),
                c("event_type", "string"),
                c("odometer_miles", "float64"),
                c("battery_level_percent", "float64"),
                c("diagnostic_score", "float64"),
            ),
            (fk("vehicle_id", "vehicles", "vehicle_id"),),
            "Connected vehicle telemetry for EV, diagnostics, and autonomous demos.",
        ),
    }
    return DomainSchema(
        name="automotive",
        tables=tables,
        description="Automotive domain for vehicle sales, dealerships, service, warranty, and telematics.",
        behaviors=(
            "EV and connected-vehicle telemetry",
            "Dealer and online sales channels",
            "Warranty and service lifecycle events",
            "Fleet and retail customer patterns",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)

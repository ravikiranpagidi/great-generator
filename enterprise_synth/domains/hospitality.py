"""Hospitality and travel domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from enterprise_synth.domains._industry import c, fk, generate_industry_pandas, table
from enterprise_synth.schemas.models import DomainSchema

CHOICES = {
    "customer_segment": ["leisure", "business", "loyalty", "group", "premium"],
    "property_type": ["hotel", "resort", "airport_hotel", "cruise", "vacation_rental"],
    "room_type": ["standard", "suite", "family", "accessible", "premium"],
    "booking_channel": ["direct", "ota", "corporate", "agency", "mobile"],
    "reservation_status": ["booked", "checked_in", "completed", "cancelled", "no_show"],
    "payment_status": ["paid", "authorized", "refunded", "failed"],
    "review_sentiment": ["positive", "neutral", "negative"],
    "loyalty_tier": ["none", "silver", "gold", "platinum"],
}


def schema() -> DomainSchema:
    tables = {
        "customers": table(
            "customers",
            "customer_id",
            (
                c("customer_id", "int64"),
                c("customer_code", "string"),
                c("customer_segment", "string"),
                c("loyalty_tier", "string"),
                c("region", "string"),
                c("joined_date", "date"),
            ),
        ),
        "properties": table(
            "properties",
            "property_id",
            (
                c("property_id", "int64"),
                c("property_name", "string"),
                c("property_type", "string"),
                c("region", "string"),
                c("star_rating", "float64"),
                c("active", "bool"),
            ),
        ),
        "rooms": table(
            "rooms",
            "room_id",
            (
                c("room_id", "int64"),
                c("property_id", "int64"),
                c("room_code", "string"),
                c("room_type", "string"),
                c("nightly_rate", "float64"),
                c("capacity_count", "int64"),
            ),
            (fk("property_id", "properties", "property_id"),),
            "Rooms and inventory units per property.",
        ),
        "reservations": table(
            "reservations",
            "reservation_id",
            (
                c("reservation_id", "int64"),
                c("customer_id", "int64"),
                c("property_id", "int64"),
                c("room_id", "int64"),
                c("booking_ts", "datetime64[ns]"),
                c("check_in_date", "date"),
                c("check_out_date", "date"),
                c("booking_channel", "string"),
                c("reservation_status", "string"),
                c("total_amount", "float64"),
            ),
            (
                fk("customer_id", "customers", "customer_id"),
                fk("property_id", "properties", "property_id"),
                fk("room_id", "rooms", "room_id"),
            ),
            "Bookings across direct, OTA, corporate, and agency channels.",
        ),
        "stays": table(
            "stays",
            "stay_id",
            (
                c("stay_id", "int64"),
                c("reservation_id", "int64"),
                c("customer_id", "int64"),
                c("property_id", "int64"),
                c("check_in_ts", "datetime64[ns]"),
                c("check_out_ts", "datetime64[ns]"),
                c("nights_count", "int64"),
                c("ancillary_revenue", "float64"),
            ),
            (
                fk("reservation_id", "reservations", "reservation_id"),
                fk("customer_id", "customers", "customer_id"),
                fk("property_id", "properties", "property_id"),
            ),
            "Actual stay records and ancillary spend.",
        ),
        "payments": table(
            "payments",
            "payment_id",
            (
                c("payment_id", "int64"),
                c("reservation_id", "int64"),
                c("customer_id", "int64"),
                c("payment_date", "date"),
                c("payment_amount", "float64"),
                c("payment_status", "string"),
            ),
            (
                fk("reservation_id", "reservations", "reservation_id"),
                fk("customer_id", "customers", "customer_id"),
            ),
            "Travel and lodging payment events.",
        ),
        "reviews": table(
            "reviews",
            "review_id",
            (
                c("review_id", "int64"),
                c("stay_id", "int64"),
                c("customer_id", "int64"),
                c("property_id", "int64"),
                c("review_date", "date"),
                c("rating_score", "float64"),
                c("review_sentiment", "string"),
            ),
            (
                fk("stay_id", "stays", "stay_id"),
                fk("customer_id", "customers", "customer_id"),
                fk("property_id", "properties", "property_id"),
            ),
            "Guest review and satisfaction records.",
        ),
    }
    return DomainSchema(
        name="hospitality",
        tables=tables,
        description="Hospitality and travel domain for customers, properties, rooms, reservations, stays, payments, and reviews.",
        behaviors=(
            "Direct and OTA booking channels",
            "Loyalty tiers and property types shape spend",
            "Reservations link to stays, payments, and reviews",
            "Useful for hotel, cruise, and travel analytics demos",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)

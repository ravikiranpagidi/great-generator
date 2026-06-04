"""Public sector and government domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from great_generator.domains._industry import c, fk, generate_industry_pandas, table
from great_generator.schemas.models import DomainSchema

CHOICES = {
    "resident_segment": ["household", "student", "business", "senior", "veteran"],
    "agency_type": ["municipal", "education", "tax", "defense", "health", "transportation"],
    "program_type": ["benefits", "permit", "tax", "education", "public_safety"],
    "application_status": ["submitted", "under_review", "approved", "denied", "withdrawn"],
    "case_status": ["open", "assigned", "resolved", "escalated", "closed"],
    "payment_type": ["tax", "fee", "fine", "benefit", "grant"],
    "payment_status": ["paid", "due", "late", "refunded"],
    "request_category": ["road", "water", "permit", "records", "school", "safety"],
    "request_status": ["new", "in_progress", "resolved", "closed"],
}


def schema() -> DomainSchema:
    tables = {
        "residents": table(
            "residents",
            "resident_id",
            (
                c("resident_id", "int64"),
                c("resident_code", "string"),
                c("resident_segment", "string"),
                c("region", "string"),
                c("enrolled_date", "date"),
                c("resident_status", "string"),
            ),
        ),
        "agencies": table(
            "agencies",
            "agency_id",
            (
                c("agency_id", "int64"),
                c("agency_name", "string"),
                c("agency_type", "string"),
                c("region", "string"),
                c("active", "bool"),
            ),
        ),
        "programs": table(
            "programs",
            "program_id",
            (
                c("program_id", "int64"),
                c("agency_id", "int64"),
                c("program_name", "string"),
                c("program_type", "string"),
                c("annual_budget", "float64"),
                c("active", "bool"),
            ),
            (fk("agency_id", "agencies", "agency_id"),),
            "Public programs administered by agencies.",
        ),
        "applications": table(
            "applications",
            "application_id",
            (
                c("application_id", "int64"),
                c("resident_id", "int64"),
                c("program_id", "int64"),
                c("application_ts", "datetime64[ns]"),
                c("application_status", "string"),
                c("requested_amount", "float64"),
                c("eligibility_score", "float64"),
            ),
            (
                fk("resident_id", "residents", "resident_id"),
                fk("program_id", "programs", "program_id"),
            ),
            "Program, permit, education, and tax applications.",
        ),
        "cases": table(
            "cases",
            "case_id",
            (
                c("case_id", "int64"),
                c("resident_id", "int64"),
                c("agency_id", "int64"),
                c("opened_ts", "datetime64[ns]"),
                c("case_category", "string"),
                c("case_status", "string"),
                c("priority_score", "float64"),
            ),
            (
                fk("resident_id", "residents", "resident_id"),
                fk("agency_id", "agencies", "agency_id"),
            ),
            "Government case management records.",
        ),
        "payments": table(
            "payments",
            "payment_id",
            (
                c("payment_id", "int64"),
                c("resident_id", "int64"),
                c("agency_id", "int64"),
                c("payment_date", "date"),
                c("payment_type", "string"),
                c("payment_amount", "float64"),
                c("payment_status", "string"),
            ),
            (
                fk("resident_id", "residents", "resident_id"),
                fk("agency_id", "agencies", "agency_id"),
            ),
            "Taxes, fees, fines, benefits, and grants.",
        ),
        "service_requests": table(
            "service_requests",
            "service_request_id",
            (
                c("service_request_id", "int64"),
                c("resident_id", "int64"),
                c("agency_id", "int64"),
                c("request_ts", "datetime64[ns]"),
                c("request_category", "string"),
                c("request_status", "string"),
                c("resolution_hours", "int64"),
            ),
            (
                fk("resident_id", "residents", "resident_id"),
                fk("agency_id", "agencies", "agency_id"),
            ),
            "Municipal and public service requests.",
        ),
    }
    return DomainSchema(
        name="public_sector",
        tables=tables,
        description="Public sector and government domain for agencies, programs, applications, cases, payments, and services.",
        behaviors=(
            "Agencies administer programs and cases",
            "Applications include eligibility and approval status",
            "Payments represent taxes, benefits, fees, and grants",
            "Service requests support municipal operations demos",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)

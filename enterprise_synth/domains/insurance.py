"""Insurance domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from enterprise_synth.domains._industry import c, fk, generate_industry_pandas, table
from enterprise_synth.schemas.models import DomainSchema

CHOICES = {
    "customer_type": ["individual", "small_business", "enterprise"],
    "policy_type": ["auto", "home", "life", "health", "commercial", "reinsurance"],
    "coverage_level": ["basic", "standard", "premium", "umbrella"],
    "policy_status": ["active", "pending", "lapsed", "cancelled"],
    "claim_type": ["collision", "property_damage", "medical", "liability", "life_event"],
    "claim_status": ["open", "investigating", "approved", "denied", "paid"],
    "payment_status": ["paid", "due", "late", "failed"],
    "risk_band": ["low", "medium", "high", "catastrophe"],
    "agent_channel": ["direct", "broker", "partner", "digital"],
    "reinsurer_name": ["Reinsurer North", "Reinsurer Harbor", "Reinsurer Global"],
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
                c("risk_band", "string"),
                c("customer_status", "string"),
                c("joined_date", "date"),
            ),
            description="Policyholders and insured entities.",
        ),
        "agents": table(
            "agents",
            "agent_id",
            (
                c("agent_id", "int64"),
                c("agent_name", "string"),
                c("agent_channel", "string"),
                c("region", "string"),
                c("active", "bool"),
            ),
            description="Agents, brokers, and digital acquisition channels.",
        ),
        "policies": table(
            "policies",
            "policy_id",
            (
                c("policy_id", "int64"),
                c("customer_id", "int64"),
                c("agent_id", "int64"),
                c("policy_type", "string"),
                c("coverage_level", "string"),
                c("effective_date", "date"),
                c("expiration_date", "date"),
                c("premium_amount", "float64"),
                c("policy_status", "string"),
            ),
            (fk("customer_id", "customers", "customer_id"), fk("agent_id", "agents", "agent_id")),
            "Insurance policies across consumer and commercial lines.",
        ),
        "claims": table(
            "claims",
            "claim_id",
            (
                c("claim_id", "int64"),
                c("policy_id", "int64"),
                c("customer_id", "int64"),
                c("claim_ts", "datetime64[ns]"),
                c("claim_type", "string"),
                c("claim_status", "string"),
                c("claim_amount", "float64"),
                c("approved_amount", "float64"),
                c("fraud_score", "float64"),
            ),
            (
                fk("policy_id", "policies", "policy_id"),
                fk("customer_id", "customers", "customer_id"),
            ),
            "Claims with severity, fraud, and adjudication state.",
        ),
        "premium_payments": table(
            "premium_payments",
            "payment_id",
            (
                c("payment_id", "int64"),
                c("policy_id", "int64"),
                c("customer_id", "int64"),
                c("payment_date", "date"),
                c("payment_amount", "float64"),
                c("payment_status", "string"),
            ),
            (
                fk("policy_id", "policies", "policy_id"),
                fk("customer_id", "customers", "customer_id"),
            ),
            "Recurring premium collection events.",
        ),
        "risk_assessments": table(
            "risk_assessments",
            "assessment_id",
            (
                c("assessment_id", "int64"),
                c("policy_id", "int64"),
                c("customer_id", "int64"),
                c("assessment_date", "date"),
                c("risk_band", "string"),
                c("risk_score", "float64"),
                c("underwriting_decision", "string"),
            ),
            (
                fk("policy_id", "policies", "policy_id"),
                fk("customer_id", "customers", "customer_id"),
            ),
            "Underwriting and renewal risk assessment records.",
        ),
        "reinsurance_contracts": table(
            "reinsurance_contracts",
            "reinsurance_contract_id",
            (
                c("reinsurance_contract_id", "int64"),
                c("policy_id", "int64"),
                c("reinsurer_name", "string"),
                c("contract_type", "string"),
                c("coverage_amount", "float64"),
                c("effective_date", "date"),
            ),
            (fk("policy_id", "policies", "policy_id"),),
            "Reinsurance coverage linked to selected policies.",
        ),
    }
    return DomainSchema(
        name="insurance",
        tables=tables,
        description="Insurance domain for policies, claims, premium payments, risk, and reinsurance.",
        behaviors=(
            "Policy type and coverage level influence premium and claims",
            "Claims carry adjudication and fraud-risk signals",
            "Premium payments support late-payment and lapse testing",
            "Reinsurance contracts model risk transfer for selected policies",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)

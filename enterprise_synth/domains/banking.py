"""Banking domain pack."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

import numpy as np
import pandas as pd

from enterprise_synth.cdc.generator import generate_customer_cdc
from enterprise_synth.distributions.time_patterns import (
    random_timestamps_on_dates,
    weighted_calendar_dates,
)
from enterprise_synth.distributions.weighted import normalize
from enterprise_synth.relationships.keys import KeyRegistry
from enterprise_synth.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema
from enterprise_synth.utils.random import get_rng


def _c(name: str, dtype: str, nullable: bool = False, description: str = "") -> ColumnSpec:
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable, description=description)


def schema() -> DomainSchema:
    tables = {
        "customers": TableSchema(
            name="customers",
            primary_key="customer_id",
            description="Retail and business customers with segment and risk bands.",
            columns=(
                _c("customer_id", "int64"),
                _c("customer_code", "string"),
                _c("customer_type", "string"),
                _c("segment", "string"),
                _c("opened_date", "date"),
                _c("status", "string"),
                _c("risk_band", "string"),
                _c("region", "string"),
            ),
        ),
        "accounts": TableSchema(
            name="accounts",
            primary_key="account_id",
            foreign_keys=(ForeignKey("customer_id", "customers", "customer_id"),),
            description="Deposit and credit accounts owned by customers.",
            columns=(
                _c("account_id", "int64"),
                _c("customer_id", "int64"),
                _c("account_type", "string"),
                _c("opened_date", "date"),
                _c("balance", "float64"),
                _c("status", "string"),
            ),
        ),
        "cards": TableSchema(
            name="cards",
            primary_key="card_id",
            foreign_keys=(ForeignKey("customer_id", "customers", "customer_id"),),
            description="Customer payment cards.",
            columns=(
                _c("card_id", "int64"),
                _c("customer_id", "int64"),
                _c("card_type", "string"),
                _c("issued_date", "date"),
                _c("status", "string"),
            ),
        ),
        "merchants": TableSchema(
            name="merchants",
            primary_key="merchant_id",
            description="Merchant dimension with category and risk signals.",
            columns=(
                _c("merchant_id", "int64"),
                _c("merchant_name", "string"),
                _c("merchant_category", "string"),
                _c("risk_band", "string"),
            ),
        ),
        "transactions": TableSchema(
            name="transactions",
            primary_key="transaction_id",
            foreign_keys=(
                ForeignKey("account_id", "accounts", "account_id"),
                ForeignKey("card_id", "cards", "card_id"),
                ForeignKey("merchant_id", "merchants", "merchant_id"),
            ),
            description="Financial events with payroll and weekend behavior.",
            columns=(
                _c("transaction_id", "int64"),
                _c("account_id", "int64"),
                _c("card_id", "Int64", nullable=True),
                _c("merchant_id", "int64"),
                _c("transaction_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("ingestion_timestamp", "datetime64[ns]"),
                _c("transaction_type", "string"),
                _c("direction", "string"),
                _c("amount", "float64"),
                _c("status", "string"),
                _c("is_late_arriving", "bool"),
                _c("duplicate_record", "bool"),
            ),
        ),
        "fraud_events": TableSchema(
            name="fraud_events",
            primary_key="fraud_event_id",
            foreign_keys=(ForeignKey("transaction_id", "transactions", "transaction_id"),),
            description="Rare, clustered fraud labels tied to transactions.",
            columns=(
                _c("fraud_event_id", "int64"),
                _c("transaction_id", "int64"),
                _c("event_ts", "datetime64[ns]"),
                _c("fraud_type", "string"),
                _c("risk_score", "float64"),
                _c("status", "string"),
            ),
        ),
        "cdc_customer_changes": TableSchema(
            name="cdc_customer_changes",
            primary_key="sequence_number",
            foreign_keys=(ForeignKey("customer_id", "customers", "customer_id"),),
            description="CDC-like customer events for pipeline testing.",
            columns=(
                _c("customer_id", "int64"),
                _c("operation", "string"),
                _c("before", "string", nullable=True),
                _c("after", "string", nullable=True),
                _c("event_timestamp", "datetime64[ns]"),
                _c("ingestion_timestamp", "datetime64[ns]"),
                _c("sequence_number", "int64"),
                _c("source_system", "string"),
                _c("late_arriving", "bool"),
                _c("duplicate", "bool"),
            ),
        ),
    }
    return DomainSchema(
        name="banking",
        tables=tables,
        description="A banking domain with customers, accounts, transactions, fraud, and CDC events.",
        behaviors=(
            "Customers can own multiple accounts and cards",
            "Account and customer type influence spend",
            "Transactions rise around payroll dates and weekends",
            "Fraud is rare but clustered",
            "CDC records model inserts, updates, deletes, duplicates, and late arrivals",
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

    customer_rng = get_rng(seed, "banking.customers")
    customer_count = row_counts["customers"]
    customer_ids = np.arange(1, customer_count + 1, dtype=np.int64)
    customer_types = customer_rng.choice(["individual", "business"], customer_count, p=[0.84, 0.16])
    segments = np.where(
        customer_types == "business",
        customer_rng.choice(["smb", "enterprise"], customer_count, p=[0.82, 0.18]),
        customer_rng.choice(["mass", "premium"], customer_count, p=[0.78, 0.22]),
    )
    opened_dates = weighted_calendar_dates(
        customer_rng,
        customer_count,
        start="2020-01-01",
        end="2025-12-31",
        weekend_multiplier=1.0,
        holiday_multiplier=1.0,
    )
    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_code": [f"CUS{value:08d}" for value in customer_ids],
            "customer_type": customer_types,
            "segment": segments,
            "opened_date": opened_dates.date,
            "status": customer_rng.choice(
                ["active", "dormant", "closed"], customer_count, p=[0.89, 0.08, 0.03]
            ),
            "risk_band": customer_rng.choice(
                ["low", "medium", "high"], customer_count, p=[0.74, 0.22, 0.04]
            ),
            "region": customer_rng.choice(
                ["northeast", "south", "midwest", "west"],
                customer_count,
                p=[0.24, 0.34, 0.20, 0.22],
            ),
        }
    )
    registry.register("customers", customer_ids)

    account_rng = get_rng(seed, "banking.accounts")
    account_count = row_counts["accounts"]
    account_ids = np.arange(1, account_count + 1, dtype=np.int64)
    customer_weights = (
        customers["customer_type"].map({"individual": 1.0, "business": 2.3}).to_numpy(dtype=float)
    )
    account_customer_ids = _base_or_sample(customer_ids, account_count, account_rng)
    if account_count > customer_count:
        extra_count = account_count - customer_count
        account_customer_ids[-extra_count:] = account_rng.choice(
            customer_ids,
            size=extra_count,
            replace=True,
            p=normalize(customer_weights),
        )
    account_types = account_rng.choice(
        ["checking", "savings", "credit", "business_checking"],
        account_count,
        p=[0.42, 0.28, 0.20, 0.10],
    )
    owning_types = (
        customers.set_index("customer_id").loc[account_customer_ids, "customer_type"].to_numpy()
    )
    account_types = np.where(
        (owning_types == "business") & (account_rng.random(account_count) < 0.55),
        "business_checking",
        account_types,
    )
    balance_means = (
        pd.Series(account_types)
        .map({"checking": 8.1, "savings": 9.2, "credit": 7.4, "business_checking": 10.0})
        .to_numpy()
    )
    balances = np.round(account_rng.lognormal(balance_means, 0.65), 2)
    accounts = pd.DataFrame(
        {
            "account_id": account_ids,
            "customer_id": account_customer_ids,
            "account_type": account_types,
            "opened_date": weighted_calendar_dates(
                account_rng,
                account_count,
                start="2020-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
            "balance": balances,
            "status": account_rng.choice(
                ["open", "restricted", "closed"], account_count, p=[0.93, 0.04, 0.03]
            ),
        }
    )
    registry.register("accounts", account_ids)

    card_rng = get_rng(seed, "banking.cards")
    card_count = row_counts["cards"]
    card_ids = np.arange(1, card_count + 1, dtype=np.int64)
    card_customer_ids = _base_or_sample(customer_ids, card_count, card_rng)
    cards = pd.DataFrame(
        {
            "card_id": card_ids,
            "customer_id": card_customer_ids,
            "card_type": card_rng.choice(
                ["debit", "credit", "corporate"], card_count, p=[0.60, 0.33, 0.07]
            ),
            "issued_date": weighted_calendar_dates(
                card_rng,
                card_count,
                start="2021-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
            "status": card_rng.choice(
                ["active", "blocked", "expired"], card_count, p=[0.94, 0.03, 0.03]
            ),
        }
    )
    registry.register("cards", card_ids)

    merchant_rng = get_rng(seed, "banking.merchants")
    merchant_count = row_counts["merchants"]
    merchant_ids = np.arange(1, merchant_count + 1, dtype=np.int64)
    merchant_categories = merchant_rng.choice(
        ["grocery", "fuel", "travel", "restaurant", "ecommerce", "utilities", "cash_like"],
        merchant_count,
        p=[0.22, 0.12, 0.10, 0.18, 0.20, 0.12, 0.06],
    )
    merchants = pd.DataFrame(
        {
            "merchant_id": merchant_ids,
            "merchant_name": [f"Merchant {value:05d}" for value in merchant_ids],
            "merchant_category": merchant_categories,
            "risk_band": np.where(
                merchant_categories == "cash_like",
                merchant_rng.choice(["medium", "high"], merchant_count, p=[0.35, 0.65]),
                merchant_rng.choice(
                    ["low", "medium", "high"], merchant_count, p=[0.72, 0.24, 0.04]
                ),
            ),
        }
    )
    registry.register("merchants", merchant_ids)

    txn_rng = get_rng(seed, "banking.transactions")
    txn_count = row_counts["transactions"]
    account_type_weights = (
        accounts["account_type"]
        .map({"checking": 1.0, "savings": 0.35, "credit": 1.25, "business_checking": 1.8})
        .to_numpy(dtype=float)
    )
    transaction_account_ids = registry.sample(
        "accounts", txn_count, txn_rng, normalize(account_type_weights)
    )
    txn_accounts = accounts.set_index("account_id").loc[transaction_account_ids].reset_index()
    transaction_customer_ids = txn_accounts["customer_id"].to_numpy()

    cards_by_customer: dict[int, list[int]] = defaultdict(list)
    for row in cards.itertuples(index=False):
        cards_by_customer[int(row.customer_id)].append(int(row.card_id))
    card_usage = txn_rng.random(txn_count) < 0.67
    chosen_cards: list[int | None] = []
    for customer_id, uses_card in zip(transaction_customer_ids, card_usage):
        available = cards_by_customer[int(customer_id)]
        chosen_cards.append(int(txn_rng.choice(available)) if uses_card and available else None)

    merchant_weights = (
        merchants["merchant_category"]
        .map(
            {
                "grocery": 0.22,
                "fuel": 0.12,
                "travel": 0.08,
                "restaurant": 0.18,
                "ecommerce": 0.22,
                "utilities": 0.12,
                "cash_like": 0.06,
            }
        )
        .to_numpy(dtype=float)
    )
    transaction_merchant_ids = registry.sample(
        "merchants", txn_count, txn_rng, normalize(merchant_weights)
    )
    txn_merchants = merchants.set_index("merchant_id").loc[transaction_merchant_ids].reset_index()

    txn_dates = weighted_calendar_dates(
        txn_rng,
        txn_count,
        weekend_multiplier=1.25,
        holiday_multiplier=1.1,
        payroll_multiplier=1.55,
    )
    txn_ts = random_timestamps_on_dates(txn_rng, txn_dates, business_hours_bias=0.52)
    customer_type_lookup = customers.set_index("customer_id")["customer_type"]
    owning_customer_types = pd.Series(transaction_customer_ids).map(customer_type_lookup).to_numpy()
    merchant_amount_factor = (
        txn_merchants["merchant_category"]
        .map(
            {
                "grocery": 0.7,
                "fuel": 0.8,
                "travel": 2.2,
                "restaurant": 0.9,
                "ecommerce": 1.1,
                "utilities": 1.3,
                "cash_like": 1.6,
            }
        )
        .to_numpy(dtype=float)
    )
    account_amount_factor = (
        txn_accounts["account_type"]
        .map({"checking": 1.0, "savings": 0.7, "credit": 1.15, "business_checking": 1.8})
        .to_numpy(dtype=float)
    )
    customer_amount_factor = np.where(owning_customer_types == "business", 2.4, 1.0)
    amounts = np.round(
        txn_rng.lognormal(mean=3.55, sigma=0.75, size=txn_count)
        * merchant_amount_factor
        * account_amount_factor
        * customer_amount_factor,
        2,
    )
    transaction_types = txn_rng.choice(
        ["card_purchase", "ach_credit", "atm_withdrawal", "transfer"],
        txn_count,
        p=[0.66, 0.12, 0.08, 0.14],
    )
    directions = np.where(np.isin(transaction_types, ["ach_credit"]), "credit", "debit")
    ingestion_ts = txn_ts + pd.to_timedelta(txn_rng.integers(0, 180, size=txn_count), unit="m")
    transactions = pd.DataFrame(
        {
            "transaction_id": np.arange(1, txn_count + 1, dtype=np.int64),
            "account_id": transaction_account_ids,
            "card_id": pd.Series(chosen_cards, dtype="Int64"),
            "merchant_id": transaction_merchant_ids,
            "transaction_ts": txn_ts,
            "event_date": txn_ts.dt.date,
            "ingestion_timestamp": ingestion_ts,
            "transaction_type": transaction_types,
            "direction": directions,
            "amount": amounts,
            "status": txn_rng.choice(
                ["posted", "pending", "reversed"], txn_count, p=[0.94, 0.04, 0.02]
            ),
            "is_late_arriving": False,
            "duplicate_record": False,
        }
    )
    registry.register("transactions", transactions["transaction_id"])

    fraud_rng = get_rng(seed, "banking.fraud")
    fraud_count = row_counts["fraud_events"]
    if fraud_count:
        cluster_customer_count = max(1, min(customer_count, max(1, customer_count // 100)))
        clustered_customers = set(
            fraud_rng.choice(customer_ids, size=cluster_customer_count, replace=False).tolist()
        )
        fraud_weights = np.where(
            pd.Series(transaction_customer_ids).isin(clustered_customers),
            8.0,
            1.0,
        ) * np.where(txn_merchants["risk_band"].to_numpy() == "high", 4.0, 1.0)
        fraud_transaction_ids = fraud_rng.choice(
            transactions["transaction_id"].to_numpy(),
            size=fraud_count,
            replace=fraud_count > txn_count,
            p=normalize(fraud_weights.astype(float)),
        )
        fraud_txns = (
            transactions.set_index("transaction_id").loc[fraud_transaction_ids].reset_index()
        )
        fraud_events = pd.DataFrame(
            {
                "fraud_event_id": np.arange(1, fraud_count + 1, dtype=np.int64),
                "transaction_id": fraud_transaction_ids,
                "event_ts": fraud_txns["transaction_ts"]
                + pd.to_timedelta(fraud_rng.integers(5, 720, size=fraud_count), unit="m"),
                "fraud_type": fraud_rng.choice(
                    ["card_testing", "account_takeover", "merchant_abuse", "velocity_spike"],
                    fraud_count,
                    p=[0.22, 0.28, 0.18, 0.32],
                ),
                "risk_score": np.round(fraud_rng.uniform(0.72, 0.99, size=fraud_count), 3),
                "status": fraud_rng.choice(
                    ["confirmed", "review", "dismissed"], fraud_count, p=[0.58, 0.32, 0.10]
                ),
            }
        )
    else:
        fraud_events = pd.DataFrame(
            columns=[
                "fraud_event_id",
                "transaction_id",
                "event_ts",
                "fraud_type",
                "risk_score",
                "status",
            ]
        )

    cdc_customer_changes = generate_customer_cdc(
        customers,
        rows=row_counts["cdc_customer_changes"],
        late_arrival_rate=0.0,
        duplicate_rate=0.0,
        seed=seed,
    )

    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "cards": cards,
        "merchants": merchants,
        "fraud_events": fraud_events,
        "cdc_customer_changes": cdc_customer_changes,
    }

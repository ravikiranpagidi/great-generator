import pandas as pd

from enterprise_synth import generate_domain


def test_banking_domain_generates_expected_tables():
    data = generate_domain("banking", scale="tiny", seed=42)
    assert set(data) == {
        "customers",
        "accounts",
        "transactions",
        "cards",
        "merchants",
        "fraud_events",
        "cdc_customer_changes",
    }


def test_banking_tables_have_expected_columns():
    data = generate_domain("banking", scale="tiny", seed=42)
    assert {"customer_id", "customer_type", "segment"}.issubset(data["customers"].columns)
    assert {"account_id", "customer_id", "account_type"}.issubset(data["accounts"].columns)
    assert {"transaction_id", "account_id", "merchant_id", "amount"}.issubset(
        data["transactions"].columns
    )


def test_banking_outputs_are_pandas_dataframes():
    data = generate_domain("banking", scale="tiny", seed=42)
    assert all(isinstance(frame, pd.DataFrame) for frame in data.values())


def test_business_customers_have_higher_average_transaction_amounts():
    data = generate_domain("banking", scale="small", seed=42)
    txns = (
        data["transactions"]
        .merge(data["accounts"][["account_id", "customer_id"]], on="account_id")
        .merge(
            data["customers"][["customer_id", "customer_type"]],
            on="customer_id",
        )
    )
    grouped = txns.groupby("customer_type")["amount"].mean()
    assert grouped["business"] > grouped["individual"]

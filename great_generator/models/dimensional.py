"""Dimensional model generation for domain packs."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def generate_dimensional_model(
    domain: str,
    source: Mapping[str, pd.DataFrame],
    model: str = "star",
    grain: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Build a star-style dimensional model from generated domain tables."""

    if model != "star":
        raise ValueError("Only model='star' is currently supported.")
    if domain == "ecommerce":
        return _ecommerce(source, grain=grain or "order_item")
    if domain == "banking":
        return _banking(source, grain=grain or "transaction")
    return _generic_star(domain, source)


def _date_dim(dates: pd.Series) -> pd.DataFrame:
    parsed = pd.to_datetime(dates).dt.date.dropna().drop_duplicates().sort_values()
    frame = pd.DataFrame({"date": parsed})
    if frame.empty:
        return pd.DataFrame(columns=["date_key", "date", "year", "month", "day", "day_of_week"])
    values = pd.to_datetime(frame["date"])
    frame["date_key"] = values.dt.strftime("%Y%m%d").astype(int)
    frame["year"] = values.dt.year
    frame["month"] = values.dt.month
    frame["day"] = values.dt.day
    frame["day_of_week"] = values.dt.day_name()
    return frame[["date_key", "date", "year", "month", "day", "day_of_week"]]


def _ecommerce(source: Mapping[str, pd.DataFrame], grain: str) -> dict[str, pd.DataFrame]:
    if grain != "order_item":
        raise ValueError("Ecommerce dimensional model currently supports grain='order_item'.")
    customers = source["customers"].copy()
    products = source["products"].copy()
    orders = source["orders"].copy()
    items = source["order_items"].copy()
    payments = source["payments"].copy()

    dim_customer = customers.rename(columns={"customer_id": "customer_key"})
    dim_product = products.rename(columns={"product_id": "product_key"})
    dim_date = _date_dim(orders["event_date"])

    fact_sales = (
        items.merge(
            orders[["order_id", "customer_id", "event_date", "order_status"]], on="order_id"
        )
        .assign(
            customer_key=lambda frame: frame["customer_id"],
            product_key=lambda frame: frame["product_id"],
            date_key=lambda frame: pd.to_datetime(frame["event_date"])
            .dt.strftime("%Y%m%d")
            .astype(int),
        )
        .rename(columns={"order_item_id": "sales_fact_key"})
    )
    fact_sales = fact_sales[
        [
            "sales_fact_key",
            "order_id",
            "customer_key",
            "product_key",
            "date_key",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_amount",
            "order_status",
        ]
    ]

    fact_payments = (
        payments.merge(orders[["order_id", "customer_id", "event_date"]], on="order_id")
        .assign(
            customer_key=lambda frame: frame["customer_id"],
            date_key=lambda frame: pd.to_datetime(frame["event_date"])
            .dt.strftime("%Y%m%d")
            .astype(int),
        )
        .rename(columns={"payment_id": "payment_fact_key"})
    )
    fact_payments = fact_payments[
        [
            "payment_fact_key",
            "order_id",
            "customer_key",
            "date_key",
            "payment_method",
            "payment_status",
            "amount",
            "refunded_amount",
        ]
    ]
    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_date": dim_date,
        "fact_sales": fact_sales,
        "fact_payments": fact_payments,
        "_model_metadata": _metadata("dimensional", "ecommerce", grain),
    }


def _banking(source: Mapping[str, pd.DataFrame], grain: str) -> dict[str, pd.DataFrame]:
    if grain != "transaction":
        raise ValueError("Banking dimensional model currently supports grain='transaction'.")
    customers = source["customers"].copy()
    accounts = source["accounts"].copy()
    merchants = source["merchants"].copy()
    transactions = source["transactions"].copy()
    fraud = source["fraud_events"].copy()

    dim_customer = customers.rename(columns={"customer_id": "customer_key"})
    dim_account = accounts.rename(
        columns={"account_id": "account_key", "customer_id": "customer_key"}
    )
    dim_merchant = merchants.rename(columns={"merchant_id": "merchant_key"})
    dim_date = _date_dim(transactions["event_date"])

    fact_transactions = transactions.merge(
        accounts[["account_id", "customer_id"]], on="account_id"
    ).assign(
        transaction_fact_key=lambda frame: frame["transaction_id"],
        account_key=lambda frame: frame["account_id"],
        customer_key=lambda frame: frame["customer_id"],
        merchant_key=lambda frame: frame["merchant_id"],
        date_key=lambda frame: pd.to_datetime(frame["event_date"])
        .dt.strftime("%Y%m%d")
        .astype(int),
    )
    fact_transactions = fact_transactions[
        [
            "transaction_fact_key",
            "transaction_id",
            "account_key",
            "customer_key",
            "merchant_key",
            "date_key",
            "transaction_type",
            "direction",
            "amount",
            "status",
        ]
    ]

    fact_fraud = fraud.merge(
        transactions[["transaction_id", "account_id", "merchant_id", "event_date"]]
    ).assign(
        fraud_fact_key=lambda frame: frame["fraud_event_id"],
        account_key=lambda frame: frame["account_id"],
        merchant_key=lambda frame: frame["merchant_id"],
        date_key=lambda frame: pd.to_datetime(frame["event_date"])
        .dt.strftime("%Y%m%d")
        .astype(int),
    )
    fact_fraud = fact_fraud[
        [
            "fraud_fact_key",
            "transaction_id",
            "account_key",
            "merchant_key",
            "date_key",
            "fraud_type",
            "risk_score",
            "status",
        ]
    ]
    return {
        "dim_customer": dim_customer,
        "dim_account": dim_account,
        "dim_merchant": dim_merchant,
        "dim_date": dim_date,
        "fact_transactions": fact_transactions,
        "fact_fraud": fact_fraud,
        "_model_metadata": _metadata("dimensional", "banking", grain),
    }


def _generic_star(domain: str, source: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    for table_name, frame in source.items():
        if table_name.startswith("_"):
            continue
        prefix = (
            "fact"
            if any(
                token in table_name
                for token in (
                    "event",
                    "transaction",
                    "claim",
                    "payment",
                    "invoice",
                    "usage",
                    "order",
                )
            )
            else "dim"
        )
        result[f"{prefix}_{table_name}"] = frame.copy()
    result["_model_metadata"] = _metadata("dimensional", domain, "generic")
    return result


def _metadata(model_type: str, domain: str, grain: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_type": model_type,
                "domain": domain,
                "grain": grain,
                "generated_by": "great-generator",
            }
        ]
    )

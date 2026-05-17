import pandas as pd

from enterprise_synth import generate_domain


def test_ecommerce_domain_generates_expected_tables():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    assert set(data) == {
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
        "shipments",
        "returns",
    }


def test_ecommerce_tables_have_expected_columns():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    assert {"customer_id", "customer_segment", "signup_date"}.issubset(data["customers"].columns)
    assert {"order_id", "customer_id", "total_amount"}.issubset(data["orders"].columns)
    assert {"order_item_id", "order_id", "product_id", "line_amount"}.issubset(
        data["order_items"].columns
    )


def test_ecommerce_outputs_are_pandas_dataframes():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    assert all(isinstance(frame, pd.DataFrame) for frame in data.values())


def test_ecommerce_order_totals_are_positive():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    assert (data["orders"]["total_amount"] >= 0).all()

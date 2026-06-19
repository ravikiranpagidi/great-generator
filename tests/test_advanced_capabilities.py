import json

import pandas as pd

from great_generator import (
    generate_data_vault_model,
    generate_dimensional_model,
    generate_domain,
    generate_from_recipe,
    generate_history,
)


def test_anomaly_labels_round_trip_for_invalid_status():
    data = generate_domain(
        "ecommerce",
        scale="tiny",
        seed=42,
        anomalies={"invalid_status_rate": 1.0},
        return_labels=True,
    )

    labels = data["_anomaly_labels"]
    status_labels = labels[labels["anomaly_type"] == "invalid_status"]

    assert not status_labels.empty
    for label in status_labels.itertuples(index=False):
        assert data[label.table].loc[label.row_index, label.column] == label.corrupted_value
        assert label.corrupted_value == "__INVALID__"


def test_generate_history_returns_valid_scd2_intervals():
    history = generate_history("ecommerce", table="customers", scale="tiny", seed=42)

    assert {"effective_from", "effective_to", "is_current"}.issubset(history.columns)
    assert history.groupby("customer_id")["is_current"].sum().eq(1).all()

    for _, group in history.sort_values(["customer_id", "effective_from"]).groupby("customer_id"):
        previous_to = None
        for row in group.itertuples(index=False):
            assert row.effective_from < row.effective_to
            if previous_to is not None:
                assert row.effective_from == previous_to
            previous_to = row.effective_to


def test_generate_domain_can_include_history_tables():
    data = generate_domain("banking", scale="tiny", seed=42, history="scd2")

    assert "customers_history" in data
    assert data["customers_history"].groupby("customer_id")["is_current"].sum().eq(1).all()


def test_recipe_generation_is_deterministic(tmp_path):
    recipe = {
        "kind": "domain",
        "domain": "banking",
        "scale": "tiny",
        "seed": 42,
        "realism": "realistic",
    }
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(recipe), encoding="utf-8")

    first = generate_from_recipe(path)
    second = generate_from_recipe(path)

    pd.testing.assert_frame_equal(first["customers"], second["customers"])
    pd.testing.assert_frame_equal(first["transactions"], second["transactions"])


def test_yaml_recipe_generation_is_supported(tmp_path):
    path = tmp_path / "recipe.yaml"
    path.write_text(
        "\n".join(
            [
                "kind: domain",
                "domain: ecommerce",
                "scale: tiny",
                "realism: realistic",
                "seed: 42",
            ]
        ),
        encoding="utf-8",
    )

    data = generate_from_recipe(path)

    assert {"customers", "orders", "order_items"}.issubset(data)


def test_ecommerce_dimensional_model_has_valid_fact_references():
    model = generate_dimensional_model("ecommerce", scale="tiny", seed=42)

    assert {"dim_customer", "dim_product", "dim_date", "fact_sales"}.issubset(model)
    fact = model["fact_sales"]

    assert fact["customer_key"].isin(model["dim_customer"]["customer_key"]).all()
    assert fact["product_key"].isin(model["dim_product"]["product_key"]).all()
    assert fact["date_key"].isin(model["dim_date"]["date_key"]).all()


def test_banking_dimensional_model_has_transaction_fact_grain():
    model = generate_dimensional_model("banking", scale="tiny", seed=42)

    fact = model["fact_transactions"]
    assert fact["transaction_id"].is_unique
    assert fact["account_key"].isin(model["dim_account"]["account_key"]).all()
    assert fact["merchant_key"].isin(model["dim_merchant"]["merchant_key"]).all()


def test_data_vault_model_has_valid_hubs_and_links():
    vault = generate_data_vault_model("ecommerce", scale="tiny", seed=42)

    assert {"hub_customer", "hub_order", "hub_product", "link_order_customer"}.issubset(vault)
    assert vault["hub_customer"]["hub_customer_key"].is_unique
    assert vault["hub_order"]["hub_order_key"].is_unique
    assert (
        vault["link_order_customer"]["hub_order_key"]
        .isin(vault["hub_order"]["hub_order_key"])
        .all()
    )
    assert (
        vault["link_order_customer"]["hub_customer_key"]
        .isin(vault["hub_customer"]["hub_customer_key"])
        .all()
    )

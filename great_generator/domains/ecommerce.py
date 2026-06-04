"""Ecommerce domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from great_generator.distributions.time_patterns import (
    random_timestamps_on_dates,
    weighted_calendar_dates,
)
from great_generator.distributions.weighted import normalize, pareto_like_weights
from great_generator.relationships.keys import KeyRegistry
from great_generator.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema
from great_generator.utils.random import get_rng


def _c(name: str, dtype: str, nullable: bool = False, description: str = "") -> ColumnSpec:
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable, description=description)


def schema() -> DomainSchema:
    tables = {
        "customers": TableSchema(
            name="customers",
            primary_key="customer_id",
            description="Customer master data with lifecycle and segment signals.",
            columns=(
                _c("customer_id", "int64"),
                _c("customer_code", "string"),
                _c("customer_segment", "string"),
                _c("customer_status", "string"),
                _c("signup_date", "date"),
                _c("country", "string"),
                _c("age", "int64"),
            ),
        ),
        "products": TableSchema(
            name="products",
            primary_key="product_id",
            description="Catalog products with category-sensitive price ranges.",
            columns=(
                _c("product_id", "int64"),
                _c("sku", "string"),
                _c("category", "string"),
                _c("brand", "string"),
                _c("list_price", "float64"),
                _c("active", "bool"),
            ),
        ),
        "orders": TableSchema(
            name="orders",
            primary_key="order_id",
            foreign_keys=(ForeignKey("customer_id", "customers", "customer_id"),),
            description="Customer orders with seasonality, spend, and lifecycle behavior.",
            columns=(
                _c("order_id", "int64"),
                _c("customer_id", "int64"),
                _c("order_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("order_status", "string"),
                _c("subtotal", "float64"),
                _c("tax", "float64"),
                _c("shipping_fee", "float64"),
                _c("total_amount", "float64"),
            ),
        ),
        "order_items": TableSchema(
            name="order_items",
            primary_key="order_item_id",
            foreign_keys=(
                ForeignKey("order_id", "orders", "order_id"),
                ForeignKey("product_id", "products", "product_id"),
            ),
            description="Line items connecting orders to products.",
            columns=(
                _c("order_item_id", "int64"),
                _c("order_id", "int64"),
                _c("product_id", "int64"),
                _c("quantity", "int64"),
                _c("unit_price", "float64"),
                _c("discount_amount", "float64"),
                _c("line_amount", "float64"),
            ),
        ),
        "payments": TableSchema(
            name="payments",
            primary_key="payment_id",
            foreign_keys=(ForeignKey("order_id", "orders", "order_id"),),
            description="Payments with captured, failed, and refunded states.",
            columns=(
                _c("payment_id", "int64"),
                _c("order_id", "int64"),
                _c("payment_ts", "datetime64[ns]"),
                _c("payment_method", "string"),
                _c("payment_status", "string"),
                _c("amount", "float64"),
                _c("refunded_amount", "float64"),
            ),
        ),
        "shipments": TableSchema(
            name="shipments",
            primary_key="shipment_id",
            foreign_keys=(ForeignKey("order_id", "orders", "order_id"),),
            description="Fulfilment records with carrier and delay behavior.",
            columns=(
                _c("shipment_id", "int64"),
                _c("order_id", "int64"),
                _c("shipment_ts", "datetime64[ns]"),
                _c("delivery_ts", "datetime64[ns]"),
                _c("carrier", "string"),
                _c("shipment_status", "string"),
                _c("delayed", "bool"),
            ),
        ),
        "returns": TableSchema(
            name="returns",
            primary_key="return_id",
            foreign_keys=(ForeignKey("order_id", "orders", "order_id"),),
            description="Returns biased toward higher-return categories.",
            columns=(
                _c("return_id", "int64"),
                _c("order_id", "int64"),
                _c("return_ts", "datetime64[ns]"),
                _c("return_reason", "string"),
                _c("return_status", "string"),
                _c("refund_amount", "float64"),
            ),
        ),
    }
    return DomainSchema(
        name="ecommerce",
        tables=tables,
        description="A retail domain with customers, catalog, orders, fulfilment, and returns.",
        behaviors=(
            "Pareto-style customer ordering behavior",
            "Weekend and holiday season order lift",
            "Category-sensitive pricing and return propensity",
            "Payment failures, refunds, and shipment delays",
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

    customer_rng = get_rng(seed, "ecommerce.customers")
    customer_count = row_counts["customers"]
    customer_ids = np.arange(1, customer_count + 1, dtype=np.int64)
    segments = customer_rng.choice(
        np.array(["vip", "standard", "new", "inactive"]),
        size=customer_count,
        p=[0.08, 0.68, 0.14, 0.10],
    )
    signup_dates = weighted_calendar_dates(
        customer_rng,
        customer_count,
        start="2023-01-01",
        end="2025-12-31",
        weekend_multiplier=1.0,
        holiday_multiplier=1.0,
    )
    recent_signup = pd.date_range("2025-10-01", "2025-12-31", freq="D")
    new_mask = segments == "new"
    if new_mask.any():
        signup_dates_array = signup_dates.to_numpy().copy()
        signup_dates_array[new_mask] = customer_rng.choice(
            recent_signup.to_numpy(), size=int(new_mask.sum())
        )
        signup_dates = pd.DatetimeIndex(signup_dates_array)
    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_code": [f"CUST{value:08d}" for value in customer_ids],
            "customer_segment": segments,
            "customer_status": np.where(segments == "inactive", "inactive", "active"),
            "signup_date": signup_dates.date,
            "country": customer_rng.choice(
                ["US", "CA", "GB", "DE", "IN", "AU"],
                size=customer_count,
                p=[0.48, 0.10, 0.12, 0.08, 0.17, 0.05],
            ),
            "age": customer_rng.integers(18, 76, size=customer_count),
        }
    )
    registry.register("customers", customer_ids)

    product_rng = get_rng(seed, "ecommerce.products")
    product_count = row_counts["products"]
    product_ids = np.arange(1, product_count + 1, dtype=np.int64)
    categories = product_rng.choice(
        ["electronics", "apparel", "home", "beauty", "sports", "grocery"],
        size=product_count,
        p=[0.18, 0.24, 0.18, 0.12, 0.12, 0.16],
    )
    price_ranges = {
        "electronics": (4.7, 0.55),
        "apparel": (3.6, 0.45),
        "home": (4.1, 0.50),
        "beauty": (3.2, 0.40),
        "sports": (4.0, 0.48),
        "grocery": (2.6, 0.35),
    }
    prices = np.array(
        [round(float(product_rng.lognormal(*price_ranges[category])), 2) for category in categories]
    )
    products = pd.DataFrame(
        {
            "product_id": product_ids,
            "sku": [f"SKU{value:07d}" for value in product_ids],
            "category": categories,
            "brand": product_rng.choice(
                ["Northstar", "Aster", "Harbor", "Nimbus", "Keystone"], product_count
            ),
            "list_price": prices,
            "active": product_rng.random(product_count) > 0.03,
        }
    )
    registry.register("products", product_ids)

    order_rng = get_rng(seed, "ecommerce.orders")
    order_count = row_counts["orders"]
    order_ids = np.arange(1, order_count + 1, dtype=np.int64)
    customer_base_weights = pareto_like_weights(customer_count)
    customer_rank_order = order_rng.permutation(customer_count)
    customer_weights = np.empty(customer_count, dtype=float)
    customer_weights[customer_rank_order] = customer_base_weights
    segment_multiplier = (
        customers["customer_segment"]
        .map({"vip": 2.8, "standard": 1.0, "new": 0.45, "inactive": 0.08})
        .to_numpy()
    )
    customer_weights = normalize(customer_weights * segment_multiplier)
    sampled_customers = registry.sample("customers", order_count, order_rng, customer_weights)
    order_dates = weighted_calendar_dates(order_rng, order_count)
    order_ts = random_timestamps_on_dates(order_rng, order_dates, business_hours_bias=0.55)
    orders = pd.DataFrame(
        {
            "order_id": order_ids,
            "customer_id": sampled_customers,
            "order_ts": order_ts,
            "event_date": order_ts.dt.date,
            "order_status": order_rng.choice(
                ["completed", "pending", "cancelled"], size=order_count, p=[0.88, 0.08, 0.04]
            ),
            "subtotal": np.zeros(order_count),
            "tax": np.zeros(order_count),
            "shipping_fee": np.zeros(order_count),
            "total_amount": np.zeros(order_count),
        }
    )
    registry.register("orders", order_ids)

    item_rng = get_rng(seed, "ecommerce.order_items")
    item_count = row_counts["order_items"]
    order_ids_for_items = _base_or_sample(order_ids, item_count, item_rng)
    product_weights = normalize(
        products["category"]
        .map(
            {
                "electronics": 0.12,
                "apparel": 0.26,
                "home": 0.16,
                "beauty": 0.16,
                "sports": 0.12,
                "grocery": 0.18,
            }
        )
        .to_numpy(dtype=float)
    )
    product_ids_for_items = registry.sample("products", item_count, item_rng, product_weights)
    product_lookup = products.set_index("product_id")
    chosen_products = product_lookup.loc[product_ids_for_items].reset_index()
    quantity_cap = (
        chosen_products["category"]
        .map({"electronics": 2, "apparel": 4, "home": 3, "beauty": 4, "sports": 3, "grocery": 6})
        .to_numpy()
    )
    quantities = np.array([item_rng.integers(1, int(cap) + 1) for cap in quantity_cap])
    unit_prices = chosen_products["list_price"].to_numpy()
    discount_rates = item_rng.choice(
        [0.0, 0.05, 0.10, 0.15, 0.20], size=item_count, p=[0.58, 0.18, 0.14, 0.07, 0.03]
    )
    gross = quantities * unit_prices
    discount_amounts = np.round(gross * discount_rates, 2)
    line_amounts = np.round(gross - discount_amounts, 2)
    order_items = pd.DataFrame(
        {
            "order_item_id": np.arange(1, item_count + 1, dtype=np.int64),
            "order_id": order_ids_for_items,
            "product_id": product_ids_for_items,
            "quantity": quantities,
            "unit_price": unit_prices,
            "discount_amount": discount_amounts,
            "line_amount": line_amounts,
        }
    )
    subtotals = order_items.groupby("order_id", sort=False)["line_amount"].sum()
    orders["subtotal"] = orders["order_id"].map(subtotals).fillna(0.0).round(2)
    orders["tax"] = np.round(orders["subtotal"] * 0.0825, 2)
    orders["shipping_fee"] = np.where(orders["subtotal"] >= 75, 0.0, 6.99)
    orders["total_amount"] = np.round(
        orders["subtotal"] + orders["tax"] + orders["shipping_fee"], 2
    )

    return_rng = get_rng(seed, "ecommerce.returns")
    return_count = row_counts["returns"]
    item_with_category = order_items.merge(
        products[["product_id", "category"]], on="product_id", how="left"
    )
    return_propensity = (
        item_with_category["category"]
        .map(
            {
                "electronics": 0.12,
                "apparel": 0.22,
                "home": 0.07,
                "beauty": 0.08,
                "sports": 0.06,
                "grocery": 0.02,
            }
        )
        .to_numpy(dtype=float)
    )
    selected_item_idx = (
        return_rng.choice(
            item_with_category.index.to_numpy(),
            size=return_count,
            replace=return_count > len(item_with_category),
            p=normalize(return_propensity),
        )
        if return_count
        else np.array([], dtype=int)
    )
    returned_items = item_with_category.loc[selected_item_idx].reset_index(drop=True)
    order_ts_lookup = orders.set_index("order_id")["order_ts"]
    return_offsets = (
        pd.to_timedelta(return_rng.integers(3, 36, size=return_count), unit="D")
        if return_count
        else pd.to_timedelta([])
    )
    return_ts = (
        pd.to_datetime(returned_items["order_id"].map(order_ts_lookup)).reset_index(drop=True)
        + return_offsets
        if return_count
        else pd.Series(dtype="datetime64[ns]")
    )
    returns = pd.DataFrame(
        {
            "return_id": np.arange(1, return_count + 1, dtype=np.int64),
            "order_id": returned_items["order_id"] if return_count else pd.Series(dtype="int64"),
            "return_ts": return_ts,
            "return_reason": (
                return_rng.choice(
                    ["size_issue", "damaged", "changed_mind", "late_delivery", "not_as_described"],
                    size=return_count,
                    p=[0.28, 0.18, 0.24, 0.12, 0.18],
                )
                if return_count
                else pd.Series(dtype="object")
            ),
            "return_status": (
                return_rng.choice(
                    ["approved", "received", "rejected"], size=return_count, p=[0.72, 0.22, 0.06]
                )
                if return_count
                else pd.Series(dtype="object")
            ),
            "refund_amount": (
                returned_items["line_amount"].round(2)
                if return_count
                else pd.Series(dtype="float64")
            ),
        }
    )
    returned_order_ids = set(
        returns.loc[returns["return_status"] != "rejected", "order_id"].tolist()
    )
    if returned_order_ids:
        orders.loc[orders["order_id"].isin(returned_order_ids), "order_status"] = "returned"

    payment_rng = get_rng(seed, "ecommerce.payments")
    payment_count = row_counts["payments"]
    order_ids_for_payments = _base_or_sample(order_ids, payment_count, payment_rng)
    payment_orders = orders.set_index("order_id").loc[order_ids_for_payments].reset_index()
    payment_status = payment_rng.choice(["captured", "failed"], size=payment_count, p=[0.97, 0.03])
    refunded_mask = payment_orders["order_id"].isin(returned_order_ids).to_numpy()
    payment_status[refunded_mask] = "refunded"
    payments = pd.DataFrame(
        {
            "payment_id": np.arange(1, payment_count + 1, dtype=np.int64),
            "order_id": order_ids_for_payments,
            "payment_ts": payment_orders["order_ts"]
            + pd.to_timedelta(payment_rng.integers(0, 120, size=payment_count), unit="m"),
            "payment_method": payment_rng.choice(
                ["card", "wallet", "bank_transfer", "gift_card"],
                size=payment_count,
                p=[0.68, 0.18, 0.10, 0.04],
            ),
            "payment_status": payment_status,
            "amount": payment_orders["total_amount"].round(2),
            "refunded_amount": np.where(
                payment_status == "refunded", payment_orders["total_amount"], 0.0
            ),
        }
    )

    shipment_rng = get_rng(seed, "ecommerce.shipments")
    shipment_count = row_counts["shipments"]
    order_ids_for_shipments = _base_or_sample(order_ids, shipment_count, shipment_rng)
    shipment_orders = orders.set_index("order_id").loc[order_ids_for_shipments].reset_index()
    delayed = shipment_rng.random(shipment_count) < 0.09
    shipment_days = shipment_rng.integers(0, 3, size=shipment_count)
    delivery_days = shipment_rng.integers(2, 7, size=shipment_count) + np.where(
        delayed,
        shipment_rng.integers(2, 6, size=shipment_count),
        0,
    )
    shipments = pd.DataFrame(
        {
            "shipment_id": np.arange(1, shipment_count + 1, dtype=np.int64),
            "order_id": order_ids_for_shipments,
            "shipment_ts": shipment_orders["order_ts"] + pd.to_timedelta(shipment_days, unit="D"),
            "delivery_ts": shipment_orders["order_ts"] + pd.to_timedelta(delivery_days, unit="D"),
            "carrier": shipment_rng.choice(
                ["UPS", "FedEx", "USPS", "DHL"], shipment_count, p=[0.34, 0.28, 0.26, 0.12]
            ),
            "shipment_status": np.where(delayed, "delayed", "delivered"),
            "delayed": delayed,
        }
    )

    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "shipments": shipments,
        "returns": returns,
    }

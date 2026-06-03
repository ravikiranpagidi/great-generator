"""Logistics domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

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
        "shippers": TableSchema(
            name="shippers",
            primary_key="shipper_id",
            description="Companies sending goods through the logistics network.",
            columns=(
                _c("shipper_id", "int64"),
                _c("shipper_name", "string"),
                _c("industry", "string"),
                _c("region", "string"),
                _c("account_tier", "string"),
            ),
        ),
        "warehouses": TableSchema(
            name="warehouses",
            primary_key="warehouse_id",
            description="Fulfilment and cross-dock facilities.",
            columns=(
                _c("warehouse_id", "int64"),
                _c("warehouse_code", "string"),
                _c("region", "string"),
                _c("warehouse_type", "string"),
                _c("capacity_units", "int64"),
            ),
        ),
        "carriers": TableSchema(
            name="carriers",
            primary_key="carrier_id",
            description="Transportation providers and service levels.",
            columns=(
                _c("carrier_id", "int64"),
                _c("carrier_name", "string"),
                _c("carrier_type", "string"),
                _c("service_level", "string"),
                _c("on_time_score", "float64"),
            ),
        ),
        "products": TableSchema(
            name="products",
            primary_key="product_id",
            description="Shipped goods with handling requirements.",
            columns=(
                _c("product_id", "int64"),
                _c("sku", "string"),
                _c("category", "string"),
                _c("weight_kg", "float64"),
                _c("hazmat", "bool"),
            ),
        ),
        "shipments": TableSchema(
            name="shipments",
            primary_key="shipment_id",
            foreign_keys=(
                ForeignKey("shipper_id", "shippers", "shipper_id"),
                ForeignKey("origin_warehouse_id", "warehouses", "warehouse_id"),
                ForeignKey("destination_warehouse_id", "warehouses", "warehouse_id"),
                ForeignKey("carrier_id", "carriers", "carrier_id"),
                ForeignKey("product_id", "products", "product_id"),
            ),
            description="Shipment facts with cost, delay, and route behavior.",
            columns=(
                _c("shipment_id", "int64"),
                _c("shipper_id", "int64"),
                _c("origin_warehouse_id", "int64"),
                _c("destination_warehouse_id", "int64"),
                _c("carrier_id", "int64"),
                _c("product_id", "int64"),
                _c("ship_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("promised_delivery_date", "date"),
                _c("delivery_status", "string"),
                _c("distance_miles", "float64"),
                _c("shipping_cost", "float64"),
                _c("delayed", "bool"),
            ),
        ),
        "shipment_events": TableSchema(
            name="shipment_events",
            primary_key="shipment_event_id",
            foreign_keys=(ForeignKey("shipment_id", "shipments", "shipment_id"),),
            description="Tracking events for each shipment lifecycle.",
            columns=(
                _c("shipment_event_id", "int64"),
                _c("shipment_id", "int64"),
                _c("event_ts", "datetime64[ns]"),
                _c("event_type", "string"),
                _c("location_region", "string"),
                _c("sequence_number", "int64"),
            ),
        ),
        "inventory_movements": TableSchema(
            name="inventory_movements",
            primary_key="movement_id",
            foreign_keys=(
                ForeignKey("warehouse_id", "warehouses", "warehouse_id"),
                ForeignKey("product_id", "products", "product_id"),
            ),
            description="Warehouse stock movements for operational testing.",
            columns=(
                _c("movement_id", "int64"),
                _c("warehouse_id", "int64"),
                _c("product_id", "int64"),
                _c("movement_ts", "datetime64[ns]"),
                _c("movement_type", "string"),
                _c("quantity", "int64"),
                _c("reason_code", "string"),
            ),
        ),
    }
    return DomainSchema(
        name="logistics",
        tables=tables,
        description="A logistics domain with shippers, warehouses, carriers, shipments, tracking, and inventory.",
        behaviors=(
            "Large shippers generate a disproportionate share of shipments",
            "Carrier service level influences delay probability",
            "Hazmat and heavy products cost more to ship",
            "Tracking events follow a shipment lifecycle sequence",
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

    shipper_rng = get_rng(seed, "logistics.shippers")
    shipper_count = row_counts["shippers"]
    shipper_ids = np.arange(1, shipper_count + 1, dtype=np.int64)
    account_tiers = shipper_rng.choice(
        ["strategic", "enterprise", "standard", "growth"],
        shipper_count,
        p=[0.08, 0.18, 0.54, 0.20],
    )
    shippers = pd.DataFrame(
        {
            "shipper_id": shipper_ids,
            "shipper_name": [f"Shipper {value:05d}" for value in shipper_ids],
            "industry": shipper_rng.choice(
                ["retail", "manufacturing", "healthcare", "automotive", "technology"],
                shipper_count,
                p=[0.34, 0.24, 0.14, 0.12, 0.16],
            ),
            "region": shipper_rng.choice(["northeast", "south", "midwest", "west"], shipper_count),
            "account_tier": account_tiers,
        }
    )
    registry.register("shippers", shipper_ids)

    wh_rng = get_rng(seed, "logistics.warehouses")
    warehouse_count = row_counts["warehouses"]
    warehouse_ids = np.arange(1, warehouse_count + 1, dtype=np.int64)
    warehouses = pd.DataFrame(
        {
            "warehouse_id": warehouse_ids,
            "warehouse_code": [f"WH{value:04d}" for value in warehouse_ids],
            "region": wh_rng.choice(["northeast", "south", "midwest", "west"], warehouse_count),
            "warehouse_type": wh_rng.choice(
                ["fulfillment", "cross_dock", "cold_storage", "returns"],
                warehouse_count,
                p=[0.48, 0.24, 0.12, 0.16],
            ),
            "capacity_units": wh_rng.integers(10_000, 500_000, warehouse_count),
        }
    )
    registry.register("warehouses", warehouse_ids)

    carrier_rng = get_rng(seed, "logistics.carriers")
    carrier_count = row_counts["carriers"]
    carrier_ids = np.arange(1, carrier_count + 1, dtype=np.int64)
    service_levels = carrier_rng.choice(
        ["standard", "expedited", "same_day", "freight"], carrier_count, p=[0.48, 0.24, 0.08, 0.20]
    )
    carriers = pd.DataFrame(
        {
            "carrier_id": carrier_ids,
            "carrier_name": [f"Carrier {value:04d}" for value in carrier_ids],
            "carrier_type": carrier_rng.choice(
                ["parcel", "ltl", "ftl", "air"], carrier_count, p=[0.52, 0.22, 0.18, 0.08]
            ),
            "service_level": service_levels,
            "on_time_score": np.round(
                carrier_rng.normal(np.where(service_levels == "expedited", 0.92, 0.84), 0.05), 3
            ).clip(0.55, 0.99),
        }
    )
    registry.register("carriers", carrier_ids)

    product_rng = get_rng(seed, "logistics.products")
    product_count = row_counts["products"]
    product_ids = np.arange(1, product_count + 1, dtype=np.int64)
    categories = product_rng.choice(
        ["apparel", "electronics", "grocery", "industrial", "pharma"],
        product_count,
        p=[0.26, 0.22, 0.18, 0.22, 0.12],
    )
    products = pd.DataFrame(
        {
            "product_id": product_ids,
            "sku": [f"LOGSKU{value:07d}" for value in product_ids],
            "category": categories,
            "weight_kg": np.round(
                product_rng.lognormal(
                    pd.Series(categories)
                    .map(
                        {
                            "apparel": 0.9,
                            "electronics": 1.4,
                            "grocery": 1.1,
                            "industrial": 2.8,
                            "pharma": 0.6,
                        }
                    )
                    .to_numpy(),
                    0.5,
                    product_count,
                ),
                2,
            ),
            "hazmat": product_rng.random(product_count)
            < np.where(categories == "industrial", 0.12, 0.015),
        }
    )
    registry.register("products", product_ids)

    shipment_rng = get_rng(seed, "logistics.shipments")
    shipment_count = row_counts["shipments"]
    shipment_ids = np.arange(1, shipment_count + 1, dtype=np.int64)
    shipper_weights = (
        pd.Series(account_tiers)
        .map({"strategic": 4.2, "enterprise": 2.4, "standard": 1.0, "growth": 0.7})
        .to_numpy()
    )
    shipment_shipper_ids = registry.sample(
        "shippers", shipment_count, shipment_rng, normalize(shipper_weights)
    )
    shipment_product_ids = registry.sample("products", shipment_count, shipment_rng)
    shipment_carrier_ids = registry.sample("carriers", shipment_count, shipment_rng)
    origin_ids = registry.sample("warehouses", shipment_count, shipment_rng)
    dest_ids = registry.sample("warehouses", shipment_count, shipment_rng)
    same = dest_ids == origin_ids
    if same.any():
        dest_ids[same] = registry.sample("warehouses", int(same.sum()), shipment_rng)
    shipment_dates = weighted_calendar_dates(shipment_rng, shipment_count, weekend_multiplier=0.65)
    ship_ts = random_timestamps_on_dates(shipment_rng, shipment_dates, business_hours_bias=0.78)
    carrier_base = carriers.set_index("carrier_id").loc[shipment_carrier_ids]
    product_base = products.set_index("product_id").loc[shipment_product_ids]
    distance = np.round(shipment_rng.lognormal(6.3, 0.65, shipment_count), 2)
    delay_probability = (1.0 - carrier_base["on_time_score"].to_numpy()) + np.where(
        product_base["hazmat"].to_numpy(), 0.04, 0.0
    )
    delayed = shipment_rng.random(shipment_count) < delay_probability.clip(0.02, 0.35)
    transit_days = np.where(carrier_base["service_level"].to_numpy() == "expedited", 2, 5)
    transit_days = np.where(
        delayed, transit_days + shipment_rng.integers(2, 7, shipment_count), transit_days
    )
    shipping_cost = np.round(8.5 + distance * 0.12 + product_base["weight_kg"].to_numpy() * 1.8, 2)
    shipments = pd.DataFrame(
        {
            "shipment_id": shipment_ids,
            "shipper_id": shipment_shipper_ids,
            "origin_warehouse_id": origin_ids,
            "destination_warehouse_id": dest_ids,
            "carrier_id": shipment_carrier_ids,
            "product_id": shipment_product_ids,
            "ship_ts": ship_ts,
            "event_date": ship_ts.dt.date,
            "promised_delivery_date": (
                ship_ts
                + pd.to_timedelta(np.where(delayed, transit_days - 2, transit_days), unit="D")
            ).dt.date,
            "delivery_status": np.where(
                delayed,
                "delayed",
                shipment_rng.choice(["delivered", "in_transit"], shipment_count, p=[0.74, 0.26]),
            ),
            "distance_miles": distance,
            "shipping_cost": shipping_cost,
            "delayed": delayed,
        }
    )
    registry.register("shipments", shipment_ids)

    event_rng = get_rng(seed, "logistics.shipment_events")
    event_count = row_counts["shipment_events"]
    event_ids = np.arange(1, event_count + 1, dtype=np.int64)
    event_shipment_ids = _base_or_sample(shipment_ids, event_count, event_rng)
    event_base = shipments.set_index("shipment_id").loc[event_shipment_ids]
    event_types = event_rng.choice(
        ["label_created", "picked_up", "in_transit", "out_for_delivery", "delivered", "exception"],
        event_count,
        p=[0.16, 0.18, 0.34, 0.14, 0.15, 0.03],
    )
    shipment_events = pd.DataFrame(
        {
            "shipment_event_id": event_ids,
            "shipment_id": event_shipment_ids,
            "event_ts": pd.to_datetime(event_base["ship_ts"].to_numpy())
            + pd.to_timedelta(event_rng.integers(1, 144, event_count), unit="h"),
            "event_type": event_types,
            "location_region": event_rng.choice(
                ["northeast", "south", "midwest", "west"], event_count
            ),
            "sequence_number": event_rng.integers(1, 8, event_count),
        }
    )

    move_rng = get_rng(seed, "logistics.inventory")
    movement_count = row_counts["inventory_movements"]
    movement_ids = np.arange(1, movement_count + 1, dtype=np.int64)
    movement_types = move_rng.choice(
        ["receipt", "pick", "adjustment", "return", "transfer"],
        movement_count,
        p=[0.28, 0.38, 0.08, 0.12, 0.14],
    )
    movement_dates = weighted_calendar_dates(move_rng, movement_count)
    inventory_movements = pd.DataFrame(
        {
            "movement_id": movement_ids,
            "warehouse_id": registry.sample("warehouses", movement_count, move_rng),
            "product_id": registry.sample("products", movement_count, move_rng),
            "movement_ts": random_timestamps_on_dates(
                move_rng, movement_dates, business_hours_bias=0.76
            ),
            "movement_type": movement_types,
            "quantity": np.where(
                movement_types == "pick",
                -move_rng.integers(1, 80, movement_count),
                move_rng.integers(1, 160, movement_count),
            ),
            "reason_code": move_rng.choice(
                ["customer_order", "replenishment", "cycle_count", "damage", "return"],
                movement_count,
            ),
        }
    )

    return {
        "shippers": shippers,
        "warehouses": warehouses,
        "carriers": carriers,
        "products": products,
        "shipments": shipments,
        "shipment_events": shipment_events,
        "inventory_movements": inventory_movements,
    }

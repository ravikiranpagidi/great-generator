"""Manufacturing and industrial domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from great_generator.domains._industry import c, fk, generate_industry_pandas, table
from great_generator.schemas.models import DomainSchema

CHOICES = {
    "supplier_category": ["raw_material", "electronics", "packaging", "machining", "logistics"],
    "plant_type": ["assembly", "fabrication", "packaging", "test_lab"],
    "product_family": [
        "aerospace",
        "heavy_machinery",
        "consumer_electronics",
        "industrial",
        "automotive",
    ],
    "work_order_status": ["released", "in_progress", "on_hold", "completed", "scrapped"],
    "run_status": ["running", "completed", "stopped", "maintenance"],
    "inspection_result": ["pass", "fail", "rework", "waived"],
    "defect_type": ["cosmetic", "dimension", "electrical", "material", "assembly"],
    "movement_type": ["receipt", "issue", "transfer", "adjustment", "scrap"],
}


def schema() -> DomainSchema:
    tables = {
        "suppliers": table(
            "suppliers",
            "supplier_id",
            (
                c("supplier_id", "int64"),
                c("supplier_name", "string"),
                c("supplier_category", "string"),
                c("region", "string"),
                c("quality_score", "float64"),
            ),
        ),
        "plants": table(
            "plants",
            "plant_id",
            (
                c("plant_id", "int64"),
                c("plant_code", "string"),
                c("plant_type", "string"),
                c("region", "string"),
                c("capacity_units", "int64"),
            ),
        ),
        "products": table(
            "products",
            "product_id",
            (
                c("product_id", "int64"),
                c("sku", "string"),
                c("product_name", "string"),
                c("product_family", "string"),
                c("unit_cost", "float64"),
                c("active", "bool"),
            ),
        ),
        "work_orders": table(
            "work_orders",
            "work_order_id",
            (
                c("work_order_id", "int64"),
                c("plant_id", "int64"),
                c("product_id", "int64"),
                c("supplier_id", "int64"),
                c("scheduled_start_ts", "datetime64[ns]"),
                c("planned_quantity", "int64"),
                c("work_order_status", "string"),
            ),
            (
                fk("plant_id", "plants", "plant_id"),
                fk("product_id", "products", "product_id"),
                fk("supplier_id", "suppliers", "supplier_id"),
            ),
            "Planned manufacturing demand and production orders.",
        ),
        "production_runs": table(
            "production_runs",
            "production_run_id",
            (
                c("production_run_id", "int64"),
                c("work_order_id", "int64"),
                c("plant_id", "int64"),
                c("product_id", "int64"),
                c("run_start_ts", "datetime64[ns]"),
                c("run_status", "string"),
                c("produced_quantity", "int64"),
                c("scrap_quantity", "int64"),
                c("runtime_minutes", "int64"),
            ),
            (
                fk("work_order_id", "work_orders", "work_order_id"),
                fk("plant_id", "plants", "plant_id"),
                fk("product_id", "products", "product_id"),
            ),
            "Actual production runs with scrap and runtime signals.",
        ),
        "quality_inspections": table(
            "quality_inspections",
            "inspection_id",
            (
                c("inspection_id", "int64"),
                c("production_run_id", "int64"),
                c("product_id", "int64"),
                c("inspection_ts", "datetime64[ns]"),
                c("inspection_result", "string"),
                c("defect_type", "string", nullable=True),
                c("defect_rate", "float64"),
            ),
            (
                fk("production_run_id", "production_runs", "production_run_id"),
                fk("product_id", "products", "product_id"),
            ),
            "Quality inspection outcomes and defect patterns.",
        ),
        "inventory_movements": table(
            "inventory_movements",
            "movement_id",
            (
                c("movement_id", "int64"),
                c("plant_id", "int64"),
                c("product_id", "int64"),
                c("movement_ts", "datetime64[ns]"),
                c("movement_type", "string"),
                c("quantity", "int64"),
                c("inventory_value", "float64"),
            ),
            (fk("plant_id", "plants", "plant_id"), fk("product_id", "products", "product_id")),
            "Inventory and materials movement records.",
        ),
    }
    return DomainSchema(
        name="manufacturing",
        tables=tables,
        description="Manufacturing and industrial domain for suppliers, plants, products, work orders, production, quality, and inventory.",
        behaviors=(
            "Production runs connect planning to actual output",
            "Quality inspection results expose defect and rework patterns",
            "Supplier and plant dimensions support operational benchmarking",
            "Inventory movement records support factory automation demos",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)
